from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import json

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def doc_id_from_path(path: str) -> str:
    return _sha1(str(Path(path).resolve()))

def convert_pdfs_to_markdown(pdf_paths: List[str], *, output_dir: str) -> List[Dict[str, Any]]:
    """
    Converte PDFs para Markdown usando Docling.

    Retorna uma lista de dicts:
      {doc_id, source_path, markdown_path, meta_path}
    """
    from docling.document_converter import DocumentConverter

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()

    results: List[Dict[str, Any]] = []
    for p in pdf_paths:
        doc_id = doc_id_from_path(p)
        md_path = out_dir / f"{doc_id}.md"
        meta_path = out_dir / f"{doc_id}.json"

        result = converter.convert(p)
        md = result.document.export_to_markdown()
        # JSON "lossless" também existe no Docling, mas o método pode variar por versão.
        # Aqui salvamos metadados básicos.
        meta = {
            "doc_id": doc_id,
            "source_path": str(Path(p).resolve()),
        }

        md_path.write_text(md, encoding="utf-8")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        results.append({
            "doc_id": doc_id,
            "source_path": meta["source_path"],
            "markdown_path": str(md_path),
            "meta_path": str(meta_path),
        })

    return results
