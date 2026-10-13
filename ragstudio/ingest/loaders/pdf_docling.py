"""PDF -> Markdown through Docling (heavy dependency, imported lazily; `pip install docling`).

Same pipeline as JudDoc_Ex / DecisionAI (standard PDF pipeline, OCR and table structure on, no picture images).
The converter is created once per process: building it loads the layout models, which takes seconds. The Markdown
is also written to Dados/Output/<name>.md so the exact text that was indexed can be inspected.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ...core import paths
from ...core.errors import ValidationError
from ...core.models import Document

MISSING = ("PDF loading needs Docling, which is not installed in this Python environment "
           "(pip install docling). Markdown, text and JSON files need nothing extra")
_converter: Any = None


def _docling() -> Any:
    global _converter
    if _converter is None:
        try:
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
            from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
        except ImportError as exc:
            raise ValidationError(MISSING) from exc
        options = PdfPipelineOptions()
        options.accelerator_options.num_threads = os.cpu_count() or 4
        options.do_ocr = True
        options.do_table_structure = True
        options.generate_picture_images = False
        _converter = DocumentConverter(format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_cls=StandardPdfPipeline, pipeline_options=options)})
    return _converter


def load(path: Path) -> list[Document]:
    from . import make_document, slugify
    converter = _docling()
    try:
        result = converter.convert(str(path))
        markdown = result.document.export_to_markdown()
        pages = len(getattr(result.document, "pages", {}) or {}) or None
    except Exception as exc:  # noqa: BLE001 - one unreadable PDF must not abort a whole folder
        raise ValidationError(f"{path.name}: PDF conversion failed ({type(exc).__name__}: {exc})") from exc
    out = paths.output_dir() / f"{slugify(path.stem)}.md"
    out.write_text(markdown, encoding="utf-8")
    return [make_document(slugify(path.stem), markdown, str(path), "pdf", pages=pages,
                          metadata={"markdown_path": str(out)})]
