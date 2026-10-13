# Adicionando uma técnica

Uma técnica é **um módulo** com duas coisas: `SPEC` e `run`. O núcleo não precisa ser alterado: o registry descobre o
módulo, o executor monta as dependências e a validação garante que o resultado é comparável com o das outras.

## 1. Onde colocar

- Técnica simples: `ragstudio/techniques/<nome>.py`.
- Técnica com componentes próprios (heurísticas, índice auxiliar, adaptador): subpacote
  `ragstudio/techniques/<nome>/` com `__init__.py` e `technique.py`. Veja `rag_evo/`.
- Fora do repositório: qualquer pasta listada em `RAGSTUDIO_TECHNIQUES_PATH`.

Nomes iniciados por `_` são ignorados pelo registry.

## 2. Esqueleto mínimo

```python
"""Uma linha dizendo o que a técnica faz e a referência."""
from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, pool_size, select

SPEC = TechniqueSpec(
    name="minha_tecnica", title="Minha Técnica", version="0.1.0", family="query",
    description="One sentence in English.",
    params={"n": Param(3, "what it controls")},
    reference="https://...", origin="new",
    status="prototype",          # implemented | prototype | adapter | mock | pending
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)          # defaults + validação de nomes e tipos
    question = request.query.text
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
    chunks = select(deps, question, pool, request.k)          # reranker do run, ou ordem por score
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context, {"n": params["n"]})
```

## 3. O que `deps` oferece

| Membro | Uso |
|---|---|
| `deps.ask(task, **variáveis)` | renderiza o prompt versionado `task` e chama o LLM |
| `deps.ask_tool(task, tools, **variáveis)` | o mesmo, oferecendo ferramentas (`Tool`) por tool calling nativo; devolve um `ToolCall` |
| `deps.embed(textos)` | vetores de embedding |
| `deps.log_retrieval(query, modo, itens)` | registra como evidência um ranking calculado pela própria técnica (grafo, árvore) |
| `deps.retrieve(query, k, mode=None, query_vector=None, filters=None, **opções)` | busca no índice do run |
| `deps.rerank(query, chunks, k)` | reranker do run; sem reranker, ordena por score e corta |
| `deps.stage(nome)` | atribui o tempo a uma etapa |
| `deps.store` | chunks, embeddings, texto dos documentos, `aux_load` / `aux_save` |
| `deps.seed`, `deps.language`, `deps.llm_model`, `deps.has_reranker` | contexto do run |

Tudo que passa por `deps` já é medido (tempo, tokens, chamadas por tarefa) e gravado como evidência. Por isso a
técnica **não** deve abrir conexões, ler configuração, escolher modelo nem chamar providers diretamente.

Etapas canônicas: `query_transform`, `retrieval`, `rerank`, `compression`, `context`, `generation`, `control`.
`retrieval` e `generation` são obrigatórias. Outros nomes são aceitos (por exemplo `index_build`).

## 4. Prompts novos

Adicione a tarefa em `ragstudio/prompts/templates.py`, nos dois idiomas (`pt` e `en`), e uma regra em
`ragstudio/providers/mock.py` (`_RULES`) para que a técnica rode offline. Alterar um template muda o hash gravado
em cada run.

## 5. Regras do contrato (verificadas por `validate_result`)

- retornar `TechniqueResult`, de preferência via `finish(...)`;
- `diagnostics["technique"] == SPEC.name` e `diagnostics` serializável em JSON;
- toda citação e todo chunk do contexto precisam estar em `contexts`;
- `timings` cobre `retrieval` e `generation`.

Convenções:

- Texto alterado (compressão, expansão) usa `item.with_text(...)` ou um novo `Chunk` com os offsets corretos, para que as métricas de recuperação continuem válidas.
- Estrutura auxiliar cara vai em `deps.store.aux_save(nome, dados)` com chave que inclua o modelo usado. Registre `built_now` em `diagnostics`.
- Limitações vão em `warnings` e no docstring. Status `implemented` só com teste passando.
- Uma dependência opcional é importada dentro da função, com erro claro quando ausente.

## 6. Testes

`tests/techniques/test_all_techniques.py` já roda **toda** técnica registrada em três configurações, verifica o
contrato, o determinismo com o mock, a rejeição de parâmetro desconhecido e o respeito ao limite de contexto.
Atualize o conjunto `EXPECTED` desse arquivo e acrescente em `tests/techniques/test_specific.py` um teste do que
torna a técnica o que ela é.

```bash
RAGSTUDIO_PROVIDER=mock ./rs techniques describe --name minha_tecnica
scripts/check.sh
```

## 7. Usando

```yaml
techniques:
  - name: minha_tecnica
    grid: {n: [2, 4]}
```

Acrescente a linha em `docs/techniques.md` e marque o item no `ROADMAP.md`.

## Outros pontos de extensão

| O quê | Onde | Registro |
|---|---|---|
| Estratégia de chunking | `processing/chunking/<nome>.py` com `spans(text, **opções)` | `STRATEGIES` em `processing/chunking/__init__.py` |
| Modo de recuperação | `retrieval/<nome>.py` | `MODES` e `retrieve()` em `retrieval/__init__.py` |
| Reranker | `rerankers/<nome>.py` | `build()` em `rerankers/__init__.py` |
| Store de índice | `stores/<nome>.py` com a interface de `stores/base.py` | `create()` e `load()` em `stores/__init__.py` |
| Loader de documento | `ingest/loaders/<nome>.py` com `load(path)` | `LOADERS` em `ingest/loaders/__init__.py` |
| Provider | builder de `Endpoint` em `providers/` | `resolve_endpoint()` em `providers/routing.py` |
| Métrica | `evaluation/*_metrics.py` | coluna em nova migração, `Repo.add_metrics`, `MEAN_METRICS` em `evaluation/aggregate.py` |
