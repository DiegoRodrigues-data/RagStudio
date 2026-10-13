from typing import List, Dict, Any

def format_context(docs: List[Dict[str, Any]], max_chars: int) -> str:
    parts = []
    total = 0
    for d in docs:
        text = d.get("text", "")
        if not text:
            continue
        remain = max_chars - total
        if remain <= 0:
            break
        if len(text) > remain:
            text = text[:remain]
        parts.append(f"[{d.get('id','?')}] {text}")
        total += len(text)
    return "\n\n".join(parts)


def prompt_answer_only_from_context(query: str, context: str) -> str:
    return (
        "Use apenas o CONTEXTO para responder. Se faltar informação, diga exatamente o que falta.\n\n"
        f"PERGUNTA:\n{query}\n\n"
        f"CONTEXTO:\n{context}\n\n"
        "RESPOSTA:"
    )


def prompt_make_multi_queries(query: str, n: int) -> str:
    return (
        f"Gere {n} reformulações CURTAS e diferentes para buscar documentos sobre a pergunta.\n"
        "Retorne uma por linha, sem numeração.\n\n"
        f"PERGUNTA:\n{query}"
    )


def prompt_make_hypo_doc(query: str) -> str:
    return (
        "Escreva um parágrafo técnico (hipótese) que seria uma boa resposta à pergunta.\n"
        "Não invente fatos específicos, foque em termos e linguagem do domínio.\n\n"
        f"PERGUNTA:\n{query}\n\n"
        "HIPÓTESE:"
    )


def prompt_decompose(query: str, m: int) -> str:
    return (
        f"Quebre a pergunta em {m} subperguntas objetivas. Retorne uma por linha, sem numeração.\n\n"
        f"PERGUNTA:\n{query}"
    )


def prompt_extract_essential(query: str, text: str) -> str:
    return (
        "Extraia apenas frases essenciais do TEXTO para responder à PERGUNTA.\n"
        "Não invente; se não houver evidência, retorne vazio.\n\n"
        f"PERGUNTA:\n{query}\n\n"
        f"TEXTO:\n{text}\n\n"
        "TRECHOS ESSENCIAIS:"
    )


def prompt_gap_query(query: str, partial_answer: str) -> str:
    return (
        "Dada a PERGUNTA e a RESPOSTA PARCIAL, gere uma nova query curta para buscar lacunas.\n"
        "Apenas uma linha.\n\n"
        f"PERGUNTA: {query}\n"
        f"RESPOSTA PARCIAL: {partial_answer}\n"
        "NOVA QUERY:"
    )
