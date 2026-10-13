"""In-memory knowledge graph shared by the graph techniques (GraphRAG, LightRAG, HippoRAG). No graph database.

Nodes are normalized entity names with a type and the descriptions the extractor wrote for them; edges are typed
relations between two entities, with their descriptions and the chunks that state them. The graph is plain JSON, so
it is stored next to the index (`store.aux_save`) and built once per index, LLM and language.

`louvain` detects communities by modularity optimization (Blondel et al., 2008), level by level, with a fixed node
order so the result is deterministic.
"""
from __future__ import annotations

from typing import Any

from ..core.text import normalize, tokenize

MAX_DESCRIPTIONS = 4


def _add_unique(items: list[str], value: str, limit: int | None = None) -> None:
    if value and value not in items and (limit is None or len(items) < limit):
        items.append(value)


class KnowledgeGraph:
    def __init__(self) -> None:
        self.entities: dict[str, dict[str, Any]] = {}   # key -> {label, type, descriptions, chunks}
        self.relations: dict[str, dict[str, Any]] = {}  # "a\tb" (a < b) -> {source, target, labels, descriptions, ...}

    # ------------------------------------------------------------------ build
    def add_entity(self, name: str, kind: str = "", description: str = "", chunk_id: str | None = None) -> str | None:
        key = normalize(name)
        if len(key) < 2:
            return None
        node = self.entities.setdefault(key, {"label": name.strip(), "type": "", "descriptions": [], "chunks": []})
        node["type"] = node["type"] or kind.strip().lower()
        _add_unique(node["descriptions"], description.strip(), MAX_DESCRIPTIONS)
        if chunk_id:
            _add_unique(node["chunks"], chunk_id)
        return key

    def add_relation(self, source: str, target: str, label: str = "", description: str = "",
                     chunk_id: str | None = None) -> None:
        a, b = self.add_entity(source, chunk_id=chunk_id), self.add_entity(target, chunk_id=chunk_id)
        if a is None or b is None or a == b:
            return
        edge = self.relations.setdefault("\t".join(sorted((a, b))),
                                         {"source": a, "target": b, "labels": [], "descriptions": [], "chunks": [],
                                          "weight": 0})
        edge["weight"] += 1
        _add_unique(edge["labels"], label.strip().lower(), MAX_DESCRIPTIONS)
        _add_unique(edge["descriptions"], description.strip(), MAX_DESCRIPTIONS)
        if chunk_id:
            _add_unique(edge["chunks"], chunk_id)

    def add_extraction(self, chunk_id: str, raw: str, max_entities: int) -> None:
        """Parse `ENTITY | name | type | description` and `REL | source | target | relation | description` lines.
        Tolerant by design: lines in any other shape are skipped, and relations may introduce entities."""
        seen = 0
        for line in raw.splitlines():
            fields = [f.strip() for f in line.strip().lstrip("-*• ").split("|")]
            head = fields[0].upper()
            if head == "ENTITY" and len(fields) >= 2 and seen < max_entities:
                seen += 1
                self.add_entity(fields[1], fields[2] if len(fields) > 2 else "",
                                fields[3] if len(fields) > 3 else "", chunk_id)
            elif head in ("REL", "RELATION") and len(fields) >= 3:
                self.add_relation(fields[1], fields[2], fields[3] if len(fields) > 3 else "",
                                  fields[4] if len(fields) > 4 else "", chunk_id)

    # ---------------------------------------------------------------- queries
    def adjacency(self) -> dict[str, dict[str, float]]:
        adj: dict[str, dict[str, float]] = {key: {} for key in self.entities}
        for edge in self.relations.values():
            a, b = edge["source"], edge["target"]
            adj[a][b] = adj[a].get(b, 0.0) + edge["weight"]
            adj[b][a] = adj[b].get(a, 0.0) + edge["weight"]
        return adj

    def match(self, text: str) -> list[str]:
        """Entities whose name occurs in `text` as whole words (longest first)."""
        norm = f" {' '.join(tokenize(text))} "  # punctuation never hides a name: "... de Betz?" still matches
        found = [key for key in self.entities if (words := " ".join(tokenize(key))) and f" {words} " in norm]
        return sorted(found, key=lambda k: (-len(k), k))

    def relations_of(self, key: str) -> list[dict[str, Any]]:
        return [edge for edge in self.relations.values() if key in (edge["source"], edge["target"])]

    def label(self, key: str) -> str:
        return self.entities.get(key, {}).get("label", key)

    def entity_text(self, key: str) -> str:
        node = self.entities[key]
        kind = f" ({node['type']})" if node["type"] else ""
        described = "; ".join(node["descriptions"])
        return f"{node['label']}{kind}: {described}" if described else f"{node['label']}{kind}"

    def relation_text(self, edge: dict[str, Any]) -> str:
        labels = ", ".join(edge["labels"]) or "related"
        described = "; ".join(edge["descriptions"])
        head = f"{self.label(edge['source'])} -> {self.label(edge['target'])} [{labels}]"
        return f"{head}: {described}" if described else head

    def to_dict(self) -> dict[str, Any]:
        return {"entities": self.entities, "relations": self.relations}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeGraph:
        graph = cls()
        graph.entities = data.get("entities", {})
        graph.relations = data.get("relations", {})
        return graph


def _one_level(adj: dict[str, dict[str, float]], resolution: float) -> dict[str, str]:
    """Local moving phase of Louvain. A self-loop weight counts the internal edges of an aggregated node twice."""
    degree = {node: sum(links.values()) for node, links in adj.items()}
    total = sum(degree.values())
    community = {node: node for node in adj}
    if total <= 0:
        return community
    weight_of = dict(degree)  # community -> sum of member degrees
    moved = True
    while moved:
        moved = False
        for node in sorted(adj):
            current = community[node]
            links: dict[str, float] = {}
            for other, weight in adj[node].items():
                if other != node:
                    links[community[other]] = links.get(community[other], 0.0) + weight
            weight_of[current] -= degree[node]
            best, best_gain = current, links.get(current, 0.0) - resolution * weight_of[current] * degree[node] / total
            for candidate in sorted(links):
                gain = links[candidate] - resolution * weight_of[candidate] * degree[node] / total
                if gain > best_gain + 1e-12:
                    best, best_gain = candidate, gain
            weight_of[best] += degree[node]
            if best != current:
                community[node] = best
                moved = True
    return community


def louvain(adjacency: dict[str, dict[str, float]], resolution: float = 1.0, max_levels: int = 4) -> list[dict[str, str]]:
    """Hierarchical communities, finest first: each level maps every original node to its community id."""
    levels: list[dict[str, str]] = []
    adj = {node: dict(links) for node, links in adjacency.items()}
    membership = {node: node for node in adjacency}
    for _ in range(max_levels):
        partition = _one_level(adj, resolution)
        if len(set(partition.values())) == len(adj):
            break
        membership = {node: partition[group] for node, group in membership.items()}
        levels.append(dict(membership))
        merged: dict[str, dict[str, float]] = {group: {} for group in set(partition.values())}
        for node, links in adj.items():
            for other, weight in links.items():
                a, b = partition[node], partition[other]
                merged[a][b] = merged[a].get(b, 0.0) + weight
        adj = merged
        if len(adj) <= 1:
            break
    return levels or [dict(membership)]
