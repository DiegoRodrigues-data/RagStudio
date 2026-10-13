# Executando experimentos

Todos os exemplos usam `./rs`. Para rodar sem custo, `export RAGSTUDIO_PROVIDER=mock`.

## 1. Corpus

```bash
./rs corpus import --path ./meus_documentos --name meu-corpus --clean all
./rs corpus profile --name meu-corpus
```

Formatos: `.md`, `.txt`, `.json`/`.jsonl` (lista de `{"id", "text", ...metadados}`) e `.pdf` (convertido com Docling,
alguns segundos por documento). O texto é normalizado na importação (quebras de linha, BOM, espaços finais) e é sobre esse
texto que valem todos os offsets. `--clean` aceita `all` ou uma lista de flags: `remove_image_tags`,
`remove_repeated_headers`, `collapse_blank_lines`, `remove_print_metadata`.

O perfil guarda, por documento, tamanho, palavras, parágrafos, títulos, razão de linhas de tabela e de lista,
densidade de dígitos, riqueza de vocabulário, idioma e formato. São as variáveis independentes da análise empírica.

### Splits

```bash
./rs corpus split --name meu-corpus --train 0.6 --validation 0.2 --test 0.2 --seed 42
./rs corpus split --name meu-corpus --assign '{"train": ["doc-a"], "test": ["doc-b", "doc-c"]}'
```

Um runbook com `split: test` indexa só os documentos desse split e só faz as perguntas que pertencem a ele. Se uma
pergunta marcada com o split tem gold passage em documento de fora, a criação do runbook falha com `LeakageError`.
Um question set com perguntas marcadas não pode ser usado sem declarar `split`.

## 2. Perguntas

```bash
./rs questions import-json --path perguntas.json --corpus meu-corpus
./rs evaluate availability --question-set minhas-perguntas
```

Formato do arquivo:

```json
{"name": "minhas-perguntas", "language": "pt", "questions": [
  {"code": "Q1", "text": "Qual é o limite de Betz?",
   "expected_answer": "59,3%", "answer_type": "extraction", "split": "test",
   "gold_passages": [{"document_id": "energia-eolica", "text": "trecho literal do documento"}]}
]}
```

`expected_answer` e `gold_passages` são opcionais, e definem quais métricas existem. Com `--corpus`, cada gold passage
é localizado no documento e ancorado por offsets; se o trecho não existir literalmente, a importação falha. Editar
uma pergunta já usada por um run concluído cria uma nova versão e arquiva a antiga.

## 3. Runbook

Um runbook é uma grade. Cada eixo aceita um valor ou uma lista; há um run por combinação.

```yaml
name: comparacao
corpus: meu-corpus
question_set: minhas-perguntas
split: test                      # opcional
techniques:
  - naive
  - name: mmr_rag
    grid: {lambda_: [0.3, 0.6, 0.9]}     # um run por valor
  - name: rag_evo
    params: {rounds: 3}                  # valor fixo
chunking:
  - {strategy: fixed, size: 1000, overlap: 150}
  - {strategy: sentence, size: 400, overlap: 80}   # fixed | recursive | sentence | semantic | markdown_headers | parent_child
embedding_models: [text-embedding-3-small]
llms: [gpt-4o-mini]
retrieval_modes: [dense, hybrid]         # dense | bm25 | hybrid | rrf | mmr
rerankers: [none, llm]                   # none | lexical | llm | cross_encoder
k: [3, 5]
seeds: [42, 43]
store: memory                            # memory | duckdb | faiss | chroma
enrich: null                             # ou contextual (1 chamada ao LLM por chunk na indexação)
language: pt
max_context_chars: 6000
evaluation: {judge: false, judge_model: null}
max_budget_usd: 5.00
limit_questions: null
prune: true                              # false mantém a grade inteira, com combinações redundantes
```

Com `prune: true` o runbook não cria runs redundantes (a técnica ignora o eixo variado) nem incompatíveis (a técnica
exige um índice que a combinação não constrói). `experiments preview` devolve o resumo em `pruned`. As regras por
técnica estão em `docs/techniques.md`. O chunking `semantic` gasta um embedding por sentença na indexação, registrado
em `build_usage.chunking_embedding_tokens`.

Um reranker ou store cujo pacote Python não está instalado é recusado na criação do runbook, com o `pip install` necessário. `./rs experiments options` lista o que está disponível. Se um runbook terminar com runs falhos, corrija a causa e rode de novo o mesmo runbook: os concluídos são pulados e só os falhos são refeitos.

`preset: quick | comparative | full` preenche técnicas, modos e seeds; `techniques: all` usa todo o catálogo.

```bash
./rs experiments preview --file runbook.yaml     # quantos runs, perguntas, estimativa
./rs experiments run --file runbook.yaml --stream
./rs experiments status --id <rb_id>
./rs experiments show --run-id <run_id> --full
```

A estimativa de custo é um **piso**: uma chamada por pergunta. Técnicas com várias chamadas custam mais. Modelo sem
preço em `ragstudio/providers/pricing.json` resulta em `cost_usd: null`, nunca em zero.

## 4. O que acontece na execução

1. Dados resolvidos: documentos do split, perguntas filtradas, verificação de vazamento.
2. Índice construído ou reaproveitado. O hash cobre documentos, chunking, modelo de embedding, store, split e
   enriquecimento, então técnicas com a mesma indexação compartilham vetores.
3. Snapshot de ambiente e primeiro evento de evidência.
4. Para cada pergunta: dependências instrumentadas, `technique.run`, validação do resultado, gravação de resposta,
   chunks, eventos, métricas e artefato JSONL.
5. Agregados do run e fechamento. Run concluído é imutável.

Interrupção: `Ctrl+C` ou `SIGTERM` marca o run como `cancelled`. Rodar de novo o mesmo runbook pula os concluídos e
refaz do zero os que não terminaram. Uma pergunta que falha é registrada e o run continua; se todas falham, o run
fica `failed` e o runbook segue para o próximo.

Orçamento: com `max_budget_usd`, o runbook para **antes do próximo run** quando o gasto medido atinge o limite. Um
run em andamento não é interrompido no meio.

## 5. Reprodução e evidência

```bash
./rs experiments reproduce --run-id <run_id> --dry-run   # configuração e requisições gravadas
./rs experiments reproduce --run-id <run_id>             # réplica ligada por replicates_run_id
./rs experiments verify --id <rb_id>                     # recalcula a cadeia de hashes
```

Cada run guarda `config_hash`, `index_hash`, prompts por hash, toda requisição e resposta, recuperações, avaliações
e o ambiente. A réplica informa quantas respostas saíram idênticas. Com provider real, respostas idênticas dependem
de o provedor honrar `seed` e temperatura 0.

## 6. Índices diretamente

```bash
./rs index build --corpus meu-corpus --strategy fixed --size 800 --overlap 100
./rs index search --index <hash> --query "pergunta" --mode hybrid --k 5
```
