"""Component entries: the runbook axes that are not techniques (retrieval modes, rerankers, chunking, stores...)."""
from __future__ import annotations

from typing import Any

from .entry import entry

ENTRIES: list[dict[str, Any]] = [
    # ── retrieval modes ──────────────────────────────────────────────────────────────────────────────────────────
    entry("component.retrieval.dense", "component", "retrieval_mode", "dense",
          sources=("karpukhin2020", "reimers2019"), related=("concept.embedding", "component.retrieval.bm25"),
          pt={"summary": "Busca por similaridade de cosseno entre o embedding da pergunta e os embeddings dos chunks.",
              "when": "Padrão. Encontra trechos com o mesmo sentido mesmo sem palavras em comum.",
              "limits": "Fraca para termos exatos e raros: números de processo, siglas, nomes próprios, artigos de "
                        "lei. Depende do modelo de embedding e do idioma em que ele foi treinado."},
          en={"summary": "Cosine-similarity search between the question embedding and the chunk embeddings.",
              "when": "The default. Finds passages with the same meaning even without shared words.",
              "limits": "Weak for exact rare terms: case numbers, acronyms, proper names, statute articles. Depends "
                        "on the embedding model and the language it was trained on."}),
    entry("component.retrieval.bm25", "component", "retrieval_mode", "bm25",
          sources=("robertson2009",), related=("component.retrieval.dense", "component.retrieval.hybrid"),
          pt={"summary": "Busca lexical Okapi BM25: pontua chunks pelas palavras da pergunta, ponderadas por raridade.",
              "when": "Perguntas com termos exatos. Não usa embedding, então não gasta tokens na consulta e é a "
                      "linha de base lexical de qualquer comparação.",
              "limits": "Não reconhece sinônimo nem paráfrase. Não aplica stemming: honorário e honorários são "
                        "palavras diferentes."},
          en={"summary": "Okapi BM25 lexical search: scores chunks by the question's words, weighted by rarity.",
              "when": "Questions with exact terms. It uses no embedding, so it spends no query tokens and is the "
                      "lexical baseline of any comparison.",
              "limits": "No synonyms or paraphrase. No stemming: fee and fees are different words."}),
    entry("component.retrieval.hybrid", "component", "retrieval_mode", "hybrid",
          sources=("robertson2009",),
          related=("technique.hybrid_rag", "component.retrieval.rrf", "component.retrieval.dense"),
          pt={"summary": "Soma ponderada dos escores denso e BM25, cada um normalizado pelo seu máximo.",
              "how": "escore = dense_weight × denso + (1 − dense_weight) × bm25, com dense_weight 0,7 por padrão. "
                     "Cada busca traz max(4k, 20) candidatos.",
              "when": "Corpus em que convivem perguntas semânticas e perguntas por termo exato.",
              "limits": "O peso é um parâmetro a mais. A normalização pelo máximo é sensível a um escore muito "
                        "acima dos demais."},
          en={"summary": "Weighted sum of the dense and BM25 scores, each normalized by its maximum.",
              "how": "score = dense_weight × dense + (1 − dense_weight) × bm25, with dense_weight 0.7 by default. "
                     "Each search brings max(4k, 20) candidates.",
              "when": "Corpora where semantic questions and exact-term questions coexist.",
              "limits": "The weight is one more parameter. Max-normalization is sensitive to one score far above "
                        "the rest."}),
    entry("component.retrieval.rrf", "component", "retrieval_mode", "rrf",
          sources=("cormack2009",),
          related=("technique.rag_fusion", "technique.hybrid_rag", "component.retrieval.hybrid"),
          pt={"summary": "Reciprocal Rank Fusion: combina os rankings denso e BM25 pelas posições, não pelos escores.",
              "how": "escore = soma de 1 ÷ (rrf_k + posição) em cada ranking, com rrf_k 60 por padrão.",
              "when": "Alternativa ao hybrid sem peso para ajustar. Robusta quando os escores das duas buscas têm "
                      "escalas diferentes.",
              "limits": "Ignora o tamanho da diferença de escore: o primeiro colocado por muito vale o mesmo que o "
                        "primeiro por pouco."},
          en={"summary": "Reciprocal Rank Fusion: combines the dense and BM25 rankings by position, not score.",
              "how": "score = sum of 1 ÷ (rrf_k + rank) over the rankings, with rrf_k 60 by default.",
              "when": "An alternative to hybrid with no weight to tune. Robust when the two searches score on "
                      "different scales.",
              "limits": "Ignores the size of score gaps: first by far counts the same as first by little."}),
    entry("component.retrieval.mmr", "component", "retrieval_mode", "mmr",
          sources=("carbonell1998",), related=("technique.mmr_rag",),
          pt={"summary": "Maximal Marginal Relevance sobre os candidatos da busca densa.",
              "how": "Busca 40 candidatos e escolhe k maximizando lambda × relevância − (1 − lambda) × semelhança "
                     "com os já escolhidos, com lambda 0,6 por padrão. Lambda 1 é a própria busca densa.",
              "when": "Para reduzir chunks redundantes no contexto. Como modo do run, vale para todas as técnicas.",
              "limits": "Com sobreposição grande entre chunks vizinhos, o MMR tende a pular o vizinho que "
                        "completaria a resposta."},
          en={"summary": "Maximal Marginal Relevance over the dense search candidates.",
              "how": "Fetches 40 candidates and picks k maximizing lambda × relevance − (1 − lambda) × similarity to "
                     "those already picked, with lambda 0.6 by default. Lambda 1 is plain dense search.",
              "when": "To reduce redundant chunks in the context. As a run mode it applies to every technique.",
              "limits": "With large overlap between neighbouring chunks, MMR tends to skip the neighbour that would "
                        "complete the answer."}),
    # ── rerankers ────────────────────────────────────────────────────────────────────────────────────────────────
    entry("component.reranker.none", "component", "reranker", "none",
          related=("metric.mrr", "component.reranker.lexical"),
          pt={"summary": "Sem reordenação: os chunks seguem na ordem da recuperação.",
              "when": "Linha de base. Todo reranker deve ser comparado com none no mesmo índice e modo."},
          en={"summary": "No reordering: chunks keep the retrieval order.",
              "when": "The baseline. Every reranker should be compared with none on the same index and mode."}),
    entry("component.reranker.lexical", "component", "reranker", "lexical",
          related=("component.reranker.none", "component.retrieval.hybrid"),
          pt={"summary": "Heurística: 0,7 × escore da recuperação normalizado + 0,3 × fração dos termos da pergunta "
                         "presentes no chunk.",
              "when": "Reordenação barata, sem modelo e sem tokens.",
              "limits": "Só promove chunks que repetem as palavras da pergunta. Não é um modelo de relevância."},
          en={"summary": "Heuristic: 0.7 × normalized retrieval score + 0.3 × share of the question's terms present "
                         "in the chunk.",
              "when": "Cheap reordering with no model and no tokens.",
              "limits": "Only promotes chunks repeating the question's words. Not a relevance model."}),
    entry("component.reranker.llm", "component", "reranker", "llm",
          related=("component.reranker.cross_encoder", "metric.llm_calls"),
          pt={"summary": "O LLM recebe a pergunta e os candidatos numerados e devolve a ordem de relevância.",
              "how": "Uma chamada por pergunta, com até 20 candidatos de 600 caracteres cada. Números inválidos são "
                     "ignorados e os trechos omitidos mantêm a ordem original, então uma resposta malformada não "
                     "derruba o run.",
              "when": "Quando a ordenação importa e o custo de mais uma chamada é aceitável.",
              "limits": "Soma 1 chamada ao LLM por pergunta. Só os 600 primeiros caracteres de cada chunk são vistos."},
          en={"summary": "The LLM receives the question and the numbered candidates and returns the relevance order.",
              "how": "One call per question, with up to 20 candidates of 600 characters each. Invalid numbers are "
                     "ignored and omitted passages keep their original order, so a malformed answer does not fail "
                     "the run.",
              "when": "When ordering matters and one more call is affordable.",
              "limits": "Adds 1 LLM call per question. Only the first 600 characters of each chunk are seen."}),
    entry("component.reranker.cross_encoder", "component", "reranker", "cross_encoder",
          facts={"package": "sentence-transformers"},
          sources=("reimers2019", "sbert_cross", "msmarco_minilm"),
          related=("component.reranker.llm", "component.store.faiss"),
          pt={"summary": "Um modelo local lê a pergunta e o chunk juntos e devolve um escore de relevância.",
              "how": "Usa sentence-transformers com o modelo cross-encoder/ms-marco-MiniLM-L-6-v2 por padrão. Roda "
                     "na CPU ou na GPU da máquina, sem tokens de API.",
              "when": "Reordenação de qualidade sem custo por chamada.",
              "limits": "O modelo padrão foi treinado em inglês e sua qualidade em português não foi medida neste "
                        "projeto. Não pode ser combinado com o store faiss no macOS. Exige o pacote "
                        "sentence-transformers."},
          en={"summary": "A local model reads the question and the chunk together and returns a relevance score.",
              "how": "Uses sentence-transformers with the cross-encoder/ms-marco-MiniLM-L-6-v2 model by default. "
                     "Runs on the machine's CPU or GPU, with no API tokens.",
              "when": "Quality reordering with no per-call cost.",
              "limits": "The default model was trained on English and its quality on Portuguese was not measured in "
                        "this project. It cannot be combined with the faiss store on macOS. Needs the "
                        "sentence-transformers package."}),
    # ── chunking ─────────────────────────────────────────────────────────────────────────────────────────────────
    entry("component.chunking.fixed", "component", "chunking", "fixed",
          related=("concept.chunk", "component.chunking.sentence"),
          pt={"summary": "Janelas de tamanho fixo em caracteres, com sobreposição. Padrão: 1000 com 150.",
              "when": "Linha de base previsível, para qualquer formato de documento.",
              "limits": "Corta sentenças e tabelas no meio. A sobreposição reduz o problema e aumenta o índice."},
          en={"summary": "Fixed-size character windows with overlap. Default: 1000 with 150.",
              "when": "A predictable baseline for any document format.",
              "limits": "Cuts sentences and tables in the middle. Overlap reduces the problem and enlarges the index."}),
    entry("component.chunking.sentence", "component", "chunking", "sentence",
          related=("component.chunking.fixed", "technique.sentence_window"),
          pt={"summary": "Sentenças inteiras agrupadas até o tamanho definido, com sobreposição por sentenças finais.",
              "when": "Texto corrido. Com tamanhos pequenos, de 300 a 400, é a base da técnica sentence_window.",
              "limits": "A divisão usa pontuação. Abreviações como art. e fls. quebram sentenças no lugar errado."},
          en={"summary": "Whole sentences packed up to the given size, overlapping by trailing sentences.",
              "when": "Running text. With small sizes, 300 to 400, it is the basis of the sentence_window technique.",
              "limits": "Splitting relies on punctuation. Abbreviations such as art. and p. break sentences in the "
                        "wrong place."}),
    entry("component.chunking.markdown_headers", "component", "chunking", "markdown_headers",
          related=("component.chunking.fixed", "component.loader.docling"),
          pt={"summary": "Um chunk por seção Markdown, com o caminho de títulos guardado como metadado.",
              "when": "Documentos com títulos, inclusive PDFs convertidos pelo Docling, que saem em Markdown.",
              "limits": "Seções maiores que o tamanho caem em janelas fixas. Sem títulos no documento, equivale ao "
                        "fixed."},
          en={"summary": "One chunk per Markdown section, with the heading path kept as metadata.",
              "when": "Documents with headings, including PDFs converted by Docling, which come out as Markdown.",
              "limits": "Sections larger than the size fall back to fixed windows. Without headings it equals fixed."}),
    entry("component.chunking.recursive", "component", "chunking", "recursive",
          sources=("langchain_splitters",), related=("component.chunking.fixed", "component.chunking.sentence"),
          pt={"summary": "Corta no maior limite natural que faça os pedaços caberem, e depois os reagrupa até o "
                         "tamanho definido.",
              "how": "Tenta primeiro as quebras de parágrafo. Um pedaço ainda grande é cortado em quebras de linha, "
                     "depois em fins de sentença, em vírgulas, em espaços e, por último, em largura fixa. Pedaços "
                     "vizinhos são reunidos até o tamanho, com os finais repetidos como sobreposição.",
              "when": "Padrão razoável para texto com parágrafos: respeita a estrutura sem depender de títulos.",
              "limits": "Não entende o conteúdo, só a pontuação e as quebras. Em texto extraído de PDF com quebras "
                        "de linha no meio das frases, os cortes podem cair em lugares ruins."},
          en={"summary": "Cuts at the largest natural boundary that makes the pieces fit, then packs them back up "
                         "to the given size.",
              "how": "Paragraph breaks are tried first. A piece still too large is cut at line breaks, then at "
                     "sentence ends, commas, spaces and, last, at a fixed width. Neighbouring pieces are packed up "
                     "to the size, with trailing pieces repeated as overlap.",
              "when": "A reasonable default for text with paragraphs: it respects structure without relying on "
                      "headings.",
              "limits": "It does not understand content, only punctuation and breaks. On PDF-extracted text with "
                        "line breaks inside sentences, cuts may land in poor places."}),
    entry("component.chunking.semantic", "component", "chunking", "semantic",
          sources=("qu2024",), related=("component.chunking.sentence", "concept.embedding", "guide.cost"),
          pt={"summary": "Um chunk termina onde o sentido de sentenças consecutivas mais muda.",
              "how": "Cada sentença é convertida em embedding junto com as vizinhas. A distância de cosseno entre "
                     "sentenças consecutivas é calculada, e as posições acima do percentil breakpoint_percentile do "
                     "documento, 90 por padrão, viram fronteiras. Um grupo maior que o tamanho é cortado em "
                     "sentenças inteiras.",
              "when": "Documentos que mudam de assunto sem marcação visível, como transcrições e textos corridos.",
              "cost": "Um embedding por sentença na indexação, além dos embeddings dos chunks. O custo fica "
                      "registrado no índice como chunking_embedding_tokens.",
              "limits": "A sobreposição não é usada. Os chunks têm tamanhos muito variados. O estudo citado não "
                        "encontrou ganho consistente sobre o chunking fixo que justifique o custo: meça no seu "
                        "corpus antes de adotar."},
          en={"summary": "A chunk ends where the meaning of consecutive sentences changes the most.",
              "how": "Each sentence is embedded together with its neighbours. The cosine distance between "
                     "consecutive sentences is computed, and positions above the breakpoint_percentile of the "
                     "document, 90 by default, become boundaries. A group larger than the size is cut at whole "
                     "sentences.",
              "when": "Documents that change subject with no visible mark, such as transcripts and running text.",
              "cost": "One embedding per sentence at indexing, on top of the chunk embeddings. The cost is recorded "
                      "on the index as chunking_embedding_tokens.",
              "limits": "Overlap is not used. Chunk sizes vary widely. The cited study found no consistent gain "
                        "over fixed chunking that justifies the cost: measure on your corpus before adopting it."}),
    entry("component.chunking.parent_child", "component", "chunking", "parent_child",
          related=("technique.parent_child",),
          pt={"summary": "Chunks filhos pequenos são indexados, e cada um conhece o trecho pai maior que o contém.",
              "how": "Padrão: filhos de 300 caracteres com sobreposição de 50 e pais de 1500 sem sobreposição.",
              "when": "Exigido pela técnica parent_child. As demais técnicas usam só os filhos.",
              "limits": "Gera mais chunks e portanto mais embeddings que o fixed com o tamanho do pai."},
          en={"summary": "Small child chunks are indexed, each knowing the larger parent span that contains it.",
              "how": "Default: 300-character children with an overlap of 50 and 1500-character parents without "
                     "overlap.",
              "when": "Required by the parent_child technique. Other techniques use only the children.",
              "limits": "Produces more chunks, hence more embeddings, than fixed at the parent size."}),
    # ── stores ───────────────────────────────────────────────────────────────────────────────────────────────────
    entry("component.store.memory", "component", "store", "memory",
          related=("concept.index", "component.store.faiss"),
          pt={"summary": "Vetores em numpy e BM25 em memória, salvos em arquivos simples. Busca exata.",
              "when": "Padrão. Não tem dependência extra e serve de referência para os demais stores.",
              "limits": "Carrega todos os vetores na memória e compara com todos a cada consulta."},
          en={"summary": "Vectors in numpy and BM25 in memory, saved as plain files. Exact search.",
              "when": "The default. No extra dependency, and the reference for the other stores.",
              "limits": "Loads every vector in memory and compares against all of them on each query."}),
    entry("component.store.duckdb", "component", "store", "duckdb", facts={"package": "duckdb"},
          sources=("duckdb_docs",), related=("component.store.memory",),
          pt={"summary": "Índice em um arquivo DuckDB, com a busca vetorial feita pelo banco.",
              "when": "Quando se quer consultar o índice com SQL ou medir um store em disco.",
              "limits": "Exige o pacote duckdb."},
          en={"summary": "Index in one DuckDB file, with vector search done by the database.",
              "when": "To query the index with SQL or to measure an on-disk store.",
              "limits": "Needs the duckdb package."}),
    entry("component.store.faiss", "component", "store", "faiss", facts={"package": "faiss-cpu"},
          sources=("douze2024", "faiss_repo"), related=("component.store.chroma", "component.reranker.cross_encoder"),
          pt={"summary": "FAISS com IndexFlatIP sobre vetores normalizados: busca exata por cosseno.",
              "when": "Corpus maior, em que a busca em numpy fica lenta. Os resultados são os mesmos do store "
                      "memory.",
              "limits": "Não pode ser usado com o reranker cross_encoder: faiss e torch trazem cada um a sua "
                        "biblioteca OpenMP e o processo aborta no macOS. O runbook recusa essa combinação. Exige o "
                        "pacote faiss-cpu."},
          en={"summary": "FAISS with IndexFlatIP over normalized vectors: exact cosine search.",
              "when": "Larger corpora where numpy search gets slow. Results are the same as the memory store.",
              "limits": "It cannot be used with the cross_encoder reranker: faiss and torch each bundle their own "
                        "OpenMP library and the process aborts on macOS. The runbook rejects the combination. Needs "
                        "the faiss-cpu package."}),
    entry("component.store.chroma", "component", "store", "chroma", facts={"package": "chromadb"},
          sources=("chroma_docs", "malkov2016"), related=("component.store.faiss", "concept.index_hash"),
          pt={"summary": "Chroma persistente com índice HNSW em distância de cosseno: busca aproximada.",
              "when": "Para medir o efeito de um banco vetorial de uso comum em produção.",
              "limits": "Por ser aproximada, pode devolver vizinhos um pouco diferentes da busca exata. Em corpus "
                        "pequeno os resultados coincidem. Exige o pacote chromadb."},
          en={"summary": "Persistent Chroma with an HNSW index on cosine distance: approximate search.",
              "when": "To measure the effect of a vector database commonly used in production.",
              "limits": "Being approximate, it may return slightly different neighbours than exact search. On small "
                        "corpora results coincide. Needs the chromadb package."}),
    # ── indexing extras ──────────────────────────────────────────────────────────────────────────────────────────
    entry("component.enrich.contextual", "component", "indexing", "enrich: contextual",
          sources=("anthropic2024",), related=("technique.contextual_retrieval", "concept.index_hash"),
          pt={"summary": "Na indexação, o LLM escreve para cada chunk uma frase que o situa no documento, e ela é "
                         "incluída no texto indexado.",
              "how": "O chunk em si não muda, só o texto usado para embedding e BM25. Por isso offsets e trechos "
                     "gold continuam válidos.",
              "cost": "1 chamada ao LLM por chunk, uma única vez por índice. Em corpus grande é o maior custo do "
                      "experimento: confira o número de chunks antes.",
              "limits": "Gera um índice diferente, então a comparação com runs sem enriquecimento mistura técnica e "
                        "índice."},
          en={"summary": "At indexing, the LLM writes for each chunk a sentence situating it in the document, and it "
                         "is included in the indexed text.",
              "how": "The chunk itself does not change, only the text used for embedding and BM25. Offsets and gold "
                     "passages therefore stay valid.",
              "cost": "1 LLM call per chunk, once per index. On a large corpus it is the largest cost of the "
                      "experiment: check the chunk count first.",
              "limits": "It produces a different index, so comparing with non-enriched runs mixes technique and "
                        "index."}),
    entry("component.loader.docling", "component", "indexing", {"pt": "Importação de PDF (Docling)",
                                                               "en": "PDF import (Docling)"},
          facts={"package": "docling"}, sources=("auer2024", "docling_repo"),
          related=("component.chunking.markdown_headers", "concept.document"),
          pt={"summary": "PDFs são convertidos para Markdown pelo Docling na importação do corpus.",
              "when": "Automático para arquivos .pdf. Markdown, texto e JSON são lidos diretamente.",
              "limits": "A conversão leva alguns segundos por documento. A qualidade do texto extraído limita tudo "
                        "o que vem depois: abra o documento na tela Corpus e confira antes de experimentar."},
          en={"summary": "PDFs are converted to Markdown by Docling when the corpus is imported.",
              "when": "Automatic for .pdf files. Markdown, text and JSON are read directly.",
              "limits": "Conversion takes a few seconds per document. The quality of the extracted text bounds "
                        "everything after it: open the document in the Corpus screen and check before "
                        "experimenting."}),
]
