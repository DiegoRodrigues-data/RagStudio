from typing import List, Dict, Any
import re

def split_markdown_to_chunks(md: str, *, max_chars: int = 1500, overlap: int = 150) -> List[str]:
    """
    Chunking simples e robusto para Markdown:
    - quebra em parágrafos/linhas
    - monta blocos até max_chars com overlap
    """
    md = md.replace("\r\n", "\n")
    parts = [p.strip() for p in re.split(r"\n\n+", md) if p.strip()]
    chunks: List[str] = []

    buf = ""
    for p in parts:
        if not buf:
            buf = p
            continue

        if len(buf) + 2 + len(p) <= max_chars:
            buf = buf + "\n\n" + p
        else:
            chunks.append(buf)
            # overlap: pega o final do buf
            tail = buf[-overlap:] if overlap > 0 else ""
            buf = (tail + "\n\n" + p).strip()

    if buf:
        chunks.append(buf)

    return chunks


def build_chunk_docs(chunks: List[str], *, source_id: str, extra_meta: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    out = []
    extra_meta = extra_meta or {}
    for i, text in enumerate(chunks):
        out.append({
            "chunk_id": i,
            "text": text,
            "meta": {**extra_meta, "source_id": source_id, "chunk_id": i},
        })
    return out
