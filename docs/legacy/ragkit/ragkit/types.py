from typing import Any, Callable, Dict, List, Optional, TypedDict

Doc = Dict[str, Any]

Retriever = Callable[[str, int, Optional[Dict[str, Any]]], List[Doc]]   # (query, k, filters) -> docs
Reranker  = Callable[[str, List[Doc], int], List[Doc]]                 # (query, docs, k) -> docs
LLM       = Callable[[str], str]                                       # prompt -> text
Embedder  = Callable[[str], List[float]]                               # text -> embedding


class RAGInput(TypedDict, total=False):
    query: str
    k: int
    filters: Optional[Dict[str, Any]]
    max_context_chars: int

    retriever: Retriever
    llm: LLM
    reranker: Optional[Reranker]

    extra: Dict[str, Any]


class RAGOutput(TypedDict):
    answer: str
    contexts: List[Doc]
    citations: List[Dict[str, Any]]
    diagnostics: Dict[str, Any]
