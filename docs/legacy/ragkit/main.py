import os
import duckdb

from ragkit.embed_providers import make_embed_lmstudio, make_embed_openai
from ragkit.llm_providers import make_llm_lmstudio, make_llm_openai
from ragkit.duckdb_store import make_duckdb_hybrid_retriever
from ragkit.rag_algorithms import rag_naive, rag_evo

def main():
    con = duckdb.connect("rag.duckdb")

    # Embeddings: escolha UM provider
    embed_fn = make_embed_lmstudio(
        base_url="http://localhost:1234",
        model="text-embedding-model"
    )
    # ou:
    # embed_fn = make_embed_openai(api_key=os.environ["OPENAI_API_KEY"], model="text-embedding-3-small")

    retriever = make_duckdb_hybrid_retriever(
        con,
        embed_fn=embed_fn,
        alpha=0.5,
        use_fts=True,
        use_vector=True,
        prefer_fts_macro=True,
    )

    # LLM: escolha UM provider
    llm = make_llm_lmstudio(
        base_url="http://localhost:1234",
        model="qwen2.5-32b-instruct"
    )
    # ou:
    # llm = make_llm_openai(api_key=os.environ["OPENAI_API_KEY"], model="gpt-4.1-mini")

    inp = {
        "query": "Com base no contexto, resuma o documento e aponte as 3 ideias principais.",
        "k": 6,
        "retriever": retriever,
        "llm": llm,
        "reranker": None,
        "filters": None,
        "max_context_chars": 12000,
        "extra": {},
    }

    out = rag_naive(inp)
    print(out["answer"])

    out_evo = rag_evo({**inp, "extra": {"rounds": 2, "confidence_mode": "heuristic", "confidence_threshold": 0.6}})
    print("\n=== RAG-EVO (MVP) ===\n", out_evo["answer"])
    print("Citations:", out["citations"])

if __name__ == "__main__":
    main()
