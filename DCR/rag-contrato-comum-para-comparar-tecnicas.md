# Contrato único para executar e comparar técnicas RAG no mesmo ambiente

Especificação reaproveitável de como fazer técnicas RAG diferentes (naive, HyDE, multi-query, iterativas, compressão,
grafo, agente) rodarem pelo mesmo executor e produzirem dados comparáveis: mesma medição de tempo, tokens e chamadas,
mesma trilha de evidências, mesmo índice. Extraída do projeto RagStudio, mas não depende dele.

- **Origem:** RagStudio, outubro de 2026.
- **Versões em que tudo foi medido:** Python 3.11, numpy 2.2.6, SQLite 3.53.4, DuckDB 1.4.1, pandas 2.3.3,
  matplotlib 3.10.6, macOS 27 em Apple M5.
- **Implementação de referência:** `ragstudio/core/contract.py`, `ragstudio/core/pipeline.py`,
  `ragstudio/core/registry.py`, `ragstudio/experiments/deps.py`, `ragstudio/experiments/index_builder.py`,
  `ragstudio/providers/mock.py`, `ragstudio/evaluation/`, `tests/techniques/test_all_techniques.py`.

**Limite importante deste documento:** tudo abaixo foi verificado com um provider simulado e com um servidor HTTP
falso compatível com OpenAI. Nenhuma execução com modelo de linguagem real foi feita. As lições são sobre
arquitetura e instrumentação, não sobre qual técnica responde melhor.

## 1. Quando usar

Use quando a pergunta é "qual técnica RAG se sai melhor **neste** corpus" e a resposta precisa ser defendida com
números. O desenho serve para dezenas de técnicas e centenas de runs em uma máquina.

Não use como camada de produção de um chatbot: cada chamada grava evidência completa (prompt e resposta) em SQLite,
o que é caro e desnecessário fora de experimento. Também não resolve corpora que não cabem em RAM com o índice padrão.

## 2. Arquitetura

| Parte | Papel | Por que existe |
|---|---|---|
| `TechniqueSpec` | nome, versão, parâmetros com default, status, referência | parâmetro desconhecido é erro antes de gastar token; a versão entra no hash do run |
| `run(request, deps) -> TechniqueResult` | a técnica | uma única assinatura para o executor chamar |
| `deps` instrumentado | `ask`, `embed`, `retrieve`, `rerank`, `stage` | a medição mora fora da técnica, então é igual para todas |
| Blocos de pipeline | `merge_pool`, `select`, `generate`, `finish` | evita que cada técnica reimplemente contexto, citações e empacotamento |
| Registry por descoberta | lista módulos de um pacote e de pastas externas | adicionar técnica não toca no núcleo |
| `validate_result` | checagem estrutural de todo resultado | uma técnica mal escrita falha na hora, não na análise |
| Índice por hash | chunks + vetores identificados pelo que os determina | técnicas com a mesma indexação compartilham vetores |
| Provider simulado por tarefa | regra determinística por tipo de prompt | toda técnica roda offline, inclusive as de várias chamadas |

Fluxo de uma pergunta: o executor cria um `deps` novo (cronômetro e contador zerados), chama `run`, valida, grava
resposta, chunks, eventos e métricas.

## 3. A técnica não chama o modelo: ela pede uma tarefa

A decisão que mais simplificou o resto foi a técnica chamar `deps.ask("hypo_doc", query=...)` em vez de montar um
prompt e chamar um LLM.

```python
def run(request, deps):
    with deps.stage("query_transform"):
        hypothetical = deps.ask("hypo_doc", query=request.query.text)
        vector = deps.embed([hypothetical])[0]
    with deps.stage("retrieval"):
        pool = deps.retrieve(hypothetical, request.k, query_vector=vector)
    chunks = select(deps, request.query.text, pool, request.k)
    answer, context = generate(deps, request.query.text, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context, {"hypothetical_document": hypothetical})
```

O que isso dá de graça:

- **Chamadas por tarefa.** O contador sabe que um run fez 1 `hypo_doc` e 1 `answer` por pergunta. Medido no corpus de
  teste (6 perguntas): naive 1 chamada por pergunta, HyDE 2, iterativa com 2 rodadas 3, compressão com k=3 4,
  corretiva com k=3 7. Sem isso, comparar acurácia entre técnicas esconde que uma custa sete vezes mais.
- **Prompt versionado por hash.** O template é identificado por `sha256(system + template)`, independente das
  variáveis. O evento de requisição guarda só o hash e o texto final.
- **Simulação sem parsing.** O provider simulado recebe a tarefa e as variáveis, então não precisa adivinhar a
  intenção a partir do texto do prompt.

**Armadilha:** o projeto de referência anterior simulava o LLM extraindo contexto e pergunta do prompt por regex.
Isso quebra a cada mudança de template e não cobre prompts de controle (reordenar, decompor, avaliar relevância).

## 4. Provider simulado: uma regra por tarefa

Dezesseis regras determinísticas, cada uma de 2 a 8 linhas: resposta extrativa (a sentença do contexto com mais
termos da pergunta, com marcador `[n]`), reformulações (subconjuntos dos termos), documento hipotético, decomposição
(corta em " e ", vírgula), extração, consulta de lacuna, ordenação, confiança, relevância (sim se a sobreposição de
termos for pelo menos 0,34), resumo, entidades (palavras capitalizadas), decisão de agente por número do passo, e
duas notas de juiz. Embedding: saco de palavras com hash em 96 dimensões.

Resultado: 235 testes, 16 técnicas em 3 configurações cada, rodam em 6,3 s no Apple M5.

**Armadilha:** o embedding de 96 dimensões é grosseiro. Um teste que exigia que a decomposição trouxesse dois
trechos específicos falhou com busca densa e passou com BM25. Teste que depende de um trecho específico deve usar
recuperação lexical; o embedding simulado só garante encanamento.

**Armadilha:** resultado simulado parece resultado. O relatório HTML mostra um aviso fixo quando o provider é o
simulado, e o snapshot de ambiente grava o provider de cada run.

## 5. Índice compartilhado por hash

```python
index_hash = sha256(canonical_json({
    "documents": sorted((doc.id, doc.sha256) for doc in documents),
    "chunking": normalized_chunking, "embedding": [provider, model],
    "store": store_kind, "split": split, "enrich": enrich, "enrich_model": model_if_enriched}))
```

Num runbook de 3 técnicas sobre a mesma indexação, o primeiro run constrói e os outros dois reaproveitam; o teste
confere `index_reused == [False, True, True]`. Mudar um caractere de um documento ou 1 no tamanho do chunk muda o hash.

Por que cada campo: o split entra porque um índice de teste não pode conter documentos de treino; o enriquecimento
entra porque muda o texto indexado; o tipo de store entra porque os arquivos são diferentes.

**Invariante que vale a pena impor:** `document.text[chunk.char_start:chunk.char_end] == chunk.text` para toda
estratégia de chunking, com teste parametrizado. Dele dependem a ancoragem de gold passages por offset, a expansão
para o chunk pai e a janela de sentenças. Consequência: enriquecimento contextual altera o *texto indexado* (prefixo
+ chunk), guardado à parte, e nunca o texto do chunk.

## 6. Validação estrutural do resultado

Aplicada pelo executor a todo resultado:

- citações e ids do contexto têm de estar em `contexts`;
- tempos cobrem `retrieval` e `generation`;
- `diagnostics` é serializável e traz o nome da técnica.

Caso que não deve disparar: uma técnica pode entregar em `contexts` chunks que não existem no índice (resumo de
cluster, chunk pai, janela expandida). A validação compara com `contexts`, não com o índice.

## 7. Métrica ausente é ausente

- Sem gold passages, métricas de recuperação retornam `None`. Sem resposta esperada, acurácia retorna `None`.
- Agregados trazem `<métrica>_n` (em quantas perguntas foi medida). No corpus de teste, 6 perguntas, 4 com gold e
  5 com resposta esperada: `recall_n = 4`, `f1_n = 5`, `faithfulness_n = 6`.
- Preço de modelo desconhecido resulta em custo `None`, e a soma de um run com uma parcela desconhecida é `None`.
- Cada run guarda a lista do que foi medido, do que foi medido parcialmente e do que exige anotação, com o motivo.

**Armadilha encontrada no código de referência anterior:** a agregação usava média de lista vazia igual a 0,0.
Um run sem gabarito aparecia com recall 0, indistinguível de uma técnica ruim.

**Armadilha encontrada aqui:** `config.get("k") or default` aceitou `k = 0` silenciosamente e trocou pelo default.
Só apareceu porque havia um teste de configuração inválida. Valide número com `is not None`.

## 8. Relevância de chunk por offset

Um chunk é relevante para um gold passage do mesmo documento se cobre pelo menos 50% do trecho por offsets, ou se
contém o texto normalizado. O limite de 50% existe porque um gold pode cair na fronteira entre dois chunks com
sobreposição: exigir 100% zeraria o recall por acidente de corte; aceitar qualquer interseção contaria como acerto
um chunk que pegou três caracteres. Gold passages são ancorados na importação e a importação falha se o trecho não
existe literalmente no documento, porque um gold não ancorado transforma a métrica em ruído sem avisar.

## Testes e regressão

- Um teste parametrizado sobre o registry roda toda técnica em três configurações (padrão, reranker LLM, busca
  híbrida) e verifica contrato, determinismo, rejeição de parâmetro desconhecido e limite de contexto. Técnica nova
  entra nesses testes sem escrever nada.
- Um teste por técnica verifica o que a define: HyDE busca com o documento hipotético, a iterativa faz N rodadas,
  a compressão reduz o contexto, MMR com lambda 0,1 seleciona chunks diferentes de lambda 1,0.
- O cliente HTTP é testado contra um servidor falso local compatível com OpenAI (chat, embeddings em lotes,
  429 e 503 com nova tentativa, 400 sem nova tentativa, servidor inacessível) e um runbook inteiro roda contra ele.
- Corpus de teste: três documentos em Markdown de cerca de 1.100 caracteres, seis perguntas, quatro com gold.

## O que foi testado e não ajudou

- **Teste de trecho específico com embedding simulado.** Falhou; trocado por BM25 (seção 4).
- **Rótulos diretos no fim das linhas em gráfico de recall por k.** Com séries coincidentes os rótulos se
  sobrepuseram. Ficou só a legenda, com eixo de 0 a 1.

## Problemas conhecidos e não resolvidos

- Estruturas auxiliares (resumos de cluster, grafo de entidades) são construídas na primeira pergunta do run, e o
  custo dessa construção cai nessa pergunta. Está sinalizado em `diagnostics`, mas distorce a latência média.
- O custo de construir o índice não entra no custo do run.
- Orçamento só é verificado entre runs, não no meio de um.
- As métricas de geração são lexicais e não entendem paráfrase.

## Ainda não avaliado

- Qualquer comportamento com LLM real: aderência dos modelos aos formatos pedidos (lista sem numeração, "sim/não",
  número de 0 a 1), custo real, reprodutibilidade com `seed`. Não foi medido.
- Desempenho do índice em memória acima de poucos milhares de chunks. Não foi medido.
- Se as heurísticas de fidelidade concordam com um juiz LLM ou com humanos. Não foi medido.

## Roteiro para adotar em outro projeto

1. Defina os registros imutáveis: documento, chunk com offsets, chunk recuperado, contexto, resposta, uso, tempo.
2. Defina `Spec`, `Request`, `Result` e a função de validação. Escreva o teste da validação primeiro.
3. Escreva o provider simulado com uma regra por tarefa de prompt e o embedding por hash.
4. Escreva o `deps` instrumentado: toda chamada a modelo e toda busca passam por ele e geram evento.
5. Implemente a técnica mais simples usando só `deps` e os blocos comuns. Se precisar de algo fora de `deps`, o
   contrato está incompleto: amplie `deps`, não abra exceção na técnica.
6. Escreva o teste parametrizado sobre o registry antes da segunda técnica.
7. Identifique o índice por hash do que o determina e imponha o invariante de offsets.
8. Faça toda métrica devolver ausência quando falta anotação, e carregue a contagem junto do agregado.
9. Só então adicione técnicas. Cada uma declara status honesto e o que falta em relação ao artigo.
10. Antes de publicar qualquer número, rode com um modelo real.
