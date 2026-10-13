from typing import List, Dict, Any, Callable

Doc = Dict[str, Any]

def rerank_noop(query: str, docs: List[Doc], k: int) -> List[Doc]:
    return docs[:k]

def make_rerank_llm(llm: Callable[[str], str]):
    def rerank(query: str, docs: List[Doc], k: int) -> List[Doc]:
        scored = []
        for d in docs:
            prompt = (
                "Dê uma nota de 0 a 10 para relevância do TEXTO em relação à PERGUNTA.\n"
                "Responda apenas com um número.\n\n"
                f"PERGUNTA: {query}\n\n"
                f"TEXTO:\n{d.get('text','')[:2000]}"
            )
            try:
                s = float(llm(prompt).strip().split()[0])
            except Exception:
                s = 0.0
            scored.append((s, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:k]]
    return rerank
