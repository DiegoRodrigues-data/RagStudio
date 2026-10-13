"""Concept and statistics entries: the vocabulary of the app and of the comparison screens."""
from __future__ import annotations

from typing import Any

from .entry import entry

ENTRIES: list[dict[str, Any]] = [
    # ── pipeline ─────────────────────────────────────────────────────────────────────────────────────────────────
    entry("concept.rag", "concept", "pipeline", "RAG", sources=("lewis2020", "gupta2024"),
          related=("technique.naive", "concept.chunk", "concept.context"),
          pt={"summary": "Retrieval-Augmented Generation: o modelo responde a partir de trechos recuperados de "
                         "documentos, e não só da sua memória.",
              "how": "No RagStudio toda técnica segue o mesmo fluxo: documento, chunking, índice, recuperação, "
                     "contexto, geração e avaliação. As técnicas diferem no que fazem em cada etapa.",
              "read": "Por seguirem o mesmo contrato, tempo, tokens e evidências são medidos do mesmo jeito para "
                      "todas, e os números ficam comparáveis."},
          en={"summary": "Retrieval-Augmented Generation: the model answers from passages retrieved from documents, "
                         "not only from its memory.",
              "how": "In RagStudio every technique follows the same flow: document, chunking, index, retrieval, "
                     "context, generation and evaluation. Techniques differ in what they do at each step.",
              "read": "Because they obey one contract, time, tokens and evidence are measured the same way for all, "
                      "and the numbers are comparable."}),
    entry("concept.document", "concept", "pipeline", {"pt": "Documento e corpus", "en": "Document and corpus"},
          related=("component.loader.docling", "concept.characteristics", "concept.chunk"),
          pt={"summary": "Um corpus é um conjunto nomeado de documentos. Cada documento guarda o texto normalizado "
                         "e o seu hash.",
              "how": "Na importação o texto é normalizado: quebras de linha, BOM e espaços finais. Todos os offsets "
                     "de chunks e de trechos gold se referem a esse texto.",
              "read": "Trocar o conteúdo de um documento muda o hash e portanto o índice. Resultados antigos "
                      "continuam ligados ao índice antigo."},
          en={"summary": "A corpus is a named set of documents. Each document stores the normalized text and its "
                         "hash.",
              "how": "At import the text is normalized: line breaks, BOM and trailing spaces. Every chunk and gold "
                     "offset refers to that text.",
              "read": "Changing a document's content changes the hash and hence the index. Old results stay linked "
                      "to the old index."}),
    entry("concept.chunk", "concept", "pipeline", "Chunk",
          related=("component.chunking.fixed", "concept.k", "concept.gold_passage"),
          pt={"summary": "Um pedaço do documento, a unidade que é indexada, recuperada e enviada ao modelo.",
              "how": "Todo chunk é uma fatia exata do texto: documento[início:fim] é igual ao texto do chunk. Isso "
                     "vale para todas as estratégias de chunking.",
              "read": "Tamanho e sobreposição são decisões do experimento. Chunks pequenos casam melhor com a "
                      "pergunta e levam menos contexto. Chunks grandes fazem o contrário."},
          en={"summary": "A piece of the document, the unit that is indexed, retrieved and sent to the model.",
              "how": "Every chunk is an exact slice of the text: document[start:end] equals the chunk text. This "
                     "holds for every chunking strategy.",
              "read": "Size and overlap are experimental decisions. Small chunks match the question better and "
                      "carry less context. Large chunks do the opposite."}),
    entry("concept.embedding", "concept", "pipeline", "Embedding",
          sources=("reimers2019", "openai_embeddings"), related=("component.retrieval.dense", "concept.index"),
          pt={"summary": "Vetor numérico que representa o sentido de um texto. Textos parecidos têm vetores "
                         "próximos.",
              "how": "Os chunks são convertidos em vetores na construção do índice e a pergunta, na hora da "
                     "consulta. Os vetores ficam em cache por provider, modelo e hash do texto, então o mesmo chunk "
                     "nunca é pago duas vezes.",
              "read": "O modelo de embedding é um eixo do experimento. Trocá-lo cria outro índice."},
          en={"summary": "A numeric vector representing the meaning of a text. Similar texts have close vectors.",
              "how": "Chunks are turned into vectors when the index is built, the question at query time. Vectors "
                     "are cached by provider, model and text hash, so the same chunk is never paid for twice.",
              "read": "The embedding model is an experimental axis. Changing it creates another index."}),
    entry("concept.index", "concept", "pipeline", {"pt": "Índice", "en": "Index"},
          related=("concept.index_hash", "component.store.memory", "concept.embedding"),
          pt={"summary": "Os chunks de um corpus com seus vetores e o índice lexical, prontos para busca.",
              "how": "É construído na primeira vez que um run precisa dele e guardado em Dados/indices. Runs "
                     "seguintes com a mesma indexação o reaproveitam.",
              "read": "Os embeddings não são feitos na importação dos documentos. São feitos quando o primeiro "
                      "experimento pede aquele índice, ou pela aba Índices do Corpus."},
          en={"summary": "The chunks of a corpus with their vectors and the lexical index, ready to search.",
              "how": "Built the first time a run needs it and stored under Dados/indices. Later runs with the same "
                     "indexing reuse it.",
              "read": "Embeddings are not computed when documents are imported. They are computed when the first "
                      "experiment asks for that index, or from the Indices tab of Corpus."}),
    entry("concept.index_hash", "concept", "pipeline", "index_hash",
          related=("concept.index", "guide.fair_comparison"),
          pt={"summary": "Identidade do índice: um hash de tudo o que determina os vetores.",
              "how": "Cobre documentos, com id e hash de cada um, chunking, provider e modelo de embedding, store, "
                     "split e enriquecimento.",
              "read": "Mesmo hash significa mesmos chunks e mesmos vetores. Só então a diferença entre dois runs é "
                      "da técnica. Cada run registra o seu."},
          en={"summary": "The identity of the index: a hash of everything that determines the vectors.",
              "how": "It covers the documents, with each id and hash, chunking, embedding provider and model, store, "
                     "split and enrichment.",
              "read": "Same hash means same chunks and same vectors. Only then is the difference between two runs "
                      "due to the technique. Every run records its own."}),
    entry("concept.k", "concept", "pipeline", {"pt": "k (top-k)", "en": "k (top-k)"},
          related=("metric.precision", "metric.recall", "metric.context_chars"),
          pt={"summary": "Quantos chunks finais a técnica entrega ao contexto.",
              "read": "k maior aumenta o recall e o custo, e reduz a precisão. É um eixo do runbook: use dois ou "
                      "três valores para ver a curva. Algumas técnicas buscam mais candidatos internamente e depois "
                      "reduzem a k."},
          en={"summary": "How many final chunks the technique delivers to the context.",
              "read": "A larger k raises recall and cost and lowers precision. It is a runbook axis: use two or "
                      "three values to see the curve. Some techniques fetch more candidates internally and then cut "
                      "to k."}),
    entry("concept.context", "concept", "pipeline", {"pt": "Contexto", "en": "Context"}, sources=("liu2023",),
          related=("metric.context_chars", "metric.context_coverage", "concept.citation"),
          pt={"summary": "O texto montado com os chunks finais e enviado ao modelo junto com a pergunta.",
              "how": "Os trechos são numerados como [1], [2] e assim por diante, com a origem de cada um, e o total "
                     "é cortado em max_context_chars, 6000 por padrão.",
              "read": "Se k × tamanho do chunk passa do limite, os últimos trechos são cortados. Context coverage "
                      "mostra quando isso tira a evidência."},
          en={"summary": "The text assembled from the final chunks and sent to the model with the question.",
              "how": "Passages are numbered [1], [2] and so on, each with its origin, and the total is truncated to "
                     "max_context_chars, 6000 by default.",
              "read": "If k × chunk size exceeds the limit, the last passages are cut. Context coverage shows when "
                      "that removes the evidence."}),
    entry("concept.citation", "concept", "pipeline", {"pt": "Citação", "en": "Citation"},
          related=("metric.citation_accuracy", "concept.context"),
          pt={"summary": "Marcador [n] na resposta que aponta para o trecho n do contexto.",
              "read": "O executor rejeita resultados cujas citações apontem para chunks fora do contexto. A "
                      "qualidade da citação é medida por citation accuracy."},
          en={"summary": "An [n] marker in the answer pointing to passage n of the context.",
              "read": "The runner rejects results whose citations point to chunks outside the context. Citation "
                      "quality is measured by citation accuracy."}),
    entry("concept.prompt_set", "concept", "pipeline", {"pt": "Conjunto de prompts", "en": "Prompt set"},
          related=("concept.run", "concept.evidence_chain"),
          pt={"summary": "Os modelos de prompt de todas as tarefas, em português e inglês, com versão e hash.",
              "read": "O idioma do runbook escolhe o conjunto. Cada chamada registra o hash do modelo de prompt "
                      "usado, então uma mudança de prompt fica visível na comparação entre runs."},
          en={"summary": "The prompt templates of every task, in Portuguese and English, with version and hash.",
              "read": "The runbook language selects the set. Every call records the hash of the template used, so a "
                      "prompt change is visible when comparing runs."}),
    entry("concept.stage", "concept", "pipeline", {"pt": "Etapas do pipeline", "en": "Pipeline stages"},
          sources=("gao2023survey",), related=("concept.rag", "concept.pruning", "guide.fair_comparison"),
          pt={"summary": "Cada técnica é classificada pela etapa do pipeline em que atua. É assim que o catálogo e a "
                         "montagem do experimento são organizados.",
              "how": "Documento e índice: muda o que é indexado ou constrói uma estrutura sobre o índice, como "
                     "árvore ou grafo. Consulta: transforma a pergunta antes da busca. Recuperação: muda a forma de "
                     "buscar. Pós-recuperação: reordena, comprime ou expande o que foi encontrado. Orquestração: "
                     "decide quando e quantas vezes buscar e responder.",
              "read": "Técnicas da mesma etapa são alternativas entre si e a comparação entre elas é direta. "
                      "Técnicas de etapas diferentes podem ser complementares. Chunking, store, modo de recuperação "
                      "e reranker não são técnicas: são eixos do runbook, cruzados com todas elas.",
              "limits": "A literatura fala em Naive, Advanced e Modular RAG. Isso classifica arquiteturas inteiras, "
                        "não técnicas: o RagStudio é um Modular RAG, e quase todas as técnicas do catálogo são "
                        "otimizações do tipo Advanced."},
          en={"summary": "Each technique is classified by the pipeline stage where it acts. That is how the catalog "
                         "and the experiment setup are organized.",
              "how": "Document and index: changes what is indexed or builds a structure over the index, such as a "
                     "tree or a graph. Query: transforms the question before searching. Retrieval: changes how the "
                     "search is done. Post-retrieval: reorders, compresses or expands what was found. "
                     "Orchestration: decides when and how many times to search and answer.",
              "read": "Techniques of the same stage are alternatives and compare directly. Techniques of different "
                      "stages may be complementary. Chunking, store, retrieval mode and reranker are not "
                      "techniques: they are runbook axes, crossed with all of them.",
              "limits": "The literature speaks of Naive, Advanced and Modular RAG. That classifies whole "
                        "architectures, not techniques: RagStudio is a Modular RAG, and nearly every technique in "
                        "the catalog is an Advanced-type optimization."}),
    entry("concept.pruning", "concept", "experiment", {"pt": "Poda de combinações", "en": "Pruning of combinations"},
          related=("concept.runbook", "concept.stage", "guide.cost", "guide.fair_comparison"),
          pt={"summary": "O runbook deixa de criar os runs que só repetiriam outro run ou que não fariam sentido.",
              "how": "Redundante: a técnica substitui um eixo da grade pelo próprio comportamento. O mmr_rag, por "
                     "exemplo, sempre busca com MMR e não aplica reranker, então variar esses eixos repetiria o "
                     "mesmo run. Só o primeiro valor do eixo é mantido. Incompatível: a técnica exige um índice que "
                     "a combinação não constrói, como parent_child sem o chunking parent_child. Ela se comportaria "
                     "como o naive.",
              "read": "Nos resultados, um eixo que a técnica ignora aparece como n/a. A prévia do experimento "
                      "informa quantas combinações foram podadas e de quais técnicas. Uma técnica sem nenhum run "
                      "possível é listada à parte.",
              "limits": "Para manter a grade inteira, use prune: false no runbook pela linha de comando. A poda "
                        "vale para runbooks novos: os já criados não mudam."},
          en={"summary": "The runbook stops creating runs that would only repeat another run or would make no "
                         "sense.",
              "how": "Redundant: the technique replaces a grid axis with its own behaviour. mmr_rag, for example, "
                     "always searches with MMR and applies no reranker, so varying those axes would repeat the same "
                     "run. Only the first value of the axis is kept. Incompatible: the technique needs an index the "
                     "combination does not build, such as parent_child without the parent_child chunking. It would "
                     "behave like naive.",
              "read": "In the results, an axis the technique ignores shows as n/a. The experiment preview reports "
                      "how many combinations were pruned and from which techniques. A technique with no possible "
                      "run is listed separately.",
              "limits": "To keep the whole grid, use prune: false in the runbook from the command line. Pruning "
                        "applies to new runbooks: existing ones do not change."}),
    # ── annotation ───────────────────────────────────────────────────────────────────────────────────────────────
    entry("concept.question_set", "concept", "annotation", {"pt": "Conjunto de perguntas", "en": "Question set"},
          related=("concept.expected_answer", "concept.gold_passage", "guide.metrics_available"),
          pt={"summary": "As perguntas feitas a todas as técnicas de um experimento.",
              "read": "O número de perguntas define o poder das comparações. Com uma pergunta só há um exemplo, não "
                      "uma medida. Editar uma pergunta já usada em um run concluído cria nova versão e arquiva a "
                      "antiga."},
          en={"summary": "The questions asked to every technique in an experiment.",
              "read": "The number of questions sets the power of comparisons. With one question there is an "
                      "example, not a measurement. Editing a question already used by a completed run creates a new "
                      "version and archives the old one."}),
    entry("concept.expected_answer", "concept", "annotation", {"pt": "Resposta esperada", "en": "Expected answer"},
          related=("metric.f1", "metric.exact_match", "metric.judge_accuracy"),
          pt={"summary": "A resposta correta anotada para a pergunta. Habilita exact match, Token F1, accuracy e "
                         "judge accuracy.",
              "read": "Escreva curta e no formato que espera do modelo. Respostas esperadas longas baixam o exact "
                      "match, e as muito curtas baixam o F1 de respostas completas."},
          en={"summary": "The correct answer annotated for the question. Enables exact match, Token F1, accuracy "
                         "and judge accuracy.",
              "read": "Write it short and in the format you expect from the model. Long expected answers lower "
                      "exact match, very short ones lower the F1 of complete answers."}),
    entry("concept.gold_passage", "concept", "annotation", {"pt": "Trecho gold", "en": "Gold passage"},
          related=("metric.recall", "metric.mrr", "concept.leakage"),
          pt={"summary": "O trecho do documento que contém a evidência da resposta. Habilita todas as métricas de "
                         "recuperação.",
              "how": "É um texto literal do documento. Na importação com corpus ele é localizado e ancorado por "
                     "offsets. Se não existir literalmente, a importação falha.",
              "read": "Anote todos os trechos que sustentam a resposta. Trechos não anotados contam como "
                      "irrelevantes e derrubam a precisão."},
          en={"summary": "The passage of the document holding the evidence for the answer. Enables every retrieval "
                         "metric.",
              "how": "It is literal text from the document. On import with a corpus it is located and anchored by "
                     "offsets. If it does not exist literally, the import fails.",
              "read": "Annotate every passage that supports the answer. Unannotated passages count as irrelevant "
                      "and bring precision down."}),
    entry("concept.answer_type", "concept", "annotation", {"pt": "Tipo de resposta", "en": "Answer type"},
          related=("metric.accuracy", "metric.exact_match"),
          pt={"summary": "Como a resposta deve ser comparada com a esperada: extraction, boolean ou classification, "
                         "entre outros.",
              "read": "boolean compara só o sim ou não. classification procura o rótulo esperado na resposta. Os "
                      "demais usam sobreposição de palavras."},
          en={"summary": "How the answer is compared with the expected one: extraction, boolean or classification, "
                         "among others.",
              "read": "boolean compares only yes or no. classification looks for the expected label in the answer. "
                      "The others use word overlap."}),
    # ── experiment ───────────────────────────────────────────────────────────────────────────────────────────────
    entry("concept.runbook", "concept", "experiment", "Runbook",
          related=("concept.run", "concept.pruning", "guide.flow", "guide.cost"),
          pt={"summary": "A definição de um experimento: uma grade de técnicas, indexação, modelos, parâmetros e "
                         "seeds sobre um corpus e um conjunto de perguntas.",
              "how": "Há um run para cada combinação dos eixos: técnicas × chunking × embedding × LLM × k × seed × "
                     "modo de recuperação × reranker × enriquecimento.",
              "read": "A grade cresce por multiplicação. Sem poda, 28 técnicas × 5 modos × 4 rerankers × 2 valores "
                      "de k seriam 1120 runs por seed. Comece pequeno."},
          en={"summary": "The definition of an experiment: a grid of techniques, indexing, models, parameters and "
                         "seeds over a corpus and a question set.",
              "how": "There is one run per combination of the axes: techniques × chunking × embedding × LLM × k × "
                     "seed × retrieval mode × reranker × enrichment.",
              "read": "The grid grows by multiplication. Without pruning, 28 techniques × 5 modes × 4 rerankers × "
                      "2 values of k would be 1120 runs per seed. Start small."}),
    entry("concept.run", "concept", "experiment", "Run",
          related=("concept.runbook", "concept.immutability", "concept.evidence_chain"),
          pt={"summary": "Uma configuração da grade executada sobre todas as perguntas.",
              "how": "Guarda a configuração e seu hash, o index_hash, cada resposta, os chunks recuperados, as "
                     "chamadas feitas, as métricas e o ambiente.",
              "read": "Estados: pendente, executando, concluído, falhou, cancelado e orçamento esgotado. Rodar de "
                      "novo o mesmo runbook pula os concluídos e refaz os demais do zero."},
          en={"summary": "One grid configuration executed over every question.",
              "how": "Stores the configuration and its hash, the index_hash, every answer, the retrieved chunks, "
                     "the calls made, the metrics and the environment.",
              "read": "States: pending, running, completed, failed, cancelled and budget exceeded. Running the same "
                      "runbook again skips completed runs and restarts the others from scratch."}),
    entry("concept.seed", "concept", "experiment", "Seed",
          related=("concept.replica", "statistic.n"),
          pt={"summary": "Um inteiro que fixa o aleatório do Python e do numpy e é enviado ao provider.",
              "read": "Vários seeds medem a variação do próprio modelo. Com provider real, respostas idênticas "
                      "dependem de o provedor honrar seed e temperatura 0, o que nem sempre acontece."},
          en={"summary": "An integer that fixes Python's and numpy's randomness and is sent to the provider.",
              "read": "Several seeds measure the model's own variation. With a real provider, identical answers "
                      "depend on the provider honouring seed and temperature 0, which is not guaranteed."}),
    entry("concept.replica", "concept", "experiment", {"pt": "Réplica", "en": "Replica"},
          related=("concept.immutability", "concept.seed"),
          pt={"summary": "Uma nova execução de um run concluído, ligada ao original.",
              "how": "Criada por ./rs experiments reproduce --run-id. A réplica informa quantas respostas saíram "
                     "idênticas às do original.",
              "read": "É a forma de reexecutar sem alterar o que já foi medido."},
          en={"summary": "A new execution of a completed run, linked to the original.",
              "how": "Created by ./rs experiments reproduce --run-id. The replica reports how many answers came out "
                     "identical to the original's.",
              "read": "It is how to re-execute without altering what was already measured."}),
    entry("concept.immutability", "concept", "experiment", {"pt": "Imutabilidade", "en": "Immutability"},
          related=("concept.replica", "concept.evidence_chain", "concept.eval_version"),
          pt={"summary": "Respostas, chunks recuperados e eventos de um run concluído não podem ser alterados nem "
                         "apagados.",
              "how": "Gatilhos no banco SQLite rejeitam UPDATE e DELETE nessas tabelas.",
              "read": "O que você compara hoje é o que foi medido. Novas avaliações são acrescentadas como uma nova "
                      "versão, sem sobrescrever."},
          en={"summary": "Answers, retrieved chunks and events of a completed run cannot be changed or deleted.",
              "how": "Triggers in the SQLite database reject UPDATE and DELETE on those tables.",
              "read": "What you compare today is what was measured. New evaluations are appended as a new version, "
                      "never overwritten."}),
    entry("concept.evidence_chain", "concept", "experiment", {"pt": "Cadeia de evidências", "en": "Evidence chain"},
          related=("concept.immutability", "concept.run"),
          pt={"summary": "O registro encadeado de tudo o que aconteceu em um run: requisições, respostas, "
                         "recuperações e avaliações.",
              "how": "Cada evento guarda o hash do seu conteúdo e o hash do evento anterior. Verificar a cadeia "
                     "recalcula tudo e acusa qualquer alteração.",
              "read": "Use ./rs experiments verify --id antes de publicar resultados. O relatório HTML traz o "
                      "resultado da verificação."},
          en={"summary": "The chained record of everything that happened in a run: requests, responses, retrievals "
                         "and evaluations.",
              "how": "Each event stores the hash of its content and the hash of the previous event. Verifying the "
                     "chain recomputes everything and reports any change.",
              "read": "Use ./rs experiments verify --id before publishing results. The HTML report includes the "
                      "verification outcome."}),
    entry("concept.split", "concept", "experiment", "Split",
          related=("concept.leakage", "concept.index_hash"),
          pt={"summary": "Divisão dos documentos do corpus em treino, validação e teste.",
              "how": "Sorteio determinístico por seed, com proporções escolhidas, ou atribuição manual. Um runbook "
                     "com split indexa só os documentos daquele split e faz só as perguntas dele.",
              "read": "Ajuste parâmetros no split de validação e relate os números do split de teste. O RAG não "
                      "treina nada, mas escolher k, chunking e limiares olhando o teste é ajustar ao teste."},
          en={"summary": "A division of the corpus documents into train, validation and test.",
              "how": "A deterministic draw by seed with chosen ratios, or manual assignment. A runbook with a split "
                     "indexes only that split's documents and asks only its questions.",
              "read": "Tune parameters on the validation split and report numbers from the test split. RAG trains "
                      "nothing, but choosing k, chunking and thresholds while looking at test is fitting to test."}),
    entry("concept.leakage", "concept", "experiment", {"pt": "Vazamento", "en": "Leakage"}, sources=("kapoor2022",),
          related=("concept.split", "concept.gold_passage"),
          pt={"summary": "Quando informação do conjunto de teste influencia o que deveria ser avaliado sem ela.",
              "how": "O runbook verifica antes de criar os runs: uma pergunta marcada com um split cujo trecho gold "
                     "está em documento de outro split causa LeakageError. Perguntas marcadas também não podem ser "
                     "usadas sem declarar o split.",
              "read": "Um erro de vazamento indica anotação inconsistente. Corrija o split da pergunta ou o do "
                      "documento."},
          en={"summary": "When information from the test set influences what should be evaluated without it.",
              "how": "The runbook checks before creating runs: a question tagged with a split whose gold passage "
                     "lies in a document of another split raises LeakageError. Tagged questions also cannot be used "
                     "without declaring the split.",
              "read": "A leakage error means inconsistent annotation. Fix the split of the question or of the "
                      "document."}),
    entry("concept.provider", "concept", "experiment", {"pt": "Provider e provider simulado",
                                                       "en": "Provider and mock provider"},
          related=("metric.cost", "concept.judge"),
          pt={"summary": "O serviço que atende as chamadas de LLM e de embedding: uma API compatível com a da OpenAI "
                         "ou o provider simulado.",
              "how": "O provider simulado responde por regras, sem rede e sem custo, com embeddings de 96 dimensões "
                     "feitos de um saco de palavras.",
              "read": "Resultados do provider simulado validam só o encanamento e sempre aparecem com um selo. "
                      "Nunca tire conclusões de qualidade deles."},
          en={"summary": "The service answering LLM and embedding calls: an OpenAI-compatible API or the mock "
                         "provider.",
              "how": "The mock provider answers by rules, with no network and no cost, with 96-dimension "
                     "bag-of-words embeddings.",
              "read": "Mock results validate plumbing only and always carry a badge. Never draw quality conclusions "
                      "from them."}),
    entry("concept.environment", "concept", "experiment", {"pt": "Snapshot de ambiente", "en": "Environment snapshot"},
          related=("concept.run",),
          pt={"summary": "Versões do sistema, do Python, dos pacotes e do próprio RagStudio, gravadas com cada run.",
              "read": "É o que a seção de setup experimental de um artigo precisa. Aparece no relatório HTML."},
          en={"summary": "Versions of the system, Python, packages and RagStudio itself, stored with every run.",
              "read": "It is what the experimental-setup section of a paper needs. It appears in the HTML report."}),
    # ── evaluation and analysis ──────────────────────────────────────────────────────────────────────────────────
    entry("concept.availability", "concept", "analysis", {"pt": "Métrica vazia não é zero",
                                                         "en": "An empty metric is not zero"},
          related=("guide.metrics_available", "statistic.n"),
          pt={"summary": "Uma métrica que não pode ser medida fica vazia e é mostrada como um traço.",
              "how": "Sem trechos gold não há métricas de recuperação. Sem resposta esperada não há exact match, F1 "
                     "nem accuracy. Sem o juiz ligado não há métricas do juiz. Modelo sem preço deixa o custo vazio.",
              "read": "Um traço diz que falta anotação ou configuração, não que a técnica foi mal. A disponibilidade "
                      "é informada antes de executar e junto dos resultados."},
          en={"summary": "A metric that cannot be measured stays empty and is shown as a dash.",
              "how": "Without gold passages there are no retrieval metrics. Without an expected answer there is no "
                     "exact match, F1 or accuracy. Without the judge there are no judge metrics. A model without a "
                     "price leaves cost empty.",
              "read": "A dash says annotation or configuration is missing, not that the technique did badly. "
                      "Availability is reported before running and with the results."}),
    entry("concept.eval_version", "concept", "analysis", {"pt": "Versão de avaliação", "en": "Evaluation version"},
          related=("concept.immutability", "concept.judge"),
          pt={"summary": "As métricas são acrescentadas em versões, sem apagar as anteriores.",
              "how": "./rs evaluate rerun --run-id recalcula as métricas de um run sem reexecutá-lo, por exemplo "
                     "para ligar o juiz depois.",
              "read": "Permite avaliar de novo respostas antigas quando uma métrica muda, mantendo o histórico."},
          en={"summary": "Metrics are appended in versions, without deleting earlier ones.",
              "how": "./rs evaluate rerun --run-id recomputes a run's metrics without re-executing it, for example "
                     "to enable the judge later.",
              "read": "It allows old answers to be re-evaluated when a metric changes, keeping the history."}),
    entry("concept.judge", "concept", "analysis", {"pt": "Juiz LLM", "en": "LLM judge"},
          sources=("zheng2023judge", "es2023"),
          related=("metric.judge_faithfulness", "metric.judge_accuracy", "metric.human_agreement"),
          pt={"summary": "Um modelo de linguagem que dá nota às respostas. Fica desligado por padrão.",
              "how": "Ligado por evaluation.judge no runbook. Faz até 2 chamadas por resposta, uma para fidelidade "
                     "e outra para correção quando há resposta esperada.",
              "read": "Use um modelo juiz diferente e de preferência mais forte que o avaliado, e valide uma amostra "
                      "com revisão humana.",
              "limits": "Em uma grade grande o juiz pode custar mais que os próprios runs."},
          en={"summary": "A language model that scores the answers. Off by default.",
              "how": "Enabled by evaluation.judge in the runbook. Makes up to 2 calls per answer, one for "
                     "faithfulness and one for correctness when there is an expected answer.",
              "read": "Use a judge model different from, and preferably stronger than, the evaluated one, and "
                      "validate a sample with human review.",
              "limits": "On a large grid the judge can cost more than the runs themselves."}),
    entry("concept.quadrant", "concept", "analysis", {"pt": "Quadrante", "en": "Quadrant"},
          related=("metric.accuracy", "metric.faithfulness"),
          pt={"summary": "Classificação do run pelo cruzamento de accuracy e faithfulness, com limiar de 0,7.",
              "how": "Correct and grounded, Correct but ungrounded, Grounded but incorrect ou Incorrect and "
                     "ungrounded. Fica vazio quando falta uma das duas métricas.",
              "read": "Correto e sem apoio sugere resposta de memória. Com apoio e incorreto sugere que a evidência "
                      "recuperada era a errada.",
              "limits": "Usa a faithfulness lexical, então herda o problema com paráfrase."},
          en={"summary": "Classification of the run by crossing accuracy and faithfulness, with a 0.7 threshold.",
              "how": "Correct and grounded, Correct but ungrounded, Grounded but incorrect or Incorrect and "
                     "ungrounded. Empty when either metric is missing.",
              "read": "Correct but ungrounded suggests an answer from memory. Grounded but incorrect suggests the "
                      "retrieved evidence was the wrong one.",
              "limits": "It uses lexical faithfulness, so it inherits the paraphrase problem."}),
    entry("concept.characteristics", "concept", "analysis", {"pt": "Características dos documentos",
                                                            "en": "Document characteristics"},
          related=("statistic.spearman", "statistic.terciles", "concept.document"),
          pt={"summary": "Medidas de cada documento calculadas na importação, usadas como variáveis independentes "
                         "da análise.",
              "how": "Caracteres, palavras, parágrafos, títulos, tamanho médio de parágrafo, razão de linhas de "
                     "tabela e de lista, densidade de dígitos, riqueza de vocabulário, idioma, formato e páginas.",
              "read": "Para cada resposta, o documento-alvo é o do trecho gold ou, sem gold, o primeiro recuperado. "
                      "A tela Análise cruza o perfil desse documento com as métricas."},
          en={"summary": "Measures of each document computed at import, used as the independent variables of the "
                         "analysis.",
              "how": "Characters, words, paragraphs, headings, mean paragraph size, table-line and list-line "
                     "ratios, digit density, vocabulary richness, language, format and pages.",
              "read": "For each answer, the target document is that of the gold passage or, without gold, the top "
                      "retrieved one. The Analysis screen crosses that document's profile with the metrics."}),
    # ── statistics ───────────────────────────────────────────────────────────────────────────────────────────────
    entry("statistic.n", "statistic", "basics", {"pt": "n da métrica", "en": "Metric n"},
          related=("concept.availability", "statistic.paired"),
          pt={"summary": "Em quantas perguntas a métrica foi de fato medida.",
              "read": "Toda média vem com o seu n e o desvio padrão. Uma média sobre 3 perguntas e outra sobre 60 "
                      "não têm o mesmo peso. Com n igual a 1 não há variação a estimar."},
          en={"summary": "On how many questions the metric was actually measured.",
              "read": "Every mean comes with its n and standard deviation. A mean over 3 questions and one over 60 "
                      "do not weigh the same. With n equal to 1 there is no variation to estimate."}),
    entry("statistic.paired", "statistic", "paired", {"pt": "Comparação pareada", "en": "Paired comparison"},
          sources=("smucker2007",), related=("statistic.bootstrap", "statistic.permutation", "statistic.holm"),
          pt={"summary": "Comparar dois runs pergunta a pergunta, usando a diferença b − a em cada uma.",
              "how": "Só entram as perguntas em que a métrica existe nos dois runs. Para cada métrica saem a "
                     "diferença média, o intervalo de confiança e três testes.",
              "read": "Parear remove a variação entre perguntas fáceis e difíceis, que costuma ser maior que a "
                      "diferença entre técnicas. Leia primeiro a diferença média e o intervalo, depois os p-valores."},
          en={"summary": "Comparing two runs question by question, using the difference b − a on each.",
              "how": "Only questions where the metric exists in both runs enter. For each metric you get the mean "
                     "difference, the confidence interval and three tests.",
              "read": "Pairing removes the variation between easy and hard questions, usually larger than the "
                      "difference between techniques. Read the mean difference and the interval first, then the "
                      "p-values."}),
    entry("statistic.bootstrap", "statistic", "paired", {"pt": "Intervalo de confiança por bootstrap",
                                                        "en": "Bootstrap confidence interval"},
          sources=("efron1993",), related=("statistic.paired",),
          pt={"summary": "Faixa de valores plausíveis para a diferença média, com 95% de confiança.",
              "how": "As diferenças por pergunta são reamostradas com reposição 5000 vezes. O intervalo vai do "
                     "percentil 2,5 ao 97,5 das médias.",
              "read": "Se o intervalo inclui zero, os dados não distinguem os dois runs. A largura mostra a "
                      "incerteza: com poucas perguntas ele é largo.",
              "limits": "Com menos de umas 10 perguntas o bootstrap subestima a incerteza."},
          en={"summary": "A range of plausible values for the mean difference, at 95% confidence.",
              "how": "Per-question differences are resampled with replacement 5000 times. The interval runs from "
                     "the 2.5th to the 97.5th percentile of the means.",
              "read": "If the interval includes zero, the data do not tell the two runs apart. Its width shows the "
                      "uncertainty: with few questions it is wide.",
              "limits": "With fewer than about 10 questions the bootstrap understates the uncertainty."}),
    entry("statistic.ttest", "statistic", "paired", {"pt": "Teste t pareado", "en": "Paired t-test"},
          sources=("smucker2007",), related=("statistic.wilcoxon", "statistic.permutation"),
          pt={"summary": "Testa se a diferença média é zero, supondo diferenças aproximadamente normais.",
              "how": "t = média ÷ (desvio padrão ÷ √n), com n − 1 graus de liberdade.",
              "read": "p pequeno indica que uma diferença desse tamanho seria rara se os runs fossem equivalentes.",
              "limits": "Métricas binárias ou muito assimétricas violam a suposição com n pequeno. Prefira o teste "
                        "de permutação nesses casos."},
          en={"summary": "Tests whether the mean difference is zero, assuming roughly normal differences.",
              "how": "t = mean ÷ (standard deviation ÷ √n), with n − 1 degrees of freedom.",
              "read": "A small p means a difference this large would be rare if the runs were equivalent.",
              "limits": "Binary or very skewed metrics break the assumption at small n. Prefer the permutation test "
                        "then."}),
    entry("statistic.wilcoxon", "statistic", "paired", {"pt": "Wilcoxon pareado", "en": "Wilcoxon signed-rank"},
          sources=("wilcoxon1945", "smucker2007"), related=("statistic.ttest", "statistic.permutation"),
          pt={"summary": "Teste não paramétrico sobre os postos das diferenças.",
              "how": "Diferenças iguais a zero são descartadas, as demais são ordenadas pelo valor absoluto e o "
                     "p-valor vem da aproximação normal.",
              "read": "Menos sensível a valores extremos que o teste t.",
              "limits": "Com menos de 10 diferenças não nulas a aproximação não é confiável, e o resultado vem "
                        "sinalizado."},
          en={"summary": "A non-parametric test on the ranks of the differences.",
              "how": "Zero differences are dropped, the rest ranked by absolute value, and the p-value comes from "
                     "the normal approximation.",
              "read": "Less sensitive to extreme values than the t-test.",
              "limits": "With fewer than 10 non-zero differences the approximation is unreliable, and the result is "
                        "flagged."}),
    entry("statistic.permutation", "statistic", "paired", {"pt": "Teste de permutação", "en": "Permutation test"},
          sources=("smucker2007",), related=("statistic.holm", "statistic.paired"),
          pt={"summary": "Troca o sinal das diferenças ao acaso e conta quantas vezes a média fica tão extrema "
                         "quanto a observada.",
              "how": "Exato até 12 pares, enumerando todas as trocas. Acima disso, 10.000 sorteios.",
              "read": "Não supõe distribuição e é o p-valor principal da tela de comparação. É ele que recebe a "
                      "correção de Holm.",
              "limits": "Com n pares, o menor p possível é 2 ÷ 2ⁿ. Com 4 perguntas, nenhum resultado fica abaixo de "
                        "0,125."},
          en={"summary": "Flips the sign of the differences at random and counts how often the mean is as extreme "
                         "as the observed one.",
              "how": "Exact up to 12 pairs, enumerating every flip. Above that, 10,000 draws.",
              "read": "It assumes no distribution and is the main p-value of the comparison screen. It is the one "
                      "that receives the Holm correction.",
              "limits": "With n pairs the smallest possible p is 2 ÷ 2ⁿ. With 4 questions no result goes below "
                        "0.125."}),
    entry("statistic.holm", "statistic", "paired", {"pt": "Correção de Holm", "en": "Holm correction"},
          sources=("holm1979",), related=("statistic.permutation",),
          pt={"summary": "Ajuste dos p-valores quando várias métricas são testadas de uma vez.",
              "how": "Os p-valores são ordenados. O menor é multiplicado pelo número de testes, o seguinte por um a "
                     "menos, e assim por diante, sem deixar um valor ajustado ficar menor que o anterior.",
              "read": "Testando 10 métricas, alguma passa de 0,05 por acaso. Use o p ajustado para afirmar que há "
                      "diferença."},
          en={"summary": "An adjustment of p-values when several metrics are tested at once.",
              "how": "P-values are sorted. The smallest is multiplied by the number of tests, the next by one "
                     "fewer, and so on, never letting an adjusted value fall below the previous one.",
              "read": "Testing 10 metrics, some will cross 0.05 by chance. Use the adjusted p to claim a "
                      "difference."}),
    entry("statistic.cohen", "statistic", "paired", {"pt": "Tamanho de efeito (Cohen dz)",
                                                    "en": "Effect size (Cohen's dz)"},
          sources=("cohen1988",), related=("statistic.paired",),
          pt={"summary": "A diferença média dividida pelo desvio padrão das diferenças.",
              "read": "Diz o tamanho da diferença em unidades de variação, independente do n. Referências usuais: "
                      "0,2 pequeno, 0,5 médio, 0,8 grande. Um p pequeno com efeito pequeno é uma diferença real e "
                      "pouco relevante.",
              "limits": "Fica vazio quando todas as diferenças são iguais."},
          en={"summary": "The mean difference divided by the standard deviation of the differences.",
              "read": "It gives the size of the difference in units of variation, independent of n. Usual "
                      "references: 0.2 small, 0.5 medium, 0.8 large. A small p with a small effect is a real but "
                      "minor difference.",
              "limits": "Empty when all differences are equal."}),
    entry("statistic.spearman", "statistic", "characteristics", {"pt": "Correlação de Spearman",
                                                                "en": "Spearman correlation"},
          sources=("spearman1904",), related=("concept.characteristics", "statistic.terciles"),
          pt={"summary": "Correlação entre os postos de uma característica do documento e de uma métrica, de −1 a 1.",
              "read": "Positiva: a métrica cresce com a característica. Por técnica, mostra se ela piora em "
                      "documentos longos, com muitas tabelas ou com muitos números.",
              "limits": "Com poucos documentos é só descritiva. Correlação não é causa: documentos longos podem "
                        "também ser de outro tipo."},
          en={"summary": "Correlation between the ranks of a document characteristic and of a metric, from −1 to 1.",
              "read": "Positive: the metric grows with the characteristic. Per technique, it shows whether it "
                      "degrades on long documents, with many tables or many numbers.",
              "limits": "With few documents it is descriptive only. Correlation is not cause: long documents may "
                        "also be of another kind."}),
    entry("statistic.terciles", "statistic", "characteristics", {"pt": "Tercis", "en": "Terciles"},
          related=("statistic.spearman", "concept.characteristics"),
          pt={"summary": "Os documentos-alvo são divididos em três faixas de tamanho, e as métricas são médias por "
                         "faixa e por técnica.",
              "read": "Mostra de forma direta se uma técnica vai melhor em documentos pequenos, médios ou grandes. "
                      "Confira o n de cada faixa."},
          en={"summary": "Target documents are split into three size bands, and metrics are averaged per band and "
                         "per technique.",
              "read": "It shows directly whether a technique does better on small, medium or large documents. Check "
                      "the n of each band."}),
]
