import pytest

from ragstudio.core.errors import ValidationError
from ragstudio.processing.chunking import chunk_document, normalize_config, recursive, semantic
from ragstudio.providers.mock import mock_embed

CONFIGS = [
    {"strategy": "fixed", "size": 200, "overlap": 40},
    {"strategy": "fixed", "size": 1000, "overlap": 0},
    {"strategy": "markdown_headers", "size": 250, "overlap": 30},
    {"strategy": "sentence", "size": 300, "overlap": 80},
    {"strategy": "parent_child", "size": 150, "overlap": 20, "parent_size": 500},
    {"strategy": "recursive", "size": 250, "overlap": 40},
    {"strategy": "recursive", "size": 60, "overlap": 0},
    {"strategy": "semantic", "size": 400, "overlap": 0},
    {"strategy": "semantic", "size": 120, "overlap": 0, "breakpoint_percentile": 50},
]


@pytest.mark.parametrize("config", CONFIGS, ids=lambda c: f"{c['strategy']}-{c['size']}")
def test_offsets_invariant_and_coverage(documents, config):
    for doc in documents:
        chunks = chunk_document(doc, config, mock_embed)
        assert chunks and [c.index for c in chunks] == list(range(len(chunks)))
        for c in chunks:
            assert doc.text[c.char_start:c.char_end] == c.text and c.text == c.text.strip() and c.text
            assert len(c.text) <= config["size"] + 1 and c.id == f"{doc.id}:{c.index}"
        covered = set()
        for c in chunks:
            covered.update(range(c.char_start, c.char_end))
        missing = [i for i, ch in enumerate(doc.text) if i not in covered and not ch.isspace()]
        assert not missing, f"characters not covered by any chunk: {missing[:5]}"


def test_overlap_is_applied(documents):
    chunks = chunk_document(documents[0], {"strategy": "fixed", "size": 200, "overlap": 50})
    assert any(a.char_end > b.char_start for a, b in zip(chunks, chunks[1:], strict=False))
    plain = chunk_document(documents[0], {"strategy": "fixed", "size": 200, "overlap": 0})
    assert all(a.char_end <= b.char_start for a, b in zip(plain, plain[1:], strict=False))


def test_markdown_headers_keep_heading_path(documents):
    chunks = chunk_document(documents[0], {"strategy": "markdown_headers", "size": 2000, "overlap": 0})
    assert [c.metadata["headings"] for c in chunks][:2] == [["Energia eólica"], ["Energia eólica", "Funcionamento"]]


def test_parent_child_spans(documents):
    doc = documents[0]
    chunks = chunk_document(doc, {"strategy": "parent_child", "size": 150, "overlap": 20, "parent_size": 500})
    for c in chunks:
        assert c.parent_id and c.metadata["parent_start"] <= c.char_start and c.char_end <= c.metadata["parent_end"]
    assert len({c.parent_id for c in chunks}) >= 2


def test_config_validation():
    assert list(normalize_config({"size": 500})) == ["overlap", "size", "strategy"]
    for bad in ({"strategy": "magic"}, {"size": 10}, {"size": 100, "overlap": 100}):
        with pytest.raises(ValidationError):
            normalize_config(bad)


def test_recursive_prefers_the_largest_boundary():
    text = "Primeiro parágrafo curto.\n\nSegundo parágrafo, um pouco mais longo. Tem duas frases.\n\nTerceiro."
    parts = recursive.pieces(text, 0, len(text), 60)
    assert "".join(text[a:b] for a, b in parts) == text and all(b - a <= 60 for a, b in parts)
    assert text[parts[0][0]:parts[0][1]] == "Primeiro parágrafo curto.\n\n", "paragraph breaks are tried first"
    spans = recursive.spans(text, size=60, overlap=0)
    assert [text[a:b].strip() for a, b, _ in spans][0] == "Primeiro parágrafo curto."
    assert all(a.strip() == a for a in ["x".join(text[s:e].split()) for s, e, _ in spans])
    assert recursive.pieces("a" * 130, 0, 130, 50) == [(0, 50), (50, 100), (100, 130)], "no separator: fixed width"
    counting = "Um. Dois. Três. Quatro. Cinco. Seis. Sete. Oito. Nove. Dez."
    overlapped = recursive.spans(counting, size=22, overlap=8)
    assert any(a[1] > b[0] for a, b in zip(overlapped, overlapped[1:], strict=False)), "trailing pieces are repeated"
    plain = recursive.spans(counting, size=22, overlap=0)
    assert all(a[1] <= b[0] for a, b in zip(plain, plain[1:], strict=False))


def test_semantic_breaks_where_the_topic_changes(documents):
    wind = "O vento move as turbinas eólicas. As turbinas eólicas giram com o vento forte."
    sun = "Os painéis solares captam a luz. A luz do sol alimenta os painéis solares."
    text = f"{wind} {sun}"
    spans = semantic.spans(text, size=1000, breakpoint_percentile=60, buffer=0, embed=mock_embed)
    assert [text[a:b] for a, b, _ in spans] == [wind, sun] and spans[0][2]["boundary"] == "semantic"
    capped = semantic.spans(text, size=50, breakpoint_percentile=60, buffer=0, embed=mock_embed)
    assert all(b - a <= 50 for a, b, _ in capped) and len(capped) == 4, "a group over the limit is cut at sentences"
    assert {meta["boundary"] for _, _, meta in capped} == {"size", "semantic", "end"}
    assert max(b - a for a, b, _ in semantic.spans("palavra " * 200, size=100, embed=mock_embed)) <= 100
    with pytest.raises(ValidationError, match="needs an embedder"):
        chunk_document(documents[0], {"strategy": "semantic"})
    with pytest.raises(ValidationError, match="breakpoint_percentile"):
        semantic.spans(text, breakpoint_percentile=100, embed=mock_embed)


def test_semantic_chunking_cost_is_recorded_with_the_index(documents):
    from ragstudio.experiments.index_builder import build_index
    from ragstudio.providers.routing import resolve_endpoint
    index, reused = build_index(documents, corpus_id="c", embedder=resolve_endpoint("embedding"), use_cache=False,
                                chunking={"strategy": "semantic", "size": 400, "overlap": 0})
    assert not reused and index.meta.build_usage["chunking_embedding_tokens"] > 0
    assert index.meta.chunking["strategy"] == "semantic" and len(index.all_chunks()) > len(documents)
    plain, _ = build_index(documents, corpus_id="c", embedder=resolve_endpoint("embedding"), use_cache=False,
                           chunking={"strategy": "recursive", "size": 400, "overlap": 0})
    assert plain.meta.build_usage["chunking_embedding_tokens"] == 0 and plain.meta.index_hash != index.meta.index_hash
