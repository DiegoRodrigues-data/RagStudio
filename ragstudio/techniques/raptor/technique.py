"""RAPTOR: a tree of recursive LLM summaries over clusters of chunks, searched together with the chunks.

Reference: Sarthi et al., "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval", ICLR 2024.

Building the tree, once per index (cached next to it; the cost lands on the first question, see `built_now`):
1. node embeddings are reduced to a few dimensions (UMAP when `umap-learn` is installed, PCA otherwise; which one
   was used is recorded in the diagnostics);
2. a Gaussian mixture is fitted, with the number of clusters chosen by BIC. Clustering is soft: a node joins every
   cluster where its probability passes `soft_threshold`, so one chunk can feed several summaries;
3. a cluster whose text exceeds `summary_input_chars` is clustered again, as in the paper;
4. the LLM summarizes each cluster; the summaries are the nodes of the next level;
5. steps 1 to 4 repeat on the new level until it can no longer be clustered or `max_levels` is reached.

Querying:
- `mode="collapsed"` (the paper's best setting): chunks and summaries of every level compete in one ranking;
- `mode="tree_traversal"`: the most similar nodes of the top level are chosen, then the most similar of their
  children, down to the chunks; the nodes chosen at every level form the candidate set.

Differences from the paper: the mixture uses diagonal covariances; the paper's two-step global then local
clustering is replaced by step 3; without `umap-learn` the reduction is PCA.
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from typing import Any

import numpy as np

from ...core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ...core.errors import ValidationError
from ...core.hashing import sha256_text
from ...core.models import RetrievedChunk
from ...core.pipeline import finish, generate, merge_pool, select, synthetic_chunk
from ...core.seeds import rng
from .. import _vectors

SPEC = TechniqueSpec(
    name="raptor", title="RAPTOR", stage="indexing", ignores=("retrieval_mode",), version="1.0.0", family="structure",
    description="Search chunks together with a recursive tree of LLM summaries built over soft clusters of chunks.",
    params={"mode": Param("collapsed", "collapsed: all levels in one ranking; tree_traversal: top-down",
                          ("collapsed", "tree_traversal")),
            "max_levels": Param(3, "summary levels built above the chunks"),
            "reduction": Param("auto", "dimensionality reduction before clustering; auto = UMAP when installed",
                               ("auto", "umap", "pca", "none")),
            "reduction_dim": Param(10, "dimensions kept by the reduction"),
            "max_clusters": Param(50, "largest number of clusters the BIC search may choose"),
            "soft_threshold": Param(0.1, "membership probability above which a node joins a cluster"),
            "summary_input_chars": Param(6000, "characters of cluster text sent to the summarizer"),
            "tree_top_k": Param(3, "nodes kept per level in tree traversal")},
    requires=("embedder", "llm", "index:aux"),
    reference="https://arxiv.org/abs/2401.18059", origin="new",
)
CANDIDATES = (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 32, 40, 50, 64, 80, 100)


def reduce(matrix: np.ndarray, method: str, dim: int, seed: int) -> tuple[np.ndarray, str]:
    """(reduced matrix, method actually used)."""
    n = len(matrix)
    dim = max(1, min(dim, n - 2, matrix.shape[1]))
    if method == "none" or n < 4:
        return matrix, "none"
    has_umap = importlib.util.find_spec("umap") is not None
    if method == "umap" and not has_umap:
        raise ValidationError("raptor: reduction=umap needs `pip install umap-learn`")
    if method in ("auto", "umap") and has_umap and n > dim + 2:
        import umap
        reducer = umap.UMAP(n_neighbors=max(2, min(15, n - 1)), n_components=dim, metric="cosine", random_state=seed)
        return np.asarray(reducer.fit_transform(matrix), dtype=np.float64), "umap"
    centered = matrix - matrix.mean(axis=0)
    with np.errstate(all="ignore"):
        _, _, components = np.linalg.svd(centered, full_matrices=False)
        return centered @ components[:dim].T, "pca"


def fit_gmm(data: np.ndarray, k: int, seed: int, iterations: int = 40) -> tuple[np.ndarray, float]:
    """Diagonal-covariance Gaussian mixture by EM. Returns (responsibilities n x k, BIC)."""
    n, d = data.shape
    generator = rng(seed)
    centers = [data[int(generator.integers(n))]]
    for _ in range(1, k):  # k-means++ seeding
        distance = np.min([((data - c) ** 2).sum(axis=1) for c in centers], axis=0)
        total = distance.sum()
        centers.append(data[int(generator.choice(n, p=distance / total)) if total > 0 else int(generator.integers(n))])
    means = np.array(centers)
    floor = 1e-6 + 1e-3 * data.var(axis=0).mean()
    variances = np.tile(data.var(axis=0) + floor, (k, 1))
    weights = np.full(k, 1.0 / k)
    log_likelihood = 0.0
    responsibilities = np.full((n, k), 1.0 / k)
    for _ in range(iterations):
        log_prob = (-0.5 * (((data[:, None, :] - means[None]) ** 2) / variances[None]).sum(axis=2)
                    - 0.5 * np.log(2 * np.pi * variances).sum(axis=1)[None] + np.log(weights)[None])
        peak = log_prob.max(axis=1, keepdims=True)
        log_norm = peak + np.log(np.exp(log_prob - peak).sum(axis=1, keepdims=True))
        responsibilities = np.exp(log_prob - log_norm)
        log_likelihood = float(log_norm.sum())
        mass = responsibilities.sum(axis=0) + 1e-12
        weights = mass / n
        with np.errstate(all="ignore"):  # numpy/Accelerate emits spurious matmul warnings on macOS arm64
            means = (responsibilities.T @ data) / mass[:, None]
            variances = (responsibilities.T @ (data ** 2)) / mass[:, None] - means ** 2 + floor
        variances = np.maximum(variances, floor)
    return responsibilities, -2.0 * log_likelihood + (2 * k * d + k - 1) * np.log(n)


def soft_clusters(data: np.ndarray, max_clusters: int, threshold: float, seed: int) -> list[list[int]]:
    """Clusters as lists of row indices; a row may be in several. The number of clusters minimizes BIC."""
    n = len(data)
    if n < 3:
        return [list(range(n))]
    best: tuple[float, np.ndarray] | None = None
    for k in (c for c in CANDIDATES if c <= min(max_clusters, n - 1)):
        responsibilities, bic = fit_gmm(data, k, seed)
        if best is None or bic < best[0]:
            best = (bic, responsibilities)
    assert best is not None
    responsibilities = best[1]
    members: list[list[int]] = [[] for _ in range(responsibilities.shape[1])]
    for row, probabilities in enumerate(responsibilities):
        chosen = [c for c, p in enumerate(probabilities) if p > threshold] or [int(np.argmax(probabilities))]
        for c in chosen:
            members[c].append(row)
    return [m for m in members if m]


def fitting_clusters(matrix: np.ndarray, lengths: list[int], rows: list[int], params: dict[str, Any], seed: int,
                     depth: int = 0) -> tuple[list[list[int]], str]:
    """Cluster `rows`, clustering again any cluster whose text would not fit the summarizer."""
    reduced, method = reduce(matrix[rows], params["reduction"], params["reduction_dim"], seed)
    out: list[list[int]] = []
    for cluster in soft_clusters(reduced, params["max_clusters"], params["soft_threshold"], seed):
        ids = [rows[i] for i in cluster]
        if sum(lengths[i] for i in ids) <= params["summary_input_chars"] or len(ids) == 1:
            out.append(ids)
        elif len(ids) < len(rows) and depth < 4:
            out.extend(fitting_clusters(matrix, lengths, ids, params, seed, depth + 1)[0])
        else:  # the mixture would not split it further: cut it into consecutive groups that fit
            group, used = [], 0
            for i in ids:
                if group and used + lengths[i] > params["summary_input_chars"]:
                    out.append(group)
                    group, used = [], 0
                group.append(i)
                used += lengths[i]
            out.append(group)
    return out, method


def build_tree(deps: TechniqueDeps, params: dict[str, Any]) -> dict[str, Any]:
    chunks = deps.store.all_chunks()
    nodes = [{"id": c.id, "text": c.text, "document_id": c.document_id} for c in chunks]
    matrix = _vectors.unit_rows([deps.store.embedding(c.id) for c in chunks]).astype(np.float64)
    tree: list[dict[str, Any]] = []
    method = "none"
    for level in range(1, params["max_levels"] + 1):
        if len(nodes) < 2:
            break
        clusters, method = fitting_clusters(matrix, [len(n["text"]) for n in nodes], list(range(len(nodes))), params,
                                            deps.seed + level)
        if len(clusters) >= len(nodes):
            break
        level_nodes = []
        for number, cluster in enumerate(clusters):
            text = "\n\n".join(nodes[i]["text"] for i in cluster)[:params["summary_input_chars"]]
            summary = deps.ask("summarize", text=text).strip()
            if summary:
                documents = Counter(nodes[i]["document_id"] for i in cluster)
                level_nodes.append({"id": f"raptor:L{level}:{number}", "level": level, "text": summary,
                                    "children": [nodes[i]["id"] for i in cluster],
                                    "document_id": documents.most_common(1)[0][0]})
        if not level_nodes:
            break
        tree.extend(level_nodes)
        nodes = level_nodes
        matrix = _vectors.unit_rows(deps.embed([n["text"] for n in nodes])).astype(np.float64)
    return {"nodes": tree, "levels": max((n["level"] for n in tree), default=0), "reduction": method}


def as_chunk(node: dict[str, Any], score: float, rank: int) -> RetrievedChunk:
    return synthetic_chunk(node["id"], node["document_id"], node["text"], score, rank, "raptor:summary",
                           raptor_level=node["level"], children=len(node["children"]))


def collapsed(deps: TechniqueDeps, tree: dict[str, Any], key: str, request: TechniqueRequest,
              vector: list[float]) -> list[RetrievedChunk]:
    nodes = tree["nodes"]
    leaves = deps.retrieve(request.query.text, request.k, mode="dense", query_vector=vector, filters=request.filters)
    matrix = _vectors.vectors(deps, key, "raptor", [n["text"] for n in nodes])
    summaries = [as_chunk(nodes[i], score, rank)
                 for rank, (i, score) in enumerate(_vectors.top(_vectors.similarities(matrix, vector), request.k,
                                                                minimum=-1.0), 1)]
    deps.log_retrieval(request.query.text, "raptor:collapsed", summaries)
    return merge_pool(leaves, summaries)


def traversal(deps: TechniqueDeps, tree: dict[str, Any], key: str, request: TechniqueRequest, vector: list[float],
              width: int) -> list[RetrievedChunk]:
    nodes = tree["nodes"]
    if not nodes:
        return deps.retrieve(request.query.text, request.k, mode="dense", query_vector=vector, filters=request.filters)
    by_id = {n["id"]: n for n in nodes}
    scores = dict(zip(by_id, _vectors.similarities(_vectors.vectors(deps, key, "raptor", [n["text"] for n in nodes]),
                                                   vector).tolist(), strict=True))
    frontier = [n["id"] for n in nodes if n["level"] == tree["levels"]]
    chosen: list[RetrievedChunk] = []
    while frontier:
        summaries = sorted((i for i in frontier if i in by_id), key=lambda i: (-scores[i], i))[:width]
        leaf_ids = [i for i in frontier if i not in by_id]
        if leaf_ids:
            found = deps.store.get(leaf_ids)
            leaf_matrix = _vectors.unit_rows([deps.store.embedding(c.id) for c in found])
            ranked = _vectors.top(_vectors.similarities(leaf_matrix, vector), width, minimum=-1.0)
            chosen += [RetrievedChunk(found[i], score, 0, "raptor:leaf") for i, score in ranked]
        chosen += [as_chunk(by_id[i], scores[i], 0) for i in summaries]
        frontier = list(dict.fromkeys(child for i in summaries for child in by_id[i]["children"]))
    pool = merge_pool(chosen)
    deps.log_retrieval(request.query.text, "raptor:tree_traversal", pool)
    return pool


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    built = "|".join(str(params[name]) for name in ("max_levels", "reduction", "reduction_dim", "max_clusters",
                                                    "soft_threshold", "summary_input_chars"))
    key = "raptor_" + sha256_text(f"{deps.llm_model}|{deps.language}|{deps.seed}|{built}")[:12]
    tree = deps.store.aux_load(key)
    built_now = tree is None
    if built_now:
        with deps.stage("index_build"):
            tree = build_tree(deps, params)
            deps.store.aux_save(key, tree)
    with deps.stage("retrieval"):
        vector = deps.embed([question])[0]
        if params["mode"] == "tree_traversal":
            pool = traversal(deps, tree, key, request, vector, max(1, params["tree_top_k"]))
        else:
            pool = collapsed(deps, tree, key, request, vector)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    per_level = Counter(n["level"] for n in tree["nodes"])
    return finish(SPEC, deps, answer, chunks, context,
                  {"mode": params["mode"], "levels": tree["levels"], "summaries": len(tree["nodes"]),
                   "summaries_per_level": {str(level): per_level[level] for level in sorted(per_level)},
                   "reduction": tree["reduction"], "built_now": built_now,
                   "summaries_in_context": sum(1 for c in chunks if c.source == "raptor:summary")})
