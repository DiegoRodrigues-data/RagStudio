# Comparando técnicas

## Métricas

| Grupo | Métricas | Exige |
|---|---|---|
| Eficiência | latência total e por etapa, tokens, chamadas ao LLM por pergunta, custo, tamanho do contexto | nada |
| Geração, baseadas no contexto | `faithfulness`, `groundedness`, `citation_accuracy`, `hallucination`, `refusal` | nada |
| Recuperação | `hit`, `recall`, `precision`, `mrr`, `ndcg`, `context_coverage` | gold passages |
| Geração, baseadas em referência | `exact_match`, `f1`, `accuracy` | resposta esperada |
| Juiz | `judge_accuracy`, `judge_faithfulness` | `evaluation.judge: true` |
| Humano | concordância com revisão humana | `evaluate review-add` |

Sem a anotação exigida, a métrica fica vazia e aparece em `requires_annotation` com o motivo. Não vira zero.
Cada agregado traz `<métrica>_n`, o número de perguntas em que foi medida.

Definições que importam:

- Um chunk é relevante para um gold passage do mesmo documento se cobre pelo menos metade do trecho (por offsets)
  ou se contém o texto normalizado.
- As métricas de recuperação são calculadas sobre os chunks **finais** da técnica, na ordem em que ela os entregou.
- `context_coverage` mede o contexto realmente enviado ao modelo, então captura perdas por truncamento e compressão.
- As métricas de geração são heurísticas lexicais portadas do JudDoc_Ex. Não entendem paráfrase.
- `hallucination` vale 1 quando a resposta apela a conhecimento externo ou traz número ausente do contexto.

## Comandos

```bash
./rs compare runbook --id <rb_id> --by technique       # ou chunking, retrieval_mode, reranker, k, llm, seed...
./rs compare runs --ids <run_a>,<run_b>                # pareado, por pergunta
./rs compare characteristics --runbook-id <rb_id>
./rs evaluate rerun --run-id <run_id> --judge          # nova versão de avaliação, sem reexecutar
```

`--id` e `--runbook-ids` aceitam vários runbooks separados por vírgula, para comparar entre corpora.

### Comparação pareada

`compare runs` devolve, por métrica, a diferença média (b − a), intervalo de confiança por bootstrap, teste t
pareado, Wilcoxon (aproximação normal, sinalizada quando há menos de 10 pares), teste de permutação por troca de
sinal (exato até 12 pares) e o tamanho de efeito de Cohen. Os p-valores de permutação são corrigidos por Holm entre
as métricas testadas. Com poucas perguntas esses testes têm pouco poder: leia o intervalo.

### Características dos documentos

Para cada resposta, o documento-alvo é o do gold passage, ou o primeiro recuperado quando não há gold. O perfil
desse documento é juntado às métricas. A saída traz correlações de Spearman por técnica, médias por tercis de tamanho
e médias por idioma, formato e corpus. Com poucos documentos isso é descritivo; o campo `documents` diz quantos são.

## Relatórios e exportações

```bash
./rs reports html --runbook-ids <rb_id> --output relatorio.html
./rs reports figures --runbook-ids <rb_id> --output figuras/
./rs reports tables --runbook-ids <rb_id> --format latex --by technique
./rs reports export --runbook-ids <rb_id> --table questions --format parquet
./rs reports schema
```

O HTML é autocontido, em inglês, com tabela por técnica, figuras, runs, disponibilidade de métricas, correlações,
setup experimental e verificação da cadeia de evidências. As figuras saem em PNG 300 dpi, SVG e PDF. Figura sem dados
é pulada e listada. Toda exportação tem caminho e SHA-256 registrados (`reports list`).

Tabelas exportáveis: `runs` (uma linha por run), `questions` (uma linha por run × pergunta) e `characteristics`
(a anterior com o perfil do documento-alvo e do índice).

## Cuidados ao interpretar

- Compare técnicas com o mesmo `index_hash`. Mudar chunking ou embedding muda o índice, e a diferença deixa de ser só da técnica.
- `parent_child`, `sentence_window` e `context_compression` mudam o tamanho do contexto. Olhe `context_chars_mean` junto com a acurácia.
- `raptor` e `graph_rag` constroem estruturas na primeira pergunta. A latência e as chamadas dessa pergunta incluem a construção (`diagnostics.built_now`).
- O custo de construir o índice fica em `indices.build_usage`, fora do custo do run.
