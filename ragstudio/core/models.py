"""Domain data shared by every stage: document -> chunk -> query -> retrieved chunk -> context -> answer.

All records are immutable dataclasses with `to_dict()`; nothing here knows about providers, stores or SQL.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    source_path: str = ""
    sha256: str = ""
    format: str = "text"
    language: str = ""
    chars: int = 0
    pages: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, with_text: bool = True) -> dict[str, Any]:
        data = asdict(self)
        if not with_text:
            data.pop("text")
        return data


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    index: int
    text: str
    char_start: int
    char_end: int
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Chunk:
        return Chunk(**data)


@dataclass(frozen=True)
class GoldPassage:
    document_id: str
    text: str
    char_start: int | None = None
    char_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Query:
    id: str
    text: str
    expected_answer: str | None = None
    gold_passages: tuple[GoldPassage, ...] = ()
    answer_type: str = "extraction"  # boolean | extraction | classification | reasoning | summarization
    split: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    rank: int
    source: str  # dense | bm25 | hybrid | rrf | mmr | rerank:<name> | <technique specific>

    def to_dict(self) -> dict[str, Any]:
        return {"chunk": self.chunk.to_dict(), "score": self.score, "rank": self.rank, "source": self.source}

    def with_rank(self, rank: int, score: float | None = None, source: str | None = None) -> RetrievedChunk:
        return RetrievedChunk(self.chunk, self.score if score is None else score, rank, source or self.source)

    def with_text(self, text: str, **metadata: Any) -> RetrievedChunk:
        """Same chunk identity with different text (compression, parent expansion, window expansion)."""
        c = self.chunk
        new = Chunk(c.id, c.document_id, c.index, text, c.char_start, c.char_end, c.parent_id, {**c.metadata, **metadata})
        return RetrievedChunk(new, self.score, self.rank, self.source)


@dataclass(frozen=True)
class Context:
    text: str
    chunk_ids: tuple[str, ...]
    chars: int
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0
    embedding_calls: int = 0
    embedding_tokens: int = 0
    calls_by_task: dict[str, int] = field(default_factory=dict)
    estimated: bool = False  # True when at least one call had no usage reported by the API

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Answer:
    text: str
    raw_response: str = ""
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageTiming:
    stage: str
    seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
