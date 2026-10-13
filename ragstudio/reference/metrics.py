"""Metric entries: what each number is in THIS code base (see `evaluation/`), how to read it and where it fails.

`facts.keys` are the column names the entry documents; `tests/test_reference.py` checks that every aggregated metric
is covered. `range`: unit | binary | seconds | count | usd | chars. `needs`: none | gold | expected | judge | judge+expected | human. `better`: higher | lower | context.
"""
from __future__ import annotations

from typing import Any

from .entry import entry

_GOLD = ("concept.gold_passage",)

ENTRIES: list[dict[str, Any]] = [
    # ── retrieval ────────────────────────────────────────────────────────────────────────────────────────────────
    entry("metric.recall", "metric", "retrieval", "Recall@k",
          facts={"keys": ["recall"], "needs": "gold", "better": "higher", "range": "unit"},
          sources=("karpukhin2020",), related=("metric.precision", "metric.hit", *_GOLD, "concept.k"),
          pt={"summary": "Fração dos trechos gold da pergunta que foram encontrados entre os chunks finais.",
              "how": "recall = trechos gold cobertos por algum chunk final ÷ total de trechos gold. Um chunk cobre um "
                     "trecho gold do mesmo documento quando sobrepõe pelo menos metade dele (por offsets) ou quando "
                     "contém o texto normalizado do trecho.",
              "read": "É a métrica central da recuperação: se a evidência não chegou ao contexto, a geração não tem "
                      "como acertar com base no documento. Recall baixo com F1 alto sugere que o modelo respondeu "
                      "de memória.",
              "limits": "Depende da qualidade da anotação. Com um único trecho gold por pergunta só vale 0 ou 1, "
                        "igual ao Hit@k."},
          en={"summary": "Share of the question's gold passages found among the final chunks.",
              "how": "recall = gold passages covered by some final chunk ÷ gold passages. A chunk covers a gold "
                     "passage of the same document when it overlaps at least half of it (by offsets) or contains "
                     "its normalized text.",
              "read": "The central retrieval metric: if the evidence never reached the context, generation cannot be "
                      "right from the document. Low recall with high F1 suggests the model answered from memory.",
              "limits": "Depends on annotation quality. With a single gold passage per question it is 0 or 1, the "
                        "same as Hit@k."}),
    entry("metric.precision", "metric", "retrieval", "Precision@k",
          facts={"keys": ["precision"], "needs": "gold", "better": "higher", "range": "unit"},
          related=("metric.recall", "concept.k", *_GOLD),
          pt={"summary": "Fração dos chunks finais que são relevantes, isto é, que cobrem algum trecho gold.",
              "how": "precision = chunks finais relevantes ÷ número de chunks finais.",
              "read": "Mede ruído no contexto. Cai naturalmente quando k cresce e há poucos trechos gold: com 1 trecho "
                      "gold e k = 10, o máximo possível é perto de 0,1.",
              "limits": "Um chunk útil que não foi anotado como gold conta como irrelevante. Compare precision só "
                        "entre runs com o mesmo k."},
          en={"summary": "Share of the final chunks that are relevant, i.e. cover some gold passage.",
              "how": "precision = relevant final chunks ÷ number of final chunks.",
              "read": "Measures noise in the context. It drops naturally as k grows with few gold passages: with 1 "
                      "gold passage and k = 10 the ceiling is about 0.1.",
              "limits": "A useful chunk that was not annotated as gold counts as irrelevant. Compare precision only "
                        "between runs with the same k."}),
    entry("metric.hit", "metric", "retrieval", "Hit@k",
          facts={"keys": ["hit"], "needs": "gold", "better": "higher", "range": "binary"},
          related=("metric.recall", "metric.mrr", *_GOLD),
          pt={"summary": "1 quando pelo menos um chunk final é relevante, 0 caso contrário.",
              "how": "Por pergunta é binária. No run, a média é a proporção de perguntas em que a recuperação achou "
                     "alguma evidência.",
              "read": "É o piso da recuperação: Hit@k baixo significa que a técnica nem chegou perto do trecho certo.",
              "limits": "Não distingue achar um trecho de achar todos, nem a posição em que ele apareceu."},
          en={"summary": "1 when at least one final chunk is relevant, 0 otherwise.",
              "how": "Binary per question. Over a run, the mean is the share of questions for which retrieval found "
                     "some evidence.",
              "read": "The floor of retrieval: a low Hit@k means the technique did not even get near the passage.",
              "limits": "Does not tell one passage from all of them, nor the position where it appeared."}),
    entry("metric.mrr", "metric", "retrieval", "MRR",
          facts={"keys": ["mrr"], "needs": "gold", "better": "higher", "range": "unit"},
          sources=("voorhees1999",), related=("metric.ndcg", "metric.hit", "component.reranker.none"),
          pt={"summary": "Mean Reciprocal Rank: o inverso da posição do primeiro chunk relevante.",
              "how": "Por pergunta, 1 ÷ posição do primeiro chunk relevante, ou 0 se não há nenhum. Primeiro lugar "
                     "vale 1, segundo 0,5, terceiro 0,33.",
              "read": "Mede a ordenação. É onde um reranker deve aparecer: mesmo recall, MRR maior.",
              "limits": "Só olha o primeiro acerto. A ordem avaliada é a dos chunks finais entregues pela técnica."},
          en={"summary": "Mean Reciprocal Rank: the inverse of the position of the first relevant chunk.",
              "how": "Per question, 1 ÷ rank of the first relevant chunk, or 0 when there is none. First place is 1, "
                     "second 0.5, third 0.33.",
              "read": "Measures ordering. It is where a reranker should show: same recall, higher MRR.",
              "limits": "Looks only at the first hit. The order evaluated is that of the technique's final chunks."}),
    entry("metric.ndcg", "metric", "retrieval", "nDCG@k",
          facts={"keys": ["ndcg"], "needs": "gold", "better": "higher", "range": "unit"},
          sources=("jarvelin2002",), related=("metric.mrr", "metric.recall"),
          pt={"summary": "Ganho acumulado com desconto pela posição, normalizado pelo melhor ranking possível.",
              "how": "DCG = soma de 1 ÷ log2(posição + 1) para cada chunk relevante. O ideal coloca todos os "
                     "relevantes no topo. nDCG = DCG ÷ DCG ideal. A relevância aqui é binária.",
              "read": "Resume em um número quantos relevantes vieram e quão no topo estão. Bom para comparar "
                      "rerankers e modos de recuperação.",
              "limits": "Com relevância binária e poucos trechos gold, fica muito parecido com o MRR."},
          en={"summary": "Position-discounted cumulative gain, normalized by the best possible ranking.",
              "how": "DCG = sum of 1 ÷ log2(rank + 1) over the relevant chunks. The ideal puts every relevant chunk "
                     "on top. nDCG = DCG ÷ ideal DCG. Relevance is binary here.",
              "read": "One number for how many relevant chunks came and how high they are. Good for comparing "
                      "rerankers and retrieval modes.",
              "limits": "With binary relevance and few gold passages it is very close to MRR."}),
    entry("metric.context_coverage", "metric", "retrieval", "Context coverage",
          facts={"keys": ["context_coverage"], "needs": "gold", "better": "higher", "range": "unit"},
          related=("metric.recall", "concept.context", "technique.context_compression"),
          pt={"summary": "Quanto do conteúdo dos trechos gold está no contexto realmente enviado ao modelo.",
              "how": "Para cada trecho gold, a fração de suas palavras de conteúdo presentes no texto final do "
                     "contexto. O valor é a média entre os trechos.",
              "read": "Complementa o recall: o recall olha os chunks escolhidos, esta métrica olha o que sobrou "
                      "depois de truncar em max_context_chars e de comprimir. Recall alto com cobertura baixa indica "
                      "que a evidência foi cortada.",
              "limits": "É lexical, por palavras soltas. Palavras comuns do domínio inflam o valor."},
          en={"summary": "How much of the gold passages' content is in the context actually sent to the model.",
              "how": "For each gold passage, the share of its content words present in the final context text. The "
                     "value is the mean over passages.",
              "read": "Complements recall: recall looks at the chosen chunks, this looks at what was left after "
                      "truncation to max_context_chars and compression. High recall with low coverage means the "
                      "evidence was cut.",
              "limits": "Lexical, on single words. Common domain words inflate it."}),
    # ── generation, reference based ──────────────────────────────────────────────────────────────────────────────
    entry("metric.f1", "metric", "generation_reference", "Token F1",
          facts={"keys": ["f1"], "needs": "expected", "better": "higher", "range": "unit"},
          sources=("rajpurkar2016",), related=("metric.exact_match", "metric.accuracy", "concept.expected_answer"),
          pt={"summary": "Sobreposição de palavras de conteúdo entre a resposta e a resposta esperada.",
              "how": "Sobre os conjuntos de palavras de conteúdo: precisão = comuns ÷ palavras da resposta, "
                     "recall = comuns ÷ palavras da esperada, F1 = média harmônica das duas.",
              "read": "Tolera respostas mais longas que a esperada melhor que o exact match, mas penaliza texto "
                      "extra. Respostas esperadas curtas tornam o F1 baixo para respostas completas e corretas.",
              "limits": "Não entende paráfrase nem sinônimo. Use o juiz ou revisão humana para afirmar qualidade."},
          en={"summary": "Content-word overlap between the answer and the expected answer.",
              "how": "Over the sets of content words: precision = common ÷ answer words, recall = common ÷ expected "
                     "words, F1 = their harmonic mean.",
              "read": "More tolerant of long answers than exact match, but extra text is penalized. Short expected "
                      "answers make F1 low for complete, correct answers.",
              "limits": "Does not understand paraphrase or synonyms. Use the judge or human review for quality "
                        "claims."}),
    entry("metric.exact_match", "metric", "generation_reference", "Exact match",
          facts={"keys": ["exact_match"], "needs": "expected", "better": "higher", "range": "binary"},
          sources=("rajpurkar2016",), related=("metric.f1", "concept.answer_type"),
          pt={"summary": "1 quando a resposta esperada aparece literalmente dentro da resposta.",
              "how": "Texto normalizado dos dois lados; a esperada precisa estar contida na resposta. Em perguntas "
                     "do tipo boolean, compara só o sinal sim ou não.",
              "read": "Boa para respostas curtas e factuais: valores, datas, nomes, sim ou não.",
              "limits": "Qualquer variação de formato zera: R$ 1.000,00 contra mil reais."},
          en={"summary": "1 when the expected answer appears literally inside the answer.",
              "how": "Both sides normalized; the expected answer must be contained in the answer. For boolean "
                     "questions only the yes or no sign is compared.",
              "read": "Good for short factual answers: amounts, dates, names, yes or no.",
              "limits": "Any formatting variation gives zero: $1,000.00 versus one thousand dollars."}),
    entry("metric.accuracy", "metric", "generation_reference", "Accuracy",
          facts={"keys": ["accuracy"], "needs": "expected", "better": "higher", "range": "unit"},
          related=("metric.f1", "concept.answer_type", "concept.quadrant"),
          pt={"summary": "Acerto da resposta conforme o tipo da pergunta.",
              "how": "boolean: 1 se o sinal sim ou não coincide. classification: 1 se o rótulo esperado aparece na "
                     "resposta. Nos demais casos, e quando o sinal não pode ser lido, vale o Token F1.",
              "read": "É a métrica usada no eixo de correção do quadrante. Para perguntas de extração ela é o próprio "
                      "F1, então não é uma porcentagem de acertos.",
              "limits": "Herda os limites lexicais do F1."},
          en={"summary": "Answer correctness according to the question type.",
              "how": "boolean: 1 when the yes or no sign matches. classification: 1 when the expected label appears "
                     "in the answer. Otherwise, and when the sign cannot be read, it is Token F1.",
              "read": "Used as the correctness axis of the quadrant. For extraction questions it is F1 itself, so it "
                      "is not a share of right answers.",
              "limits": "Inherits the lexical limits of F1."}),
    # ── generation, context based ────────────────────────────────────────────────────────────────────────────────
    entry("metric.faithfulness", "metric", "generation_context", "Faithfulness",
          facts={"keys": ["faithfulness"], "needs": "none", "better": "higher", "range": "unit"},
          sources=("es2023",), related=("metric.groundedness", "metric.judge_faithfulness", "metric.hallucination"),
          pt={"summary": "Fração das sentenças da resposta que têm apoio literal no contexto.",
              "how": "Cada sentença com mais de 20 caracteres é quebrada em trigramas de palavras. Ela conta como "
                     "apoiada quando pelo menos 30% dos trigramas aparecem no contexto. Cada expressão de "
                     "conhecimento externo, como geralmente ou com base no meu conhecimento, tira 0,15, até 0,5.",
              "read": "Só indica cópia próxima do texto. Uma resposta correta e reescrita com outras palavras pode "
                      "receber 0. No primeiro experimento real do projeto isso aconteceu com respostas claramente "
                      "corretas.",
              "limits": "Heurística lexical, não é a faithfulness por afirmações do RAGAS. Não use sozinha para "
                        "concluir que uma técnica alucina: confirme com Judge faithfulness ou lendo as respostas."},
          en={"summary": "Share of the answer's sentences with literal support in the context.",
              "how": "Each sentence longer than 20 characters is split into word trigrams. It counts as supported "
                     "when at least 30% of the trigrams appear in the context. Each outside-knowledge phrase, such "
                     "as generally or based on my knowledge, subtracts 0.15, up to 0.5.",
              "read": "It only signals near-copying. A correct answer rewritten in other words can get 0. That "
                      "happened with clearly correct answers in the project's first real experiment.",
              "limits": "A lexical heuristic, not the claim-based faithfulness of RAGAS. Do not use it alone to "
                        "conclude that a technique hallucinates: confirm with Judge faithfulness or by reading the "
                        "answers."}),
    entry("metric.groundedness", "metric", "generation_context", "Groundedness",
          facts={"keys": ["groundedness"], "needs": "none", "better": "higher", "range": "unit"},
          related=("metric.faithfulness",),
          pt={"summary": "Versão mais permissiva da faithfulness, sem a penalidade por conhecimento externo.",
              "how": "Mesma contagem por trigramas, com sentenças a partir de 15 caracteres e limiar de 25%.",
              "read": "Leia junto com a faithfulness. Diferença grande entre as duas vem de sentenças curtas ou das "
                      "expressões de conhecimento externo.",
              "limits": "Os mesmos da faithfulness: não entende paráfrase."},
          en={"summary": "A more permissive faithfulness, without the outside-knowledge penalty.",
              "how": "Same trigram count, with sentences from 15 characters and a 25% threshold.",
              "read": "Read it next to faithfulness. A large gap between them comes from short sentences or from "
                      "outside-knowledge phrases.",
              "limits": "The same as faithfulness: no understanding of paraphrase."}),
    entry("metric.citation_accuracy", "metric", "generation_context", "Citation accuracy",
          facts={"keys": ["citation_accuracy"], "needs": "none", "better": "higher", "range": "unit"},
          related=("concept.citation", "metric.faithfulness"),
          pt={"summary": "Fração das citações [n] que apontam para um trecho que de fato sustenta a sentença.",
              "how": "Para cada marcador [n], verifica se o trecho n existe no contexto e se pelo menos 30% das "
                     "palavras de conteúdo da sentença aparecem nele.",
              "read": "Fica vazia quando a resposta não cita nada: não há o que avaliar. Veja o n da métrica para "
                      "saber em quantas perguntas houve citação.",
              "limits": "Não mede se faltou citar. Uma resposta com uma única citação correta recebe 1."},
          en={"summary": "Share of [n] citations that point to a passage actually supporting the sentence.",
              "how": "For each [n] marker, checks that passage n exists in the context and that at least 30% of the "
                     "sentence's content words appear in it.",
              "read": "Empty when the answer cites nothing: there is nothing to assess. Check the metric's n to see "
                      "in how many questions a citation happened.",
              "limits": "Does not measure missing citations. An answer with one correct citation scores 1."}),
    entry("metric.hallucination", "metric", "generation_context", "Hallucination",
          facts={"keys": ["hallucination"], "needs": "none", "better": "lower", "range": "binary"},
          related=("metric.faithfulness", "metric.judge_faithfulness"),
          pt={"summary": "Sinal de alerta: a resposta apela a conhecimento externo ou traz um número ausente do "
                         "contexto.",
              "how": "Vale 1 se a resposta contém uma expressão de conhecimento externo ou se algum número escrito "
                     "nela não aparece no contexto. Senão vale 0.",
              "read": "No run, é a proporção de respostas com o alerta. Útil em domínios com valores, datas e "
                      "números de processo.",
              "limits": "Um número reformatado, como 10% contra 10 por cento ou 1.000 contra 1000, dispara o alerta. "
                        "Alucinações sem números não são detectadas."},
          en={"summary": "A warning flag: the answer appeals to outside knowledge or states a number absent from the "
                         "context.",
              "how": "1 when the answer contains an outside-knowledge phrase or any number written in it does not "
                     "appear in the context. Otherwise 0.",
              "read": "Over a run it is the share of flagged answers. Useful in domains with amounts, dates and case "
                      "numbers.",
              "limits": "A reformatted number, 10% versus 10 percent or 1,000 versus 1000, raises the flag. "
                        "Hallucinations without numbers go undetected."}),
    entry("metric.refusal", "metric", "generation_context", "Refusal",
          facts={"keys": ["refusal"], "needs": "none", "better": "context", "range": "binary"},
          related=("metric.recall", "metric.hallucination"),
          pt={"summary": "1 quando a resposta declara que o contexto não contém a informação.",
              "how": "Busca frases como o contexto não contém, não encontrei essa informação ou not enough "
                     "information.",
              "read": "Depende da pergunta. Recusar é correto quando a evidência não foi recuperada, e é falha "
                      "quando o recall foi 1. Cruze com o recall da mesma pergunta.",
              "limits": "Lista fixa de frases em português e inglês. Recusas com outra redação passam despercebidas."},
          en={"summary": "1 when the answer states that the context does not contain the information.",
              "how": "Looks for phrases such as the context does not contain, I cannot answer or not enough "
                     "information.",
              "read": "It depends on the question. Refusing is right when the evidence was not retrieved, and a "
                      "failure when recall was 1. Cross it with the recall of the same question.",
              "limits": "A fixed list of Portuguese and English phrases. Refusals worded differently are missed."}),
    # ── judge and human ──────────────────────────────────────────────────────────────────────────────────────────
    entry("metric.judge_faithfulness", "metric", "judge", "Judge faithfulness",
          facts={"keys": ["judge_faithfulness"], "needs": "judge", "better": "higher", "range": "unit"},
          sources=("zheng2023judge", "es2023"), related=("metric.faithfulness", "concept.judge"),
          pt={"summary": "Nota de 0 a 1 dada por um LLM sobre o quanto a resposta se sustenta no contexto.",
              "how": "Uma chamada ao modelo juiz por resposta, com a pergunta, a resposta e até 12.000 caracteres do "
                     "contexto, em temperatura 0. Notas de 0 a 10 ou de 0 a 100 são convertidas para 0 a 1.",
              "read": "Entende paráfrase, por isso é a referência quando a faithfulness lexical parece errada.",
              "limits": "Custa tokens e herda vieses do modelo juiz. O modelo e o hash do prompt ficam gravados com "
                        "cada nota. Com o provider simulado é uma regra lexical e só valida o encanamento."},
          en={"summary": "A 0 to 1 score given by an LLM for how well the answer is supported by the context.",
              "how": "One call to the judge model per answer, with the question, the answer and up to 12,000 "
                     "characters of context, at temperature 0. Scores from 0 to 10 or 0 to 100 are mapped to 0 to 1.",
              "read": "It understands paraphrase, so it is the reference when lexical faithfulness looks wrong.",
              "limits": "Costs tokens and inherits the judge model's biases. The model and the prompt hash are "
                        "stored with every score. With the mock provider it is a lexical rule and only validates "
                        "plumbing."}),
    entry("metric.judge_accuracy", "metric", "judge", "Judge accuracy",
          facts={"keys": ["judge_accuracy"], "needs": "judge+expected", "better": "higher", "range": "unit"},
          sources=("zheng2023judge",), related=("metric.accuracy", "metric.f1", "concept.judge"),
          pt={"summary": "Nota de 0 a 1 dada por um LLM comparando a resposta com a resposta esperada.",
              "how": "Uma chamada ao modelo juiz por resposta, com a pergunta, a resposta e a resposta esperada.",
              "read": "Substitui o Token F1 quando as respostas são longas ou parafraseadas.",
              "limits": "Exige resposta esperada e o juiz ligado. Não é determinística entre modelos juízes."},
          en={"summary": "A 0 to 1 score given by an LLM comparing the answer with the expected answer.",
              "how": "One call to the judge model per answer, with the question, the answer and the expected answer.",
              "read": "Replaces Token F1 when answers are long or paraphrased.",
              "limits": "Needs an expected answer and the judge enabled. Not deterministic across judge models."}),
    entry("metric.human_agreement", "metric", "judge", "Human review",
          facts={"keys": ["human_agreement"], "needs": "human", "better": "higher", "range": "unit"},
          related=("metric.judge_accuracy",),
          pt={"summary": "Concordância entre as métricas automáticas e o veredito de uma pessoa.",
              "how": "Revisões são registradas pela linha de comando, com ./rs evaluate review-add, e ligadas à "
                     "resposta avaliada.",
              "read": "É o que valida as métricas automáticas no seu domínio. Poucas dezenas de respostas revisadas "
                      "já mostram se F1 e juiz acompanham o julgamento humano.",
              "limits": "Ainda não há tela para revisar respostas no aplicativo."},
          en={"summary": "Agreement between the automatic metrics and a person's verdict.",
              "how": "Reviews are recorded from the command line, with ./rs evaluate review-add, and linked to the "
                     "assessed answer.",
              "read": "It is what validates the automatic metrics in your domain. A few dozen reviewed answers "
                      "already show whether F1 and the judge follow human judgement.",
              "limits": "There is no screen to review answers in the app yet."}),
    # ── efficiency ───────────────────────────────────────────────────────────────────────────────────────────────
    entry("metric.latency", "metric", "efficiency", "Latency",
          facts={"keys": ["latency_mean", "latency_total", "latency_median", "latency_by_stage"], "needs": "none",
                 "better": "lower", "range": "seconds"},
          related=("metric.llm_calls", "concept.index"),
          pt={"summary": "Tempo de parede por pergunta, total e por etapa.",
              "how": "Cada etapa da técnica é cronometrada pelo executor: query_transform, retrieval, rerank, "
                     "compression, control, context, generation. A latência do run é a média entre as perguntas.",
              "read": "Olhe as etapas para saber onde o tempo foi gasto. Com API remota, a geração domina e a rede "
                      "adiciona ruído: diferenças pequenas não são conclusivas.",
              "limits": "raptor, graph_rag, light_rag e hippo_rag constroem sua estrutura na primeira pergunta, "
                        "que por isso fica mais lenta. O tempo de construir o índice fica fora do run."},
          en={"summary": "Wall-clock time per question, total and per stage.",
              "how": "Each stage of the technique is timed by the runner: query_transform, retrieval, rerank, "
                     "compression, control, context, generation. Run latency is the mean over questions.",
              "read": "Look at the stages to see where the time went. With a remote API, generation dominates and "
                      "the network adds noise: small differences are not conclusive.",
              "limits": "raptor, graph_rag, light_rag and hippo_rag build their structure on the first question, "
                        "which is therefore slower. Index build time is outside the run."}),
    entry("metric.llm_calls", "metric", "efficiency", "LLM calls / question",
          facts={"keys": ["llm_calls_per_question", "llm_calls"], "needs": "none", "better": "lower",
                 "range": "count"},
          related=("metric.tokens", "metric.cost"),
          pt={"summary": "Número médio de chamadas ao modelo de linguagem para responder uma pergunta.",
              "how": "Contado pelo executor em cada chamada feita pela técnica, inclusive as do reranker llm.",
              "read": "É o custo estrutural da técnica, independente de preço e de rede. naive faz 1 chamada. "
                      "Técnicas de consulta fazem 2. As iterativas e as que avaliam cada chunk fazem várias.",
              "limits": "Chamadas do juiz e da construção do índice não entram aqui."},
          en={"summary": "Mean number of language-model calls needed to answer one question.",
              "how": "Counted by the runner on every call the technique makes, including those of the llm reranker.",
              "read": "The structural cost of the technique, independent of price and network. naive makes 1 call. "
                      "Query techniques make 2. Iterative ones and those grading each chunk make several.",
              "limits": "Judge calls and index-build calls are not included."}),
    entry("metric.tokens", "metric", "efficiency", "Tokens",
          facts={"keys": ["prompt_tokens", "completion_tokens", "embedding_tokens"], "needs": "none",
                 "better": "lower", "range": "count"},
          related=("metric.cost", "metric.context_chars"),
          pt={"summary": "Tokens de entrada, de saída e de embedding consumidos pelo run.",
              "how": "Somados a partir do que o provider informa em cada resposta. No run são totais, não médias.",
              "read": "Tokens de entrada crescem com k, com o tamanho do chunk e com o número de chamadas. São a "
                      "maior parte do custo.",
              "limits": "Embeddings já em cache não gastam tokens de novo, então um segundo run sobre o mesmo índice "
                        "mostra menos tokens de embedding."},
          en={"summary": "Prompt, completion and embedding tokens used by the run.",
              "how": "Summed from what the provider reports in each response. They are run totals, not means.",
              "read": "Prompt tokens grow with k, chunk size and number of calls. They are most of the cost.",
              "limits": "Cached embeddings do not spend tokens again, so a second run on the same index shows fewer "
                        "embedding tokens."}),
    entry("metric.cost", "metric", "efficiency", "Cost",
          facts={"keys": ["cost_usd"], "needs": "none", "better": "lower", "range": "usd"},
          related=("metric.tokens", "guide.cost"),
          pt={"summary": "Custo em dólares calculado dos tokens e da tabela de preços do projeto.",
              "how": "tokens × preço do modelo em ragstudio/providers/pricing.json. O custo do run é a soma das "
                     "perguntas.",
              "read": "Compare junto com a qualidade: custo por ponto de recall ou de F1 ganho sobre o naive.",
              "limits": "Modelo sem preço na tabela deixa o custo vazio, nunca zero. A tabela é local e pode estar "
                        "desatualizada em relação ao provedor. O custo de construir o índice fica registrado no "
                        "índice, fora do run."},
          en={"summary": "Cost in dollars computed from tokens and the project's price table.",
              "how": "tokens × model price in ragstudio/providers/pricing.json. Run cost is the sum over questions.",
              "read": "Compare it with quality: cost per point of recall or F1 gained over naive.",
              "limits": "A model without a price leaves cost empty, never zero. The table is local and may lag the "
                        "provider. Index build cost is recorded on the index, outside the run."}),
    entry("metric.context_chars", "metric", "efficiency", "Context chars",
          facts={"keys": ["context_chars_mean", "context_chars"], "needs": "none", "better": "context",
                 "range": "chars"},
          sources=("liu2023",), related=("concept.context", "metric.context_coverage"),
          pt={"summary": "Tamanho médio do contexto enviado ao modelo na chamada final.",
              "how": "Caracteres do texto de contexto depois da montagem e do corte em max_context_chars.",
              "read": "Controle para comparações justas. parent_child e sentence_window aumentam o contexto, "
                      "context_compression diminui. Um ganho de qualidade pode vir só de mais texto.",
              "limits": "Menos não é sempre melhor: o que importa é a qualidade obtida por caractere enviado."},
          en={"summary": "Mean size of the context sent to the model in the final call.",
              "how": "Characters of the context text after assembly and truncation to max_context_chars.",
              "read": "A control for fair comparisons. parent_child and sentence_window enlarge the context, "
                      "context_compression shrinks it. A quality gain may come only from more text.",
              "limits": "Less is not always better: what matters is the quality obtained per character sent."}),
]
