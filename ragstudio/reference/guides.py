"""Guide entries: short how-to notes that support running experiments and reading their results."""
from __future__ import annotations

from typing import Any

from .entry import entry

ENTRIES: list[dict[str, Any]] = [
    entry("guide.flow", "guide", "running", {"pt": "Do documento ao resultado", "en": "From document to result"},
          related=("concept.runbook", "concept.index", "guide.metrics_available", "guide.first_experiment"),
          pt={"summary": "A ordem das telas segue o fluxo do experimento.",
              "steps": "1. Corpus: importe os documentos e confira o texto extraído e as características.\n"
                       "2. Corpus › Splits: opcional, separe treino, validação e teste.\n"
                       "3. Perguntas: crie ou importe o conjunto, com resposta esperada e trechos gold quando "
                       "possível.\n"
                       "4. Configurações: escolha o provider, os modelos e os padrões.\n"
                       "5. Experimentos › Montar: escolha técnicas e eixos, veja o número de runs e a estimativa de "
                       "custo, e execute.\n"
                       "6. Experimentos › Monitor: acompanhe o progresso e as falhas.\n"
                       "7. Experimentos › Resultados e Comparar: tabela de runs, comparação pareada e respostas por "
                       "pergunta.\n"
                       "8. Análise: métricas por eixo e cruzamento com as características dos documentos.\n"
                       "9. Relatórios: relatório HTML, figuras, tabelas e exportações.",
              "read": "O índice é construído no passo 5, na primeira vez que um run precisa dele. Técnicas com a "
                      "mesma indexação compartilham os vetores."},
          en={"summary": "The order of the screens follows the flow of the experiment.",
              "steps": "1. Corpus: import the documents and check the extracted text and the characteristics.\n"
                       "2. Corpus › Splits: optional, separate train, validation and test.\n"
                       "3. Questions: create or import the set, with expected answers and gold passages when "
                       "possible.\n"
                       "4. Settings: choose the provider, models and defaults.\n"
                       "5. Experiments › Setup: choose techniques and axes, see the number of runs and the cost "
                       "estimate, and run.\n"
                       "6. Experiments › Monitor: follow progress and failures.\n"
                       "7. Experiments › Results and Compare: run table, paired comparison and answers by "
                       "question.\n"
                       "8. Analysis: metrics per axis and crossing with document characteristics.\n"
                       "9. Reports: HTML report, figures, tables and exports.",
              "read": "The index is built at step 5, the first time a run needs it. Techniques with the same "
                      "indexing share the vectors."}),
    entry("guide.metrics_available", "guide", "running",
          {"pt": "Que métricas vou obter?", "en": "Which metrics will I get?"},
          related=("concept.availability", "concept.gold_passage", "concept.expected_answer", "concept.judge"),
          pt={"summary": "Depende do que foi anotado nas perguntas e do que foi ligado no runbook.",
              "steps": "Sempre: latência, tokens, chamadas ao LLM, custo, tamanho do contexto, faithfulness, "
                       "groundedness, citation accuracy, hallucination e refusal.\n"
                       "Com trechos gold: hit, recall, precision, MRR, nDCG e context coverage.\n"
                       "Com resposta esperada: exact match, Token F1 e accuracy.\n"
                       "Com o juiz ligado: judge faithfulness e, se houver resposta esperada, judge accuracy.\n"
                       "Com revisão humana: concordância com o revisor.",
              "read": "Sem resposta esperada e sem trechos gold, as únicas medidas de qualidade são as heurísticas "
                      "lexicais baseadas no contexto, que são as mais fracas. Nessa situação compare custo e "
                      "latência e leia as respostas lado a lado, ou ligue o juiz."},
          en={"summary": "It depends on what was annotated in the questions and enabled in the runbook.",
              "steps": "Always: latency, tokens, LLM calls, cost, context size, faithfulness, groundedness, citation "
                       "accuracy, hallucination and refusal.\n"
                       "With gold passages: hit, recall, precision, MRR, nDCG and context coverage.\n"
                       "With an expected answer: exact match, Token F1 and accuracy.\n"
                       "With the judge enabled: judge faithfulness and, given an expected answer, judge accuracy.\n"
                       "With human review: agreement with the reviewer.",
              "read": "Without expected answers and gold passages, the only quality measures are the lexical "
                      "context-based heuristics, the weakest ones. In that situation compare cost and latency and "
                      "read the answers side by side, or enable the judge."}),
    entry("guide.first_experiment", "guide", "running",
          {"pt": "Montando um primeiro experimento", "en": "Setting up a first experiment"},
          related=("concept.runbook", "technique.naive", "guide.cost", "concept.question_set"),
          pt={"summary": "Uma grade pequena e bem anotada ensina mais que uma grade enorme com uma pergunta.",
              "steps": "1. Escreva de 20 a 50 perguntas, com resposta esperada e pelo menos um trecho gold cada.\n"
                       "2. Comece com naive e duas ou três técnicas, um modo de recuperação, um k e reranker none.\n"
                       "3. Execute com o provider simulado para validar o fluxo sem custo.\n"
                       "4. Execute com o provider real e confira a estimativa antes.\n"
                       "5. Amplie um eixo por vez: modo de recuperação, depois k, depois reranker.",
              "read": "Ampliar um eixo por vez mantém o custo sob controle e deixa claro de onde vem cada diferença. "
                      "Os presets quick, comparative e full do runbook são pontos de partida prontos."},
          en={"summary": "A small, well-annotated grid teaches more than a huge grid with one question.",
              "steps": "1. Write 20 to 50 questions, each with an expected answer and at least one gold passage.\n"
                       "2. Start with naive and two or three techniques, one retrieval mode, one k and reranker "
                       "none.\n"
                       "3. Run with the mock provider to validate the flow at no cost.\n"
                       "4. Run with the real provider, checking the estimate first.\n"
                       "5. Widen one axis at a time: retrieval mode, then k, then reranker.",
              "read": "Widening one axis at a time keeps cost under control and makes clear where each difference "
                      "comes from. The runbook presets quick, comparative and full are ready starting points."}),
    entry("guide.cost", "guide", "running", {"pt": "Estimando e limitando o custo", "en": "Estimating and capping cost"},
          related=("metric.cost", "metric.llm_calls", "component.enrich.contextual", "concept.judge"),
          pt={"summary": "A estimativa mostrada antes de executar é um piso, e o orçamento interrompe o runbook "
                         "entre runs.",
              "steps": "A estimativa conta uma chamada por pergunta. Técnicas com várias chamadas custam mais: veja "
                       "o campo de chamadas de cada técnica.\n"
                       "O reranker llm soma 1 chamada por pergunta. O juiz soma até 2 por resposta.\n"
                       "enrich: contextual soma 1 chamada por chunk, uma vez por índice.\n"
                       "raptor soma 1 resumo por grupo na construção. graph_rag, light_rag e hippo_rag dividem uma "
                       "única extração do grafo, com 1 chamada por chunk. Tudo isso acontece uma vez por índice.\n"
                       "max_budget_usd para o runbook antes do próximo run quando o gasto medido atinge o limite.",
              "read": "Um run em andamento não é interrompido no meio, então o gasto final pode passar um pouco do "
                      "limite. Embeddings ficam em cache e não são cobrados de novo."},
          en={"summary": "The estimate shown before running is a floor, and the budget stops the runbook between "
                         "runs.",
              "steps": "The estimate counts one call per question. Techniques with several calls cost more: see the "
                       "calls field of each technique.\n"
                       "The llm reranker adds 1 call per question. The judge adds up to 2 per answer.\n"
                       "enrich: contextual adds 1 call per chunk, once per index.\n"
                       "raptor adds 1 summary per cluster at build time. graph_rag, light_rag and hippo_rag share a "
                       "single graph extraction, with 1 call per chunk. All of this happens once per index.\n"
                       "max_budget_usd stops the runbook before the next run once measured spending reaches the "
                       "limit.",
              "read": "A run in progress is not interrupted midway, so final spending may slightly exceed the "
                      "limit. Embeddings are cached and not charged again."}),
    entry("guide.failures", "guide", "running", {"pt": "Quando um run falha", "en": "When a run fails"},
          related=("concept.run", "component.reranker.cross_encoder", "component.store.faiss"),
          pt={"summary": "Corrija a causa e execute de novo o mesmo runbook: os concluídos são pulados e só os "
                         "demais são refeitos.",
              "steps": "Pacote ausente: a mensagem traz o pip install necessário. Opções indisponíveis aparecem "
                       "desabilitadas na montagem do experimento.\n"
                       "faiss com cross_encoder: combinação recusada na criação do runbook.\n"
                       "Erro do provider: confira a chave e o modelo em Configurações.\n"
                       "Pergunta que falha: fica registrada e o run continua. Se todas falham, o run fica como "
                       "falhou e o runbook segue para o próximo.\n"
                       "LeakageError: pergunta e trecho gold em splits diferentes.",
              "read": "A causa de cada falha aparece em Experimentos › Monitor e no detalhe do run."},
          en={"summary": "Fix the cause and run the same runbook again: completed runs are skipped and only the "
                         "others are redone.",
              "steps": "Missing package: the message names the pip install needed. Unavailable options appear "
                       "disabled in the experiment setup.\n"
                       "faiss with cross_encoder: rejected when the runbook is created.\n"
                       "Provider error: check the key and the model in Settings.\n"
                       "A failing question: it is recorded and the run continues. If all fail, the run is marked "
                       "failed and the runbook moves on.\n"
                       "LeakageError: question and gold passage in different splits.",
              "read": "The cause of each failure is shown in Experiments › Monitor and in the run detail."}),
    entry("guide.fair_comparison", "guide", "reading", {"pt": "Comparando de forma justa", "en": "Comparing fairly"},
          related=("concept.index_hash", "metric.context_chars", "technique.naive", "statistic.paired"),
          pt={"summary": "Uma diferença só é da técnica quando todo o resto é igual.",
              "steps": "Compare runs com o mesmo index_hash: mesmo chunking, embedding, store e split.\n"
                       "Mantenha iguais o LLM, k, o modo de recuperação, o reranker e o seed.\n"
                       "Inclua sempre o naive como linha de base.\n"
                       "Olhe context chars junto com a qualidade: parent_child, sentence_window e "
                       "context_compression mudam o tamanho do contexto.\n"
                       "Compare precision só entre runs com o mesmo k.\n"
                       "Use a comparação pareada, e não a diferença entre duas médias.",
              "read": "parent_child e contextual_retrieval exigem índices próprios. Para elas a comparação é entre "
                      "pipelines inteiros, não só entre técnicas."},
          en={"summary": "A difference belongs to the technique only when everything else is equal.",
              "steps": "Compare runs with the same index_hash: same chunking, embedding, store and split.\n"
                       "Keep the LLM, k, retrieval mode, reranker and seed equal.\n"
                       "Always include naive as the baseline.\n"
                       "Look at context chars next to quality: parent_child, sentence_window and "
                       "context_compression change the context size.\n"
                       "Compare precision only between runs with the same k.\n"
                       "Use the paired comparison, not the difference between two means.",
              "read": "parent_child and contextual_retrieval need their own indices. For them the comparison is "
                      "between whole pipelines, not techniques alone."}),
    entry("guide.reading_results", "guide", "reading", {"pt": "Lendo os resultados", "en": "Reading the results"},
          related=("metric.recall", "metric.f1", "metric.faithfulness", "concept.quadrant", "statistic.n"),
          pt={"summary": "Leia na ordem do fluxo: primeiro a recuperação, depois a geração, depois o custo.",
              "steps": "1. Recall e Hit@k: a evidência chegou? Se não, nenhuma métrica de geração explica o "
                       "resultado.\n"
                       "2. MRR e nDCG: ela chegou bem posicionada?\n"
                       "3. Context coverage: ela sobreviveu ao corte e à compressão?\n"
                       "4. F1, accuracy ou judge accuracy: a resposta está correta?\n"
                       "5. Judge faithfulness, e a faithfulness lexical com cautela: a resposta se apoia no "
                       "contexto?\n"
                       "6. Chamadas, tokens, custo e latência: quanto custou o ganho sobre o naive?",
              "read": "Confira o n de cada métrica e abra as respostas em Comparar › Por pergunta antes de "
                      "concluir. Respostas idênticas entre técnicas são comuns quando a recuperação traz os mesmos "
                      "chunks."},
          en={"summary": "Read in flow order: retrieval first, then generation, then cost.",
              "steps": "1. Recall and Hit@k: did the evidence arrive? If not, no generation metric explains the "
                       "result.\n"
                       "2. MRR and nDCG: did it arrive well ranked?\n"
                       "3. Context coverage: did it survive truncation and compression?\n"
                       "4. F1, accuracy or judge accuracy: is the answer correct?\n"
                       "5. Judge faithfulness, and lexical faithfulness with caution: is the answer supported by the "
                       "context?\n"
                       "6. Calls, tokens, cost and latency: what did the gain over naive cost?",
              "read": "Check the n of each metric and open the answers in Compare › By question before concluding. "
                      "Identical answers across techniques are common when retrieval brings the same chunks."}),
    entry("guide.significance", "guide", "reading",
          {"pt": "A diferença é real?", "en": "Is the difference real?"},
          sources=("smucker2007",),
          related=("statistic.paired", "statistic.bootstrap", "statistic.permutation", "statistic.holm",
                   "statistic.cohen"),
          pt={"summary": "Use a comparação pareada entre dois runs e leia quatro números, nesta ordem.",
              "steps": "1. n: quantas perguntas entraram.\n"
                       "2. Diferença média b − a e o intervalo de 95%. Se o intervalo inclui zero, não há evidência "
                       "de diferença.\n"
                       "3. p de permutação com correção de Holm.\n"
                       "4. Tamanho de efeito: a diferença é grande o bastante para importar?",
              "read": "Com menos de umas 10 perguntas os testes têm pouco poder e quase nunca acusam diferença. "
                      "Ausência de significância não prova que as técnicas são equivalentes.",
              "limits": "Os testes consideram a variação entre perguntas, não a variação do modelo entre execuções. "
                        "Para esta, use vários seeds."},
          en={"summary": "Use the paired comparison between two runs and read four numbers, in this order.",
              "steps": "1. n: how many questions entered.\n"
                       "2. Mean difference b − a and the 95% interval. If the interval includes zero there is no "
                       "evidence of a difference.\n"
                       "3. Permutation p with the Holm correction.\n"
                       "4. Effect size: is the difference large enough to matter?",
              "read": "With fewer than about 10 questions the tests have little power and almost never flag a "
                      "difference. Lack of significance does not prove the techniques are equivalent.",
              "limits": "The tests account for variation between questions, not the model's variation between "
                        "executions. For that, use several seeds."}),
    entry("guide.docs", "guide", "reading", {"pt": "Documentação do projeto", "en": "Project documentation"},
          facts={"files": ["docs/running-experiments.md", "docs/comparing.md", "docs/techniques.md",
                           "docs/adding-a-technique.md", "docs/data-schema.md"]},
          related=("guide.flow",),
          pt={"summary": "Os guias em docs/ cobrem a linha de comando, o formato dos arquivos e o esquema do banco.",
              "steps": "running-experiments.md: corpus, perguntas, runbook, execução e reprodução.\n"
                       "comparing.md: métricas, comparação pareada, relatórios e exportações.\n"
                       "techniques.md: catálogo de técnicas e o que falta em cada protótipo.\n"
                       "adding-a-technique.md: como incluir uma técnica nova no contrato comum.\n"
                       "data-schema.md: tabelas do SQLite e arquivos de índice.",
              "read": "Tudo o que o aplicativo faz também está disponível pela linha de comando, com ./rs."},
          en={"summary": "The guides under docs/ cover the command line, the file formats and the database schema.",
              "steps": "running-experiments.md: corpus, questions, runbook, execution and reproduction.\n"
                       "comparing.md: metrics, paired comparison, reports and exports.\n"
                       "techniques.md: technique catalog and what each prototype lacks.\n"
                       "adding-a-technique.md: how to add a new technique under the common contract.\n"
                       "data-schema.md: SQLite tables and index files.",
              "read": "Everything the app does is also available from the command line, with ./rs."}),
]
