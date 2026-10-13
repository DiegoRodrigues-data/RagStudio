"""Portuguese and English explanations of the built-in techniques, keyed by registry name.

The live facts (status, version, parameters, requirements, reference URL) always come from the registry; this file
only adds the prose. A technique without an entry here (an external plugin) falls back to its SPEC description.
`calls` is the number of LLM calls per question with default parameters, read from each `run()`.
"""
from __future__ import annotations

from typing import Any

FAMILIES: dict[str, dict[str, str]] = {
    "basic": {"pt": "Básica", "en": "Basic"},
    "query": {"pt": "Transformação da consulta", "en": "Query transformation"},
    "diversity": {"pt": "Diversidade", "en": "Diversity"},
    "context": {"pt": "Contexto", "en": "Context"},
    "structure": {"pt": "Estrutura do índice", "en": "Index structure"},
    "iterative": {"pt": "Iterativa", "en": "Iterative"},
    "self-evaluation": {"pt": "Autoavaliação", "en": "Self-evaluation"},
    "graph": {"pt": "Grafo", "en": "Graph"},
    "agent": {"pt": "Agente", "en": "Agent"},
    "routing": {"pt": "Roteamento", "en": "Routing"},
    "ranking": {"pt": "Ranqueamento", "en": "Ranking"},
}

TEXT: dict[str, dict[str, Any]] = {
    "naive": {
        "sources": ("lewis2020",), "related": ("concept.rag", "concept.k", "guide.fair_comparison"), "calls": "1",
        "pt": {"summary": "A linha de base: recupera os k chunks mais parecidos com a pergunta e responde com eles.",
               "how": "Uma busca com o modo de recuperação do run, reranker opcional, montagem do contexto e uma "
                      "chamada de geração.",
               "when": "Sempre. Toda comparação precisa do naive no mesmo índice para mostrar o que cada técnica "
                       "acrescenta.",
               "cost": "1 chamada ao LLM por pergunta. É o piso de custo e de latência.",
               "limits": "Falha quando a pergunta usa vocabulário diferente do documento ou quando a resposta está "
                         "espalhada em vários trechos."},
        "en": {"summary": "The baseline: retrieves the k chunks most similar to the question and answers from them.",
               "how": "One search with the run's retrieval mode, optional reranker, context assembly and one "
                      "generation call.",
               "when": "Always. Every comparison needs naive on the same index to show what each technique adds.",
               "cost": "1 LLM call per question. The floor for cost and latency.",
               "limits": "Fails when the question uses vocabulary unlike the document's or when the answer is spread "
                         "over several passages."}},
    "hyde": {
        "sources": ("gao2023",), "related": ("technique.multi_query", "component.retrieval.dense"), "calls": "2",
        "pt": {"summary": "O LLM escreve um documento hipotético que responderia a pergunta, e a busca usa o "
                          "embedding desse texto.",
               "how": "Uma chamada gera o texto hipotético. Seu vetor substitui o da pergunta, ou é combinado com "
                      "ele quando include_query está ligado. O mesmo texto serve de consulta lexical nos modos "
                      "bm25, hybrid e rrf.",
               "when": "Perguntas curtas ou coloquiais contra documentos longos e formais, em que pergunta e "
                       "resposta têm redações muito diferentes.",
               "cost": "2 chamadas por pergunta.",
               "limits": "Se o modelo inventar um documento errado, a busca segue a invenção. Em domínios que o "
                         "modelo conhece mal o ganho tende a sumir."},
        "en": {"summary": "The LLM writes a hypothetical document that would answer the question, and the search "
                          "uses the embedding of that text.",
               "how": "One call writes the hypothetical text. Its vector replaces the question's, or is averaged "
                      "with it when include_query is on. The same text is the lexical query in the bm25, hybrid and "
                      "rrf modes.",
               "when": "Short or colloquial questions against long formal documents, where question and answer are "
                       "worded very differently.",
               "cost": "2 calls per question.",
               "limits": "If the model invents a wrong document, the search follows the invention. In domains the "
                         "model knows poorly the gain tends to vanish."}},
    "mmr_rag": {
        "sources": ("carbonell1998",), "related": ("component.retrieval.mmr", "technique.naive"), "calls": "1",
        "pt": {"summary": "Recupera com Maximal Marginal Relevance, que troca um pouco de relevância por "
                          "diversidade entre os chunks.",
               "how": "Busca k_candidates candidatos e escolhe um a um o que maximiza lambda × similaridade com a "
                      "pergunta menos (1 − lambda) × similaridade com os já escolhidos. O reranker do run não é "
                      "aplicado, porque desfaria a diversidade.",
               "when": "Corpus com muito texto repetido ou quase duplicado, como modelos de decisão e cláusulas "
                       "padrão, e perguntas cuja resposta está em mais de um documento.",
               "cost": "1 chamada por pergunta. O custo extra é só de busca.",
               "limits": "Com lambda baixo traz chunks diversos e pouco relevantes. Varie lambda_ na grade do "
                         "runbook antes de concluir."},
        "en": {"summary": "Retrieves with Maximal Marginal Relevance, trading some relevance for diversity among "
                          "chunks.",
               "how": "Fetches k_candidates candidates and picks one at a time the one maximizing lambda × "
                      "similarity to the question minus (1 − lambda) × similarity to those already picked. The "
                      "run's reranker is not applied, since it would undo the diversity.",
               "when": "Corpora with much repeated or near-duplicate text, such as boilerplate rulings and standard "
                       "clauses, and questions answered across more than one document.",
               "cost": "1 call per question. The extra cost is search only.",
               "limits": "A low lambda brings diverse, weakly relevant chunks. Vary lambda_ in the runbook grid "
                         "before concluding."}},
    "multi_query": {
        "sources": ("gupta2024",), "related": ("technique.rag_fusion", "technique.decomposition"),
        "calls": "2",
        "pt": {"summary": "O LLM reescreve a pergunta de várias formas, busca com cada uma e junta os resultados.",
               "how": "Uma chamada gera n_queries reformulações. Cada uma recupera k chunks. O pool é unido pelo "
                      "maior escore, ou por RRF quando fusion é rrf. A técnica rag_fusion faz sempre a fusão por RRF.",
               "when": "Perguntas ambíguas ou com termos que têm sinônimos no corpus.",
               "cost": "2 chamadas por pergunta e n_queries buscas.",
               "limits": "As reformulações podem se desviar da intenção original. O diagnóstico do run mostra "
                         "quanto cada consulta contribuiu para os chunks finais."},
        "en": {"summary": "The LLM rewrites the question several ways, searches with each and pools the results.",
               "how": "One call writes n_queries reformulations. Each retrieves k chunks. The pool is merged by "
                      "best score, or by RRF when fusion is rrf. The rag_fusion technique always fuses by RRF.",
               "when": "Ambiguous questions, or terms with synonyms in the corpus.",
               "cost": "2 calls per question and n_queries searches.",
               "limits": "Reformulations may drift from the original intent. The run diagnostics show how much each "
                         "query contributed to the final chunks."}},
    "decomposition": {
        "sources": ("gupta2024",), "related": ("technique.multi_query", "technique.iterative"), "calls": "2",
        "pt": {"summary": "O LLM divide a pergunta em subperguntas e reúne o que cada uma recupera.",
               "how": "Uma chamada gera até n_subquestions subperguntas. Cada consulta recupera metade de k, no "
                      "mínimo 2. A resposta final é gerada uma única vez, sobre o pool reunido.",
               "when": "Perguntas compostas, que pedem dois ou mais fatos: quem decidiu e qual foi o valor.",
               "cost": "2 chamadas por pergunta e uma busca por subpergunta.",
               "limits": "As subperguntas não são respondidas uma a uma, então não há raciocínio em cadeia. Em "
                         "perguntas simples só acrescenta ruído."},
        "en": {"summary": "The LLM splits the question into sub-questions and pools what each one retrieves.",
               "how": "One call writes up to n_subquestions sub-questions. Each query retrieves half of k, at least "
                      "2. The final answer is generated once, over the pooled chunks.",
               "when": "Compound questions asking for two or more facts: who decided and what the amount was.",
               "cost": "2 calls per question and one search per sub-question.",
               "limits": "Sub-questions are not answered one by one, so there is no chained reasoning. On simple "
                         "questions it only adds noise."}},
    "step_back": {
        "sources": ("zheng2023stepback",), "related": ("technique.multi_query", "technique.hyde"), "calls": "2",
        "pt": {"summary": "Busca também com uma pergunta mais geral, escrita pelo LLM, para trazer o contexto de "
                          "fundo.",
               "how": "Uma chamada gera a pergunta geral. A pergunta original recupera k chunks e a geral recupera "
                      "k × step_back_share. Os dois conjuntos são unidos.",
               "when": "Perguntas muito específicas cuja resposta depende de uma regra ou definição apresentada em "
                       "outro ponto do documento.",
               "cost": "2 chamadas por pergunta e duas buscas.",
               "limits": "A pergunta geral pode trazer trechos genéricos que tomam o lugar da evidência específica."},
        "en": {"summary": "Also searches with a more general question, written by the LLM, to bring background.",
               "how": "One call writes the general question. The original retrieves k chunks and the general one "
                      "k × step_back_share. Both sets are merged.",
               "when": "Very specific questions whose answer depends on a rule or definition stated elsewhere in "
                       "the document.",
               "cost": "2 calls per question and two searches.",
               "limits": "The general question may bring generic passages that displace the specific evidence."}},
    "context_compression": {
        "sources": ("gupta2024",), "related": ("metric.context_coverage", "metric.context_chars"), "calls": "k + 1",
        "pt": {"summary": "Depois de recuperar, o LLM extrai de cada chunk só as sentenças úteis para a pergunta.",
               "how": "Uma chamada por chunk selecionado. Chunks que voltam vazios são descartados quando "
                      "drop_empty está ligado. A geração recebe o contexto reduzido.",
               "when": "Chunks grandes, k alto ou modelo com janela pequena. Também reduz distração por texto "
                       "irrelevante.",
               "cost": "k + 1 chamadas por pergunta. A chamada final fica mais barata, o total quase sempre mais "
                       "caro.",
               "limits": "O compressor pode cortar a evidência. Acompanhe context coverage: se cair em relação ao "
                         "naive, a compressão está perdendo informação."},
        "en": {"summary": "After retrieval, the LLM extracts from each chunk only the sentences useful to the "
                          "question.",
               "how": "One call per selected chunk. Chunks that come back empty are dropped when drop_empty is on. "
                      "Generation receives the reduced context.",
               "when": "Large chunks, high k or a model with a small window. Also reduces distraction by irrelevant "
                       "text.",
               "cost": "k + 1 calls per question. The final call gets cheaper, the total almost always dearer.",
               "limits": "The compressor may cut the evidence. Watch context coverage: if it drops against naive, "
                         "compression is losing information."}},
    "parent_child": {
        "sources": ("gupta2024",), "related": ("component.chunking.parent_child", "technique.sentence_window"),
        "calls": "1",
        "pt": {"summary": "Busca em chunks pequenos e envia ao modelo os trechos maiores que os contêm.",
               "how": "Recupera k × children_factor chunks filhos, troca cada um pelo seu trecho pai e remove pais "
                      "repetidos.",
               "when": "Quando chunks pequenos casam melhor com a pergunta, mas a resposta precisa do parágrafo "
                       "inteiro.",
               "cost": "1 chamada por pergunta, com contexto maior.",
               "limits": "Exige índice construído com a estratégia de chunking parent_child. Em outro índice a "
                         "técnica avisa e se comporta como o naive."},
        "en": {"summary": "Searches small chunks and sends the model the larger spans that contain them.",
               "how": "Retrieves k × children_factor child chunks, swaps each for its parent span and removes "
                      "repeated parents.",
               "when": "When small chunks match the question better but the answer needs the whole paragraph.",
               "cost": "1 call per question, with a larger context.",
               "limits": "Needs an index built with the parent_child chunking strategy. On another index the "
                         "technique warns and behaves like naive."}},
    "sentence_window": {
        "sources": ("gupta2024",), "related": ("technique.parent_child", "component.chunking.sentence"), "calls": "1",
        "pt": {"summary": "Expande cada chunk encontrado com as sentenças vizinhas no documento original.",
               "how": "Depois de selecionar os k chunks, acrescenta window sentenças antes e depois de cada um e "
                      "funde janelas que se sobrepõem.",
               "when": "Índices com chunks pequenos, por exemplo sentence com tamanho de 300 a 400 caracteres.",
               "cost": "1 chamada por pergunta, com contexto maior.",
               "limits": "Com chunks já grandes a janela acrescenta pouco e pode estourar max_context_chars."},
        "en": {"summary": "Expands each matched chunk with the neighbouring sentences in the source document.",
               "how": "After selecting the k chunks, adds window sentences before and after each and merges "
                      "overlapping windows.",
               "when": "Indices with small chunks, for example sentence with a size of 300 to 400 characters.",
               "cost": "1 call per question, with a larger context.",
               "limits": "With already large chunks the window adds little and may overflow max_context_chars."}},
    "contextual_retrieval": {
        "sources": ("anthropic2024",), "related": ("component.enrich.contextual", "concept.index_hash"), "calls": "1",
        "pt": {"summary": "Busca em um índice cujos chunks receberam, antes do embedding, uma frase que os situa no "
                          "documento.",
               "how": "O enriquecimento acontece na construção do índice, com uma chamada ao LLM por chunk. Na "
                      "consulta a técnica é uma busca comum, e o prefixo vai junto para o contexto quando "
                      "prefix_in_context está ligado.",
               "when": "Chunks que perdem o sentido fora do documento: quem é a parte, de que processo se fala, a "
                       "que contrato a cláusula pertence.",
               "cost": "1 chamada por pergunta. O custo alto é único e fica na indexação.",
               "limits": "Exige enrich: contextual no runbook, o que gera outro índice. Sem isso a técnica avisa e "
                         "equivale ao naive."},
        "en": {"summary": "Searches an index whose chunks were given, before embedding, a sentence situating them "
                          "in the document.",
               "how": "Enrichment happens at index build, with one LLM call per chunk. At query time the technique "
                      "is an ordinary search, and the prefix goes into the context when prefix_in_context is on.",
               "when": "Chunks that lose meaning outside the document: who the party is, which case, which contract "
                       "the clause belongs to.",
               "cost": "1 call per question. The high cost is one-off and sits in indexing.",
               "limits": "Needs enrich: contextual in the runbook, which creates another index. Without it the "
                         "technique warns and equals naive."}},
    "corrective": {
        "sources": ("yan2024",), "related": ("technique.self_rag", "technique.naive", "component.reranker.llm"),
        "calls": "2k + 1 … 4k + 2",
        "pt": {"summary": "O LLM julga a relevância de cada chunk recuperado, descarta os irrelevantes e refaz a "
                          "busca quando sobra pouco.",
               "how": "Recupera k × candidates_factor candidatos e avalia cada um com uma chamada. Se menos de "
                      "min_relevant sobrevivem, reescreve a pergunta, busca de novo e avalia os novos.",
               "when": "Corpus ruidoso, em que a busca traz trechos parecidos e errados, e quando responder com "
                       "evidência ruim é pior que gastar mais.",
               "cost": "Com os padrões, 2k avaliações mais a geração. Uma correção acrescenta 1 reescrita e até 2k "
                       "avaliações.",
               "limits": "É o laço avaliar e corrigir sobre o índice local. A busca na web do CRAG não está "
                         "implementada. A autocrítica da resposta é o que faz a técnica self_rag."},
        "en": {"summary": "The LLM grades the relevance of each retrieved chunk, drops the irrelevant ones and "
                          "searches again when too few remain.",
               "how": "Retrieves k × candidates_factor candidates and grades each with one call. If fewer than "
                      "min_relevant survive, it rewrites the question, searches again and grades the new ones.",
               "when": "Noisy corpora where search brings similar but wrong passages, and when answering from bad "
                       "evidence is worse than spending more.",
               "cost": "With defaults, 2k gradings plus generation. A correction adds 1 rewrite and up to 2k "
                       "gradings.",
               "limits": "It is the grade-and-correct loop over the local index. CRAG's web search is not "
                         "implemented. Critiquing the answer itself is what the self_rag technique does."}},
    "iterative": {
        "sources": ("jiang2023",), "related": ("technique.multi_hop", "technique.rag_evo", "technique.agentic"),
        "calls": "2 × rounds − 1",
        "pt": {"summary": "Rodadas de recuperar e responder. Cada rodada busca o que falta na resposta parcial.",
               "how": "Em cada rodada: busca, seleção e resposta. Entre rodadas, o LLM escreve uma consulta para a "
                      "lacuna da resposta. O pool de chunks se acumula e a última resposta é a final.",
               "when": "Perguntas que precisam de mais de um salto, em que a primeira busca só revela o que "
                       "procurar a seguir.",
               "cost": "Com 2 rodadas, 3 chamadas por pergunta.",
               "limits": "É a variante por rodadas vinda do ragkit, não a recuperação ativa por token do FLARE. "
                         "Não há critério de parada: sempre executa todas as rodadas."},
        "en": {"summary": "Rounds of retrieval and answering. Each round searches for what the partial answer lacks.",
               "how": "Each round: search, selection and answer. Between rounds the LLM writes a query for the gap "
                      "in the answer. The chunk pool accumulates and the last answer is final.",
               "when": "Questions needing more than one hop, where the first search only reveals what to look for "
                       "next.",
               "cost": "With 2 rounds, 3 calls per question.",
               "limits": "It is the round-based variant from ragkit, not FLARE's token-level active retrieval. "
                         "There is no stopping rule: every round always runs."}},
    "rag_evo": {
        "sources": ("rodrigues2025", "carbonell1998"), "related": ("technique.iterative", "technique.mmr_rag"),
        "calls": "1 … 2 × rounds − 1",
        "pt": {"summary": "Rodadas com MMR e um escore de confiança: para quando a resposta é boa o bastante e "
                          "entrega a mais bem pontuada.",
               "how": "Cada rodada recupera com MMR, responde e calcula a confiança. No modo composite ela combina "
                      "tamanho da resposta, entropia lexical e cobertura do contexto com os pesos alpha, beta e "
                      "gamma. Abaixo de confidence_threshold, uma consulta de lacuna dispara outra rodada.",
               "when": "Mesmos casos do iterative, quando se quer gastar rodadas extras só nas perguntas difíceis.",
               "cost": "De 1 chamada, se a primeira resposta atinge o limiar, até 3 com 2 rodadas. O modo de "
                       "confiança llm acrescenta chamadas.",
               "limits": "A confiança composta é uma heurística de forma e não verifica correção. Calibre o limiar "
                         "no seu corpus antes de comparar custo."},
        "en": {"summary": "Rounds with MMR and a confidence score: stops when the answer is good enough and returns "
                          "the best-scored one.",
               "how": "Each round retrieves with MMR, answers and computes confidence. In composite mode it "
                      "combines answer length, lexical entropy and context coverage with weights alpha, beta and "
                      "gamma. Below confidence_threshold, a gap query triggers another round.",
               "when": "The same cases as iterative, when extra rounds should be spent only on hard questions.",
               "cost": "From 1 call, when the first answer reaches the threshold, up to 3 with 2 rounds. The llm "
                       "confidence mode adds calls.",
               "limits": "Composite confidence is a heuristic of form and does not check correctness. Calibrate the "
                         "threshold on your corpus before comparing cost."}},
    "hybrid_rag": {
        "sources": ("cormack2009", "robertson2009"),
        "related": ("component.retrieval.rrf", "component.retrieval.hybrid", "technique.naive"), "calls": "1",
        "pt": {"summary": "Combina a busca lexical BM25 com a busca semântica densa e responde.",
               "how": "Uma busca no modo rrf, que funde os dois rankings pelas posições, ou no modo hybrid, que soma "
                      "os escores normalizados quando fusion é weighted. O modo de recuperação do run é ignorado.",
               "when": "Corpus em que convivem perguntas por sentido e perguntas por termo exato, como números de "
                       "processo, siglas e nomes próprios.",
               "cost": "1 chamada por pergunta. O custo extra é só de busca.",
               "limits": "O mesmo efeito se obtém com naive em um run de modo rrf ou hybrid. Esta técnica existe "
                         "para comparar a busca híbrida com as demais dentro de um mesmo run."},
        "en": {"summary": "Combines lexical BM25 search with dense semantic search and answers.",
               "how": "One search in rrf mode, which fuses the two rankings by position, or in hybrid mode, which "
                      "sums normalized scores when fusion is weighted. The run's retrieval mode is ignored.",
               "when": "Corpora where questions by meaning and questions by exact term coexist, such as case "
                       "numbers, acronyms and proper names.",
               "cost": "1 call per question. The extra cost is search only.",
               "limits": "The same effect comes from naive in a run with rrf or hybrid mode. This technique exists "
                         "to compare hybrid search with the others inside one run."}},
    "rag_fusion": {
        "sources": ("rackauckas2024", "cormack2009"),
        "related": ("technique.multi_query", "component.retrieval.rrf"), "calls": "2",
        "pt": {"summary": "O LLM reescreve a pergunta de várias formas, e os rankings de cada versão são fundidos "
                          "por Reciprocal Rank Fusion.",
               "how": "Uma chamada gera as reformulações. Cada consulta recupera 2k chunks. O RRF soma 1 ÷ (rrf_k + "
                      "posição) em cada ranking, o que favorece os chunks em que várias consultas concordam.",
               "when": "Perguntas ambíguas ou com sinônimos no corpus, quando se quer robustez a uma reformulação "
                       "ruim.",
               "cost": "2 chamadas por pergunta e n_queries buscas.",
               "limits": "Um chunk muito relevante para uma única consulta pode perder para chunks medianos em "
                         "todas. Compare com multi_query, que mantém o melhor escore."},
        "en": {"summary": "The LLM rewrites the question several ways, and the rankings of each version are fused "
                          "by Reciprocal Rank Fusion.",
               "how": "One call writes the reformulations. Each query retrieves 2k chunks. RRF adds 1 ÷ (rrf_k + "
                      "rank) over the rankings, favouring chunks several queries agree on.",
               "when": "Ambiguous questions or synonyms in the corpus, when robustness to one bad reformulation "
                       "matters.",
               "cost": "2 calls per question and n_queries searches.",
               "limits": "A chunk highly relevant to a single query may lose to chunks that are average for all. "
                         "Compare with multi_query, which keeps the best score."}},
    "multi_hop": {
        "sources": ("trivedi2022",),
        "related": ("technique.iterative", "technique.decomposition", "technique.adaptive_rag"),
        "calls": "3 … 2 × max_hops + 1",
        "pt": {"summary": "Responde por uma cadeia de subperguntas: cada salto é escrito a partir dos fatos já "
                          "encontrados, buscado e respondido.",
               "how": "Em cada salto o LLM lê os fatos acumulados e escreve a próxima subpergunta, ou para. A busca "
                      "traz k chunks, e o LLM responde a subpergunta em uma frase. A resposta final é gerada uma "
                      "vez, com os melhores chunks de cada salto intercalados.",
               "when": "Perguntas em que um fato leva ao outro: quem relatou o processo citado na decisão X. A "
                       "segunda busca depende da resposta da primeira.",
               "cost": "2 chamadas por salto, mais a decisão de parar e a resposta final. Com os padrões, de 3 a 7.",
               "limits": "Um erro no primeiro salto se propaga. Difere do iterative, que responde a pergunta inteira "
                         "a cada rodada, e do decomposition, que escreve todas as subperguntas antes de buscar."},
        "en": {"summary": "Answers through a chain of sub-questions: each hop is written from the facts already "
                          "found, retrieved and answered.",
               "how": "At each hop the LLM reads the accumulated facts and writes the next sub-question, or stops. "
                      "The search brings k chunks, and the LLM answers the sub-question in one sentence. The final "
                      "answer is generated once, with the best chunks of each hop interleaved.",
               "when": "Questions where one fact leads to the next: who reported the case cited in ruling X. The "
                       "second search depends on the answer to the first.",
               "cost": "2 calls per hop, plus the stop decision and the final answer. With defaults, 3 to 7.",
               "limits": "An error in the first hop propagates. It differs from iterative, which answers the whole "
                         "question every round, and from decomposition, which writes every sub-question before "
                         "searching."}},
    "adaptive_rag": {
        "sources": ("jeong2024",),
        "related": ("technique.naive", "technique.multi_hop", "technique.self_rag"), "calls": "2 … 2 × max_hops + 2",
        "pt": {"summary": "Classifica a complexidade da pergunta e escolhe a estratégia mais barata capaz de "
                          "respondê-la.",
               "how": "Uma chamada classifica a pergunta em A, B ou C. A: responde sem recuperação. B: uma busca e "
                      "uma resposta, como o naive. C: a cadeia de subperguntas do multi_hop.",
               "when": "Conjuntos de perguntas mistos, com perguntas simples e compostas, em que usar sempre a "
                       "estratégia mais cara é desperdício.",
               "cost": "1 chamada de classificação mais a rota escolhida: 2 no total para A e B, até 8 para C.",
               "limits": "O artigo treina um classificador pequeno. Aqui a classificação é um prompt ao LLM do run. "
                         "Na rota A a resposta vem da memória do modelo, sem contexto e sem citações: use "
                         "allow_no_retrieval falso quando toda resposta precisa vir do corpus."},
        "en": {"summary": "Classifies the complexity of the question and picks the cheapest strategy able to "
                          "answer it.",
               "how": "One call classifies the question as A, B or C. A: answers without retrieval. B: one search "
                      "and one answer, like naive. C: the sub-question chain of multi_hop.",
               "when": "Mixed question sets, with simple and compound questions, where always using the dearest "
                       "strategy is wasteful.",
               "cost": "1 classification call plus the chosen route: 2 in total for A and B, up to 8 for C.",
               "limits": "The paper trains a small classifier. Here classification is a prompt to the run's LLM. On "
                         "route A the answer comes from the model's memory, with no context and no citations: set "
                         "allow_no_retrieval to false when every answer must come from the corpus."}},
    "self_rag": {
        "sources": ("asai2023",),
        "related": ("technique.corrective", "technique.adaptive_rag", "metric.faithfulness"),
        "calls": "2 … 2k + 7",
        "pt": {"summary": "Decide se precisa recuperar, gera uma resposta a partir de cada trecho relevante e fica "
                          "com a que a própria crítica avalia melhor.",
               "how": "O modelo decide se a pergunta exige recuperação. Se sim, avalia a relevância de 2k trechos, "
                      "gera uma resposta candidata de cada um dos 3 melhores, isoladamente, e critica cada "
                      "candidata: quanto o trecho a sustenta e quão útil ela é. Vence a de melhor nota ponderada.",
               "when": "Quando responder sem apoio é o risco principal e o custo por pergunta pode ser alto.",
               "cost": "Com os padrões: 1 decisão, 2k avaliações, 3 respostas e 3 críticas. Sem recuperação, 2 "
                       "chamadas.",
               "limits": "Protótipo. O artigo usa um modelo treinado para emitir tokens de reflexão e lê as suas "
                         "probabilidades. Aqui cada reflexão é um prompt separado ao LLM do run, e as candidatas são "
                         "respostas inteiras, não segmentos com busca em feixe. A resposta usa um único trecho."},
        "en": {"summary": "Decides whether to retrieve, generates an answer from each relevant passage and keeps "
                          "the one its own critique rates best.",
               "how": "The model decides whether the question needs retrieval. If so it grades the relevance of 2k "
                      "passages, generates a candidate answer from each of the best 3, in isolation, and critiques "
                      "each candidate: how much the passage supports it and how useful it is. The best weighted "
                      "score wins.",
               "when": "When answering without support is the main risk and the cost per question can be high.",
               "cost": "With defaults: 1 decision, 2k gradings, 3 answers and 3 critiques. Without retrieval, 2 "
                       "calls.",
               "limits": "Prototype. The paper uses a model trained to emit reflection tokens and reads their "
                         "probabilities. Here each reflection is a separate prompt to the run's LLM, and candidates "
                         "are whole answers, not segments under beam search. The answer uses a single passage."}},
    "rank_rag": {
        "sources": ("yu2024",),
        "related": ("component.reranker.llm", "technique.corrective", "metric.mrr"), "calls": "2",
        "pt": {"summary": "O mesmo LLM que responde dá nota a um conjunto maior de trechos recuperados e fica com "
                          "os k melhores.",
               "how": "Recupera 4k candidatos. O LLM atribui a cada um uma nota de 0 a 10 pela utilidade para a "
                      "pergunta, em uma única chamada ou em uma chamada por trecho quando scoring é pointwise. "
                      "Trechos abaixo de min_score são descartados.",
               "when": "Quando o trecho certo costuma estar entre os 20 primeiros e fora dos 5 primeiros.",
               "cost": "2 chamadas por pergunta no modo batch, ou 4k + 1 no modo pointwise.",
               "limits": "Protótipo. O artigo treina um único modelo para ranquear e gerar e lê a relevância das "
                         "probabilidades dos tokens. Aqui um LLM comum recebe um prompt e devolve notas. O reranker "
                         "do run não é aplicado."},
        "en": {"summary": "The same LLM that answers scores a larger set of retrieved passages and keeps the best "
                          "k.",
               "how": "Retrieves 4k candidates. The LLM gives each a 0 to 10 score for usefulness to the question, "
                      "in one call or in one call per passage when scoring is pointwise. Passages below min_score "
                      "are dropped.",
               "when": "When the right passage is usually within the first 20 and outside the first 5.",
               "cost": "2 calls per question in batch mode, or 4k + 1 in pointwise mode.",
               "limits": "Prototype. The paper tunes a single model to rank and generate and reads relevance from "
                         "token probabilities. Here an ordinary LLM is prompted and returns scores. The run's "
                         "reranker is not applied."}},
    "graph_rag": {
        "sources": ("edge2024", "blondel2008", "traag2019"),
        "related": ("technique.light_rag", "technique.hippo_rag", "technique.raptor", "guide.cost"), "calls": "1",
        "pt": {"summary": "Grafo de conhecimento com relatórios de comunidade, consultado pelas entidades da "
                          "pergunta ou por map-reduce sobre os relatórios.",
               "how": "Na indexação o LLM extrai de cada chunk entidades e relações tipadas, com descrições. As "
                      "entidades são agrupadas em comunidades hierárquicas, e o LLM escreve um relatório por "
                      "comunidade. No modo local, as entidades da pergunta levam aos chunks, e o relatório da "
                      "comunidade mais próxima entra no contexto. No modo global, cada relatório é consultado e os "
                      "pontos mais bem avaliados formam o contexto.",
               "when": "Local: perguntas sobre entidades e suas relações. Global: perguntas sobre o conjunto, como "
                       "quais são os temas principais do corpus, que nenhum trecho isolado responde.",
               "cost": "Local: 1 chamada por pergunta. Global: 1 por relatório consultado, 8 por padrão, mais a "
                       "resposta. A construção custa 1 chamada por chunk mais 1 por comunidade, uma vez por índice.",
               "limits": "As comunidades usam Louvain e não Leiden. A extração de alegações, o resumo de "
                         "subcomunidades e a busca DRIFT não estão implementados. No modo global o contexto são "
                         "relatórios, então as métricas de recuperação por trecho gold não se aplicam."},
        "en": {"summary": "A knowledge graph with community reports, queried through the question's entities or by "
                          "map-reduce over the reports.",
               "how": "At indexing the LLM extracts typed entities and relations, with descriptions, from every "
                      "chunk. Entities are grouped into hierarchical communities, and the LLM writes one report per "
                      "community. In local mode the question's entities lead to chunks, and the report of the "
                      "closest community joins the context. In global mode each report is consulted and the "
                      "best-rated points form the context.",
               "when": "Local: questions about entities and their relations. Global: questions about the whole, "
                       "such as the main themes of the corpus, which no single passage answers.",
               "cost": "Local: 1 call per question. Global: 1 per consulted report, 8 by default, plus the answer. "
                       "Building costs 1 call per chunk plus 1 per community, once per index.",
               "limits": "Communities use Louvain, not Leiden. Claim extraction, sub-community summaries and DRIFT "
                         "search are not implemented. In global mode the context is reports, so gold-passage "
                         "retrieval metrics do not apply."}},
    "light_rag": {
        "sources": ("guo2024",),
        "related": ("technique.graph_rag", "technique.hippo_rag", "technique.hybrid_rag"), "calls": "2",
        "pt": {"summary": "Recuperação em dois níveis sobre um grafo de conhecimento: termos específicos casam com "
                          "entidades e temas gerais casam com relações.",
               "how": "O LLM extrai da pergunta palavras-chave de baixo nível, como entidades e termos, e de alto "
                      "nível, como temas. As primeiras são comparadas com as entidades do grafo, as segundas com as "
                      "relações. Os chunks ligados a elas são ranqueados e, no modo mix, fundidos por RRF com a "
                      "busca vetorial. O contexto leva também um trecho com as entidades e relações encontradas.",
               "when": "Perguntas que misturam um detalhe específico e um tema amplo. É mais barato na consulta que "
                       "o GraphRAG global.",
               "cost": "2 chamadas por pergunta. A construção custa 1 chamada por chunk, uma vez por índice, e é "
                       "compartilhada com graph_rag e hippo_rag.",
               "limits": "A atualização incremental do grafo e a fusão de descrições duplicadas por LLM não estão "
                         "implementadas. A qualidade depende das descrições extraídas."},
        "en": {"summary": "Dual-level retrieval over a knowledge graph: specific terms match entities and broad "
                          "themes match relations.",
               "how": "The LLM extracts from the question low-level keywords, such as entities and terms, and "
                      "high-level ones, such as themes. The former are compared with the graph's entities, the "
                      "latter with its relations. The chunks linked to them are ranked and, in mix mode, fused by "
                      "RRF with vector search. The context also carries a passage with the matched entities and "
                      "relations.",
               "when": "Questions mixing a specific detail and a broad theme. Cheaper at query time than global "
                       "GraphRAG.",
               "cost": "2 calls per question. Building costs 1 call per chunk, once per index, shared with "
                       "graph_rag and hippo_rag.",
               "limits": "Incremental graph updates and LLM merging of duplicate descriptions are not implemented. "
                         "Quality depends on the extracted descriptions."}},
    "hippo_rag": {
        "sources": ("gutierrez2024", "haveliwala2002"),
        "related": ("technique.graph_rag", "technique.light_rag", "technique.multi_hop"), "calls": "2",
        "pt": {"summary": "Recuperação associativa: o Personalized PageRank espalha relevância a partir das "
                          "entidades da pergunta por um grafo de conhecimento.",
               "how": "O LLM extrai as entidades da pergunta. Cada uma é ligada a um nó do grafo, pelo nome ou pelo "
                      "embedding mais próximo. O PageRank parte desses nós, com peso maior para entidades raras, e "
                      "percorre as relações e as arestas de sinônimo. Um chunk soma a probabilidade das entidades "
                      "que menciona.",
               "when": "Perguntas de vários saltos, em que a evidência está em trechos ligados por entidades em "
                       "comum. Uma única passada alcança o que o multi_hop buscaria em várias chamadas.",
               "cost": "2 chamadas por pergunta. A construção do grafo é compartilhada com graph_rag e light_rag.",
               "limits": "Se nenhuma entidade da pergunta existe no grafo, a técnica usa a busca densa e avisa. Em "
                         "grafos esparsos pode entregar menos de k chunks. Os nós de passagem e o filtro de triplas "
                         "do HippoRAG 2 não estão implementados."},
        "en": {"summary": "Associative retrieval: Personalized PageRank spreads relevance from the question's "
                          "entities across a knowledge graph.",
               "how": "The LLM extracts the question's entities. Each is linked to a graph node, by name or by "
                      "nearest embedding. PageRank starts from those nodes, weighting rare entities more, and "
                      "follows relations and synonym edges. A chunk adds up the probability of the entities it "
                      "mentions.",
               "when": "Multi-hop questions whose evidence lies in passages linked by shared entities. A single "
                       "pass reaches what multi_hop would search over several calls.",
               "cost": "2 calls per question. Graph building is shared with graph_rag and light_rag.",
               "limits": "If no entity of the question exists in the graph, the technique uses dense search and "
                         "warns. On sparse graphs it may deliver fewer than k chunks. The passage nodes and triple "
                         "filter of HippoRAG 2 are not implemented."}},
    "raptor": {
        "sources": ("sarthi2024", "mcinnes2018"),
        "related": ("technique.graph_rag", "metric.latency", "guide.cost"), "calls": "1",
        "pt": {"summary": "Árvore de resumos recursivos sobre grupos de chunks, consultada junto com os chunks.",
               "how": "Os embeddings são reduzidos e agrupados por mistura gaussiana, com o número de grupos "
                      "escolhido por BIC. O agrupamento é suave: um chunk pode alimentar mais de um resumo. O LLM "
                      "resume cada grupo, e os resumos são agrupados de novo, até max_levels. Na consulta, o modo "
                      "collapsed põe chunks e resumos de todos os níveis em um só ranking. O modo tree_traversal "
                      "desce da raiz escolhendo os filhos mais parecidos.",
               "when": "Perguntas de síntese, cuja resposta está espalhada por um documento ou por vários.",
               "cost": "1 chamada por pergunta. A construção custa 1 resumo por grupo em cada nível, uma vez por "
                       "índice.",
               "limits": "A redução usa UMAP só se o pacote umap-learn estiver instalado. Sem ele usa PCA, e o "
                         "diagnóstico do run informa qual foi usada. A mistura usa covariância diagonal. Resumos no "
                         "contexto não contam como trecho gold nas métricas de recuperação."},
        "en": {"summary": "A tree of recursive summaries over groups of chunks, queried together with the chunks.",
               "how": "Embeddings are reduced and clustered by a Gaussian mixture, with the number of clusters "
                      "chosen by BIC. Clustering is soft: a chunk may feed more than one summary. The LLM "
                      "summarizes each cluster, and the summaries are clustered again, up to max_levels. At query "
                      "time, collapsed mode puts chunks and summaries of every level in one ranking. "
                      "tree_traversal mode descends from the root choosing the most similar children.",
               "when": "Synthesis questions whose answer is spread over one document or several.",
               "cost": "1 call per question. Building costs 1 summary per cluster at each level, once per index.",
               "limits": "The reduction uses UMAP only when the umap-learn package is installed. Without it PCA is "
                         "used, and the run diagnostics say which. The mixture uses diagonal covariance. Summaries "
                         "in the context do not count as gold passages in retrieval metrics."}},
    "agentic": {
        "sources": ("singh2025", "openai_tools"),
        "related": ("technique.multi_hop", "technique.adaptive_rag", "technique.corrective"),
        "calls": "3 … max_steps + 2",
        "pt": {"summary": "O LLM planeja e depois escolhe ferramentas de busca, passo a passo, até ter o bastante "
                          "para responder.",
               "how": "Uma chamada escreve o plano. A cada passo o modelo vê a pergunta, o plano e notas numeradas "
                      "dos trechos já encontrados, e escolhe uma ferramenta: search, pelo sentido; keyword_search, "
                      "por termos exatos; read_more, para ler o texto vizinho de um trecho; ou finish. A escolha "
                      "usa a chamada nativa de ferramentas do provider.",
               "when": "Perguntas abertas em que não se sabe de antemão quantas buscas são necessárias nem de que "
                       "tipo.",
               "cost": "1 chamada de plano, 1 por decisão e 1 de resposta. Com os padrões, de 3 a 6.",
               "limits": "Um único agente, com ferramentas só sobre o índice: não há busca na web, SQL nem "
                         "orquestração de vários agentes. Se o provider recusar ferramentas, a técnica passa para "
                         "um protocolo de texto em JSON e avisa. O laço para em max_steps."},
        "en": {"summary": "The LLM plans and then picks search tools, step by step, until it has enough to answer.",
               "how": "One call writes the plan. At each step the model sees the question, the plan and numbered "
                      "notes of the passages found so far, and picks a tool: search, by meaning; keyword_search, "
                      "by exact terms; read_more, to read the text around a passage; or finish. The choice uses "
                      "the provider's native tool calling.",
               "when": "Open questions where the number and kind of searches needed is not known in advance.",
               "cost": "1 plan call, 1 per decision and 1 answer. With defaults, 3 to 6.",
               "limits": "A single agent, with tools over the index only: no web search, SQL or multi-agent "
                         "orchestration. If the provider rejects tools, the technique switches to a JSON text "
                         "protocol and warns. The loop stops at max_steps."}},
    "long_context": {
        "sources": ("jiang2024long", "li2024long", "liu2023"),
        "related": ("metric.context_chars", "metric.cost", "technique.parent_child", "concept.context"),
        "calls": "1",
        "pt": {"summary": "A recuperação escolhe os documentos, e o modelo lê cada um por inteiro em vez de trechos "
                          "isolados.",
               "how": "Os chunks recuperados só decidem quais documentos importam. O contexto recebe o texto "
                      "completo dos max_documents melhores, até context_chars. Um documento que não cabe é cortado "
                      "em uma janela em volta dos trechos encontrados.",
               "when": "Documentos em que a resposta depende do conjunto, como uma decisão judicial com relatório, "
                       "fundamentação e dispositivo, e modelos com janela de contexto grande.",
               "cost": "1 chamada por pergunta, com muitos tokens de entrada. Com o padrão de 48.000 caracteres, "
                       "cerca de 12.000 tokens por pergunta.",
               "limits": "Ignora o max_context_chars do run e usa o próprio orçamento, então a comparação de custo "
                         "com as demais técnicas é desigual por desenho. Contextos longos diluem a atenção do "
                         "modelo: compare também a qualidade, não só o recall."},
        "en": {"summary": "Retrieval chooses the documents, and the model reads each one whole instead of isolated "
                          "passages.",
               "how": "Retrieved chunks only decide which documents matter. The context receives the full text of "
                      "the best max_documents, up to context_chars. A document that does not fit is cut to a window "
                      "around the matched passages.",
               "when": "Documents whose answer depends on the whole, such as a court ruling with report, reasoning "
                       "and holding, and models with a large context window.",
               "cost": "1 call per question, with many prompt tokens. With the default of 48,000 characters, about "
                       "12,000 tokens per question.",
               "limits": "It ignores the run's max_context_chars and uses its own budget, so cost comparison with "
                         "other techniques is unequal by design. Long contexts dilute the model's attention: "
                         "compare quality too, not only recall."}},
    "hierarchical": {
        "sources": ("liu2021",),
        "related": ("technique.raptor", "technique.naive", "concept.document"), "calls": "1",
        "pt": {"summary": "Escolhe primeiro os documentos e depois busca os chunks só dentro deles.",
               "how": "Cada documento tem um vetor próprio: o embedding de um resumo escrito pelo LLM, ou a média "
                      "dos vetores dos seus chunks quando document_vector é mean. A pergunta seleciona os "
                      "top_documents mais próximos, e a busca do run acontece restrita a eles.",
               "when": "Corpus com muitos documentos de vocabulário parecido, em que chunks do documento errado "
                       "tomam o lugar dos do documento certo. É o caso de coleções de decisões sobre o mesmo tema.",
               "cost": "1 chamada por pergunta. No modo summary, a construção custa 1 resumo por documento, uma vez "
                       "por índice. No modo mean não há custo de construção.",
               "limits": "Se o primeiro estágio errar o documento, o segundo não tem como recuperar. O resumo usa só "
                         "os primeiros summary_input_chars de cada documento. Em corpus com poucos documentos "
                         "equivale ao naive."},
        "en": {"summary": "Chooses the documents first and then searches for chunks only inside them.",
               "how": "Each document has its own vector: the embedding of an LLM-written summary, or the mean of "
                      "its chunk vectors when document_vector is mean. The question selects the closest "
                      "top_documents, and the run's search happens restricted to them.",
               "when": "Corpora with many documents of similar vocabulary, where chunks from the wrong document "
                       "displace those from the right one. Collections of rulings on the same subject are the case.",
               "cost": "1 call per question. In summary mode, building costs 1 summary per document, once per "
                       "index. In mean mode there is no build cost.",
               "limits": "If the first stage picks the wrong document, the second cannot recover. The summary uses "
                         "only the first summary_input_chars of each document. On a corpus with few documents it "
                         "equals naive."}},
    "recomp": {
        "sources": ("xu2023",),
        "related": ("technique.context_compression", "metric.context_coverage", "metric.context_chars"),
        "calls": "2",
        "pt": {"summary": "Comprime o que foi recuperado em um texto curto antes de o modelo ler.",
               "how": "No modo abstractive, uma única chamada escreve um resumo dos trechos voltado para a pergunta, "
                      "e só o resumo vai para o contexto. No modo extractive, ficam as n_sentences sentenças mais "
                      "parecidas com a pergunta, por embedding, sem chamada ao LLM. Se o resumo concluir que nada "
                      "ajuda, o modelo responde sem contexto.",
               "when": "Para reduzir tokens de entrada com k alto, ou para medir quanto da evidência sobrevive a "
                       "uma compressão forte.",
               "cost": "2 chamadas por pergunta no modo abstractive, 1 no modo extractive.",
               "limits": "Protótipo. O artigo treina os dois compressores. Aqui o resumo é um prompt ao LLM do run "
                         "e as sentenças são ranqueadas pelo embedding do run. A resposta cita o resumo, não os "
                         "trechos originais. Os trechos recuperados continuam no resultado, então o recall descreve "
                         "a recuperação e o context coverage descreve o que restou."},
        "en": {"summary": "Compresses what was retrieved into a short text before the model reads it.",
               "how": "In abstractive mode a single call writes a query-focused summary of the passages, and only "
                      "the summary goes into the context. In extractive mode the n_sentences sentences most similar "
                      "to the question are kept, by embedding, with no LLM call. If the summary concludes nothing "
                      "helps, the model answers without context.",
               "when": "To cut prompt tokens with a high k, or to measure how much evidence survives strong "
                       "compression.",
               "cost": "2 calls per question in abstractive mode, 1 in extractive mode.",
               "limits": "Prototype. The paper trains both compressors. Here the summary is a prompt to the run's "
                         "LLM and sentences are ranked by the run's embeddings. The answer cites the summary, not "
                         "the original passages. Retrieved passages stay in the result, so recall describes "
                         "retrieval and context coverage describes what was left."}},
    "speculative_rag": {
        "sources": ("wang2024",),
        "related": ("technique.self_rag", "technique.mmr_rag", "metric.llm_calls"), "calls": "2 × n_drafts",
        "pt": {"summary": "Gera vários rascunhos de resposta, cada um a partir de um subconjunto diverso da "
                          "evidência, e uma verificação escolhe o melhor.",
               "how": "Recupera 2k trechos e os agrupa por conteúdo com k-means. Cada rascunho recebe um trecho de "
                      "cada grupo, então nenhum lê tudo e todos veem perspectivas diferentes. Cada rascunho recebe "
                      "uma nota de 0 a 1 pelo apoio no seu subconjunto, e vence o de maior nota.",
               "when": "Quando os trechos recuperados trazem informações diferentes ou conflitantes e um contexto "
                       "único misturaria tudo.",
               "cost": "Com os padrões, 3 respostas e 3 verificações: 6 chamadas por pergunta, cada uma com "
                       "contexto menor.",
               "limits": "Protótipo. O artigo usa um modelo pequeno e treinado para rascunhar em paralelo e um "
                         "modelo maior para verificar. Um run tem um único LLM, que aqui faz os dois papéis, em "
                         "sequência. A resposta vem de um subconjunto, não de todos os trechos."},
        "en": {"summary": "Generates several answer drafts, each from a diverse subset of the evidence, and a "
                          "verification step picks the best.",
               "how": "Retrieves 2k passages and clusters them by content with k-means. Each draft takes one "
                      "passage from every cluster, so none reads everything and all see different perspectives. "
                      "Each draft gets a 0 to 1 score for support in its subset, and the highest score wins.",
               "when": "When retrieved passages carry different or conflicting information and a single context "
                       "would mix everything.",
               "cost": "With defaults, 3 answers and 3 verifications: 6 calls per question, each with a smaller "
                       "context.",
               "limits": "Prototype. The paper uses a small trained model to draft in parallel and a larger one to "
                         "verify. A run has a single LLM, which plays both roles here, sequentially. The answer "
                         "comes from one subset, not from all passages."}},
}
