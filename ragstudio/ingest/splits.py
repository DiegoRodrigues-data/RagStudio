"""Corpus splits (train / validation / test) and the leakage check enforced by the experiment runner.

A split is a list of document ids with a hash. A runbook that declares a split only indexes those documents and only
asks questions that belong to it; a question whose gold passages point outside the declared split is a leak.
"""
from __future__ import annotations

from typing import Any

from ..core.errors import LeakageError, ValidationError
from ..core.hashing import sha256_json
from ..core.seeds import rng

SPLITS = ("train", "validation", "test")


def make_splits(document_ids: list[str], ratios: dict[str, float], seed: int = 42,
                strata: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """Deterministic shuffle + proportional cut; with `strata` (doc id -> label) each label is cut separately."""
    unknown = set(ratios) - set(SPLITS)
    if unknown:
        raise ValidationError(f"unknown split name(s) {sorted(unknown)}; use {SPLITS}")
    total = sum(ratios.values())
    if total <= 0:
        raise ValidationError("split ratios must sum to a positive number")
    names = [s for s in SPLITS if ratios.get(s, 0) > 0]
    groups: dict[Any, list[str]] = {}
    for doc_id in sorted(document_ids):
        groups.setdefault((strata or {}).get(doc_id, "_all"), []).append(doc_id)
    out: dict[str, list[str]] = {name: [] for name in names}
    generator = rng(seed)
    for label in sorted(groups, key=str):
        ids = groups[label]
        order = [ids[i] for i in generator.permutation(len(ids))]
        start = 0
        for n, name in enumerate(names):
            end = len(order) if n == len(names) - 1 else start + round(len(order) * ratios[name] / total)
            out[name].extend(order[start:end])
            start = end
    return {name: sorted(ids) for name, ids in out.items()}


def splits_hash(splits: dict[str, list[str]]) -> str:
    return sha256_json({name: sorted(ids) for name, ids in sorted(splits.items())})


def assert_disjoint(splits: dict[str, list[str]]) -> None:
    seen: dict[str, str] = {}
    for name, ids in splits.items():
        for doc_id in ids:
            if doc_id in seen:
                raise LeakageError(f"document '{doc_id}' is in both '{seen[doc_id]}' and '{name}' splits")
            seen[doc_id] = name


def select_questions(questions: list[dict[str, Any]], split: str, split_docs: list[str]) -> list[dict[str, Any]]:
    """Questions usable with `split`. Raises LeakageError when a question of this split needs outside documents.

    A question is kept when it is tagged with `split`, or untagged with every gold document inside the split (or no
    gold at all). A question tagged with another split is dropped. A question tagged with `split` whose gold
    passages reference a document outside it is a leak.
    """
    inside = set(split_docs)
    kept = []
    for q in questions:
        gold_docs = {g["document_id"] for g in q.get("gold_passages", [])}
        tag = q.get("split")
        if tag and tag != split:
            continue
        outside = sorted(gold_docs - inside)
        if tag == split and outside:
            raise LeakageError(f"question '{q.get('code') or q.get('id')}' belongs to split '{split}' but its gold "
                               f"passages reference documents outside it: {outside}")
        if outside:
            continue
        kept.append(q)
    return kept
