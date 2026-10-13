# Catálogo de técnicas

Fonte de verdade: `./rs techniques list` (lido do `SPEC` de cada módulo). A tela Referências do aplicativo e
`./rs reference list` explicam cada técnica em português e em inglês, com custo em chamadas, limites e fontes.

**Nome e identificador.** Cada técnica tem um nome de exibição (`title`, por exemplo "Corrective RAG") e um
identificador estável (`name`, por exemplo `corrective`). O identificador é o que vai no runbook e o que fica gravado
com cada run; o nome de exibição aparece nas telas, nas figuras e nas tabelas dos relatórios. As exportações de
dados mantêm o identificador.

**Sobre o status.** `implemented` significa: código completo, no contrato comum, com teste de contrato e teste de
comportamento passando no provider `mock`. `prototype` significa escopo reduzido em relação ao artigo, descrito
abaixo e no docstring do módulo; a técnica avisa em `warnings` a cada resposta. **Só as 16 técnicas da primeira
versão foram executadas com um LLM real, pelo usuário, em 2026-10-12. As 12 novas e as 3 reescritas (`graph_rag`,
`raptor`, `agentic`) só rodaram com o provider `mock`.**

**Sobre as referências.** Os links foram conferidos em 2026-10-12 pela API do arXiv, pelo Crossref ou por resposta
HTTP 200.

## As 28 técnicas

| Nome | Identificador | Etapa | Status | O que faz | Referência |
|---|---|---|---|---|---|
| Naive RAG | `naive` | recuperação | implemented | Recupera top-k e responde | Lewis et al. 2020, https://arxiv.org/abs/2005.11401 |
| Hybrid RAG | `hybrid_rag` | recuperação | implemented | BM25 e busca densa combinadas por RRF ou soma ponderada | Cormack et al. 2009, https://doi.org/10.1145/1571941.1572114 |
| HyDE | `hyde` | consulta | implemented | Recupera com o embedding de um documento hipotético | Gao et al. 2023, https://aclanthology.org/2023.acl-long.99/ |
| Multi-Query RAG | `multi_query` | consulta | implemented | Reformulações da pergunta com pool único | Gupta et al. 2024, https://arxiv.org/abs/2410.12837 |
| RAG-Fusion | `rag_fusion` | consulta | implemented | Reformulações com rankings fundidos por RRF | Rackauckas 2024, https://arxiv.org/abs/2402.03367 |
| Query Decomposition | `decomposition` | consulta | implemented | Subperguntas escritas de uma vez, pool único | Gupta et al. 2024 |
| Step-Back Prompting | `step_back` | consulta | implemented | Recupera também com uma pergunta mais geral | Zheng et al. 2023, https://arxiv.org/abs/2310.06117 |
| MMR RAG | `mmr_rag` | recuperação | implemented | Recuperação com MMR | Carbonell & Goldstein 1998, https://dl.acm.org/doi/10.1145/290941.291025 |
| Contextual Compression | `context_compression` | pós-recuperação | implemented | LLM extrai de cada chunk só o que ajuda | Gupta et al. 2024 |
| Parent-Child Retrieval | `parent_child` | pós-recuperação | implemented | Busca filhos, envia os pais | sem artigo único |
| Sentence Window Retrieval | `sentence_window` | pós-recuperação | implemented | Expande o chunk com as sentenças vizinhas | sem artigo único |
| Contextual RAG | `contextual_retrieval` | documento e índice | implemented | Índice com uma frase de contexto por chunk | Anthropic 2024, https://www.anthropic.com/news/contextual-retrieval |
| RAPTOR | `raptor` | documento e índice | implemented | Árvore recursiva de resumos sobre clusters suaves | Sarthi et al. 2024, https://arxiv.org/abs/2401.18059 |
| Iterative RAG | `iterative` | orquestração | implemented | Rodadas de recuperar, responder e buscar a lacuna | Jiang et al. 2023, https://arxiv.org/abs/2305.06983 |
| Multi-Hop RAG | `multi_hop` | orquestração | implemented | Cadeia de subperguntas, cada uma buscada e respondida | Trivedi et al. 2022, https://arxiv.org/abs/2212.10509 |
| RAG-EVO | `rag_evo` | orquestração | implemented | Rodadas com MMR e escore de confiança | Rodrigues et al. 2025, https://link.springer.com/chapter/10.1007/978-3-032-05176-9_27 |
| Corrective RAG | `corrective` | orquestração | implemented | LLM avalia cada chunk, descarta e reconsulta | Yan et al. 2024, https://arxiv.org/abs/2401.15884 |
| Self-RAG | `self_rag` | orquestração | **prototype** | Decide recuperar, responde por trecho e escolhe pela autocrítica | Asai et al. 2023, https://arxiv.org/abs/2310.11511 |
| GraphRAG | `graph_rag` | documento e índice | implemented | Grafo com relatórios de comunidade; busca local e global | Edge et al. 2024, https://arxiv.org/abs/2404.16130 |
| LightRAG | `light_rag` | documento e índice | implemented | Dois níveis: palavras-chave contra entidades e contra relações | Guo et al. 2024, https://arxiv.org/abs/2410.05779 |
| HippoRAG | `hippo_rag` | documento e índice | implemented | Personalized PageRank a partir das entidades da pergunta | Gutiérrez et al. 2024, https://arxiv.org/abs/2405.14831 |
| Agentic RAG | `agentic` | orquestração | implemented | Plano e ferramentas de busca por tool calling nativo | Singh et al. 2025, https://arxiv.org/abs/2501.09136 |
| Adaptive RAG | `adaptive_rag` | orquestração | implemented | Classifica a complexidade e roteia a pergunta | Jeong et al. 2024, https://arxiv.org/abs/2403.14403 |
| RankRAG | `rank_rag` | pós-recuperação | **prototype** | O LLM gerador dá nota a 4k trechos e fica com os k melhores | Yu et al. 2024, https://arxiv.org/abs/2407.02485 |
| Long-Context RAG | `long_context` | pós-recuperação | implemented | A recuperação escolhe os documentos, e o modelo os lê inteiros | Jiang et al. 2024, https://arxiv.org/abs/2406.15319 |
| Hierarchical Retrieval | `hierarchical` | recuperação | implemented | Escolhe os documentos e depois busca chunks só dentro deles | Liu et al. 2021, https://arxiv.org/abs/2110.15439 |
| RECOMP | `recomp` | pós-recuperação | **prototype** | Comprime o recuperado em um resumo ou nas sentenças mais relevantes | Xu et al. 2023, https://arxiv.org/abs/2310.04408 |
| Speculative RAG | `speculative_rag` | orquestração | **prototype** | Rascunhos a partir de subconjuntos diversos; uma verificação escolhe | Wang et al. 2024, https://arxiv.org/abs/2407.08223 |

## Etapa do pipeline e eixos do runbook

Cada técnica declara a etapa em que atua (`SPEC.stage`) e as configurações do run que substitui pelas próprias
(`SPEC.ignores`). A tela Montar agrupa as técnicas por etapa, na ordem do fluxo:

| Etapa | O que a técnica muda | Técnicas |
|---|---|---|
| Documento e índice | o que é indexado, ou uma estrutura sobre o índice | `contextual_retrieval`, `raptor`, `graph_rag`, `light_rag`, `hippo_rag` |
| Consulta | a pergunta, antes da busca | `hyde`, `multi_query`, `rag_fusion`, `decomposition`, `step_back` |
| Recuperação | a forma de buscar | `naive`, `hybrid_rag`, `mmr_rag`, `hierarchical` |
| Pós-recuperação | reordena, comprime ou expande o que foi encontrado | `rank_rag`, `context_compression`, `recomp`, `parent_child`, `sentence_window`, `long_context` |
| Orquestração | quando e quantas vezes buscar e responder | `iterative`, `multi_hop`, `rag_evo`, `adaptive_rag`, `corrective`, `self_rag`, `speculative_rag`, `agentic` |

Chunking, store, modo de recuperação e reranker não são técnicas: são eixos do runbook, cruzados com todas elas.

### Poda de combinações

Ao expandir a grade, o runbook deixa de criar dois tipos de run (`prune: true`, o padrão):

- **Redundantes.** A técnica ignora um eixo, então variar esse eixo repetiria o mesmo run. Só o primeiro valor do
  eixo é mantido, o run registra `ignored_axes` e o eixo aparece como `n/a` nas tabelas.
- **Incompatíveis.** A técnica exige um índice que a combinação não constrói e se comportaria como `naive`.

| Técnica | Ignora | Exige |
|---|---|---|
| `mmr_rag` | modo de recuperação, reranker | |
| `hybrid_rag`, `raptor`, `hippo_rag`, `graph_rag` | modo de recuperação (`graph_rag` global: também o reranker) | |
| `rag_evo` | modo de recuperação, enquanto `use_mmr` for verdadeiro | |
| `light_rag` | modo de recuperação, fora do modo `mix` | |
| `naive` | modo de recuperação, quando o parâmetro `retrieval_mode` é dado | |
| `rank_rag`, `self_rag`, `corrective`, `speculative_rag` | reranker | |
| `parent_child` | reranker | chunking `parent_child` |
| `contextual_retrieval` | | `enrich: contextual` |
| `long_context` | `max_context_chars` (usa `context_chars`) | |

`experiments preview` e a tela Montar informam quantas combinações foram podadas e quais técnicas ficaram sem
nenhum run. `prune: false` no runbook mantém a grade inteira. Runbooks já criados não mudam.

## O que cada técnica não faz em relação ao artigo

| Técnica | Diferença |
|---|---|
| `self_rag` | **Protótipo.** O artigo treina um modelo para emitir tokens de reflexão e lê as suas probabilidades. Aqui cada reflexão (recuperar, relevância, apoio, utilidade) é um prompt separado ao LLM do run, e as candidatas são respostas inteiras, não segmentos com busca em feixe |
| `rank_rag` | **Protótipo.** O artigo treina um único modelo para ranquear e gerar. Aqui um LLM comum recebe um prompt e devolve notas de 0 a 10 |
| `adaptive_rag` | O classificador de complexidade do artigo é um modelo pequeno treinado; aqui é um prompt ao LLM do run |
| `graph_rag` | Comunidades por Louvain, não Leiden. Sem extração de alegações, sem resumo de subcomunidades, sem busca DRIFT. A fusão com a busca densa no modo local (`dense_fusion`) é um acréscimo desta implementação e pode ser desligada |
| `light_rag` | Sem atualização incremental do grafo e sem fusão de descrições duplicadas por LLM |
| `hippo_rag` | É o HippoRAG 1: sem os nós de passagem e o filtro de triplas do HippoRAG 2 |
| `raptor` | Mistura gaussiana com covariância diagonal. A redução usa UMAP só com o pacote `umap-learn` instalado; sem ele, PCA (o diagnóstico do run informa qual). O agrupamento global e depois local do artigo é substituído por reagrupar clusters que não cabem no resumidor |
| `agentic` | Um único agente, com ferramentas só sobre o índice (`search`, `keyword_search`, `read_more`, `finish`). Sem busca na web, SQL ou vários agentes |
| `recomp` | **Protótipo.** O artigo treina os dois compressores; aqui o resumo é um prompt ao LLM do run e as sentenças são ranqueadas pelo embedding do run |
| `speculative_rag` | **Protótipo.** O artigo usa um modelo pequeno treinado para rascunhar em paralelo e um maior para verificar; um run tem um único LLM, que faz os dois papéis em sequência |
| `hierarchical` | O artigo treina os recuperadores de documento e de passagem; aqui o vetor do documento é o embedding de um resumo ou a média dos chunks |
| `long_context` | Usa o próprio orçamento de contexto (`context_chars`, 48.000 por padrão) e ignora o do run |
| `corrective` | Sem o ramo de busca na web do CRAG |
| `iterative` | É a variante por rodadas do `ragkit`, não a recuperação ativa por token do FLARE |
| `hybrid_rag`, `rag_fusion` | Equivalem a `naive` em modo `rrf` e a `multi_query` com `fusion: rrf`. Existem como técnicas para entrar na comparação dentro de um mesmo run |

## Estruturas construídas na primeira pergunta

`raptor`, `graph_rag`, `light_rag` e `hippo_rag` constroem uma estrutura sobre o índice e a guardam junto dele
(`aux_*.json`). O custo cai na primeira pergunta do primeiro run que precisar (`diagnostics.built_now`).

- **Grafo de conhecimento:** 1 chamada ao LLM por chunk. **É extraído uma única vez por índice e usado pelas três
  técnicas de grafo** (`techniques/_kg.py`), desde que usem o mesmo LLM, idioma e os parâmetros
  `max_entities_per_chunk` e `entity_input_chars`.
- **Relatórios de comunidade** (`graph_rag`): mais 1 chamada por comunidade.
- **Árvore do RAPTOR:** 1 resumo por cluster em cada nível.
- **Resumos de documento** (`hierarchical`, modo `summary`): 1 chamada por documento.

Em um corpus grande isso é o maior custo do experimento. Confira o número de chunks do índice antes.

## Técnicas que podem responder sem recuperar

`adaptive_rag` (rota A), `self_rag` (quando o modelo julga a recuperação desnecessária) e `recomp` (quando o resumo
conclui que nada ajuda) podem responder com o conhecimento do próprio modelo. Nesse caso o contexto fica vazio e não
há citações. Para estudos em que toda resposta precisa vir do corpus, use `allow_no_retrieval: false`,
`adaptive_retrieval: false` e `selective: false`.

## Componentes transversais

| Componente | Opções | Onde |
|---|---|---|
| Modo de recuperação | `dense`, `bm25`, `hybrid` (soma ponderada), `rrf`, `mmr` | `retrieval_modes` no runbook |
| Reranker | `none`, `lexical`, `llm`, `cross_encoder` (adaptador, exige `sentence-transformers`; o modelo padrão é treinado em inglês) | `rerankers` no runbook |
| Chunking | `fixed`, `recursive` (maior limite natural que caiba), `sentence`, `semantic` (fronteiras por mudança de sentido; gasta 1 embedding por sentença na indexação), `markdown_headers`, `parent_child` | `chunking` no runbook |
| Store | `memory` (numpy, exato), `duckdb` (exige `duckdb`), `faiss` (`IndexFlatIP`, exato, exige `faiss-cpu`), `chroma` (HNSW cosseno, aproximado, exige `chromadb`). `faiss` não combina com o reranker `cross_encoder` | `store` no runbook |
| Enriquecimento | `contextual` | `enrich` no runbook |

## Ainda fora do catálogo

FLARE por token, SPLADE, ColBERT e late interaction, late chunking e chunking por proposições, TF-IDF, índices IVF e
PQ, Fusion-in-Decoder, recuperação multimodal e VisRAG, GraphRAG DRIFT, HippoRAG 2, e as versões de Self-RAG,
RankRAG, RECOMP e Speculative RAG com os modelos treinados dos artigos. Para incluir uma técnica siga `docs/adding-a-technique.md`.
