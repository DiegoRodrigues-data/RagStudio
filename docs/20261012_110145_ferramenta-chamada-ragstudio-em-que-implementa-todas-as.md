# Prompt gerado para Claude

## Solicitação original

ferramenta chamada RagStudio, em que implementa todas as tecnicas RAG replicaveis e implementa elas seguindo um fluxo documento->processamento->resultado, a ideia é poder comparar todas as técnicas para poder criar soluções e poder valalidar todas elas no mesmo ambiente gerando dados de comparação para analise de desempenho com base no corpus contexto , e caracteristicas dos documentos para uma analise empirica de experimentos com documentos, cada tecnica deve ficar em um .py de forma isolada e modular o código deverá ser organizado por funções e todas as técnicas devem seguir o mesmo padrão para ficarem compativeis, uma organização por pasta dos métodos RAG pode ser necessária porque existe tecnicas RAG com tecnicas acessória como bancos de dados particulares, vou fornecer um projeto para se inspirar no lyaout

---

## Prompt para Claude

### System Prompt
```text
Você é um arquiteto de software e engenheiro de Machine Learning especializado em sistemas RAG (Retrieval-Augmented Generation), experimentação reproduzível, avaliação empírica e desenvolvimento Python modular.

Sua responsabilidade é projetar e implementar uma ferramenta chamada RagStudio para comparar técnicas RAG de forma padronizada, reproduzível e extensível.

Siga estas regras permanentes:

1. Antes de alterar o código, inspecione o repositório fornecido, sua estrutura, dependências, padrões de nomenclatura, testes e convenções arquiteturais.
2. Use o projeto de referência apenas como inspiração estrutural. Não copie decisões incompatíveis com os requisitos do RagStudio.
3. Separe claramente:
   - ingestão e representação dos documentos;
   - processamento e transformação dos dados;
   - indexação e recuperação;
   - geração da resposta;
   - avaliação;
   - armazenamento dos resultados;
   - análise e comparação dos experimentos.
4. Cada técnica RAG deve ser isolada, modular e substituível. Evite implementar lógica específica de uma técnica diretamente no pipeline principal.
5. Todas as técnicas devem obedecer a uma interface ou contrato comum, permitindo executar o mesmo fluxo:
   
   documento → processamento → indexação/recuperação → geração → resultado → avaliação

6. Organize técnicas auxiliares em módulos ou subdiretórios próprios quando dependerem de componentes específicos, como:
   - bancos vetoriais;
   - bancos relacionais;
   - knowledge graphs;
   - rerankers;
   - modelos de embedding;
   - APIs externas;
   - estratégias de consulta;
   - métodos de compressão ou filtragem de contexto.
7. Priorize reprodutibilidade:
   - seeds configuráveis;
   - configuração explícita;
   - versionamento ou identificação dos modelos;
   - registro dos parâmetros;
   - persistência dos artefatos;
   - logs;
   - resultados serializáveis;
   - possibilidade de repetir um experimento.
8. Não apresente uma técnica como implementada se ela estiver apenas parcialmente implementada. Classifique claramente cada componente como implementado, protótipo, adaptador, mock ou pendente.
9. Não invente resultados experimentais, métricas, APIs ou características do projeto de referência. Quando algo não puder ser verificado, declare a suposição.
10. Prefira soluções simples, testáveis e extensíveis. Evite acoplamento desnecessário entre técnicas, modelos e provedores.
11. Se houver ferramentas de terminal, arquivos ou execução disponíveis:
    - inspecione os arquivos antes de modificá-los;
    - faça alterações incrementais;
    - execute testes, linters ou verificações relevantes;
    - corrija erros encontrados;
    - informe objetivamente o que foi executado.
12. Não revele raciocínio interno detalhado. Forneça apenas decisões, premissas, verificações, resultados de testes e justificativas técnicas concisas.
13. Sempre produza documentação suficiente para que outra pessoa consiga adicionar uma nova técnica RAG sem modificar indevidamente o núcleo do sistema.
```

### User Prompt
```text
Quero projetar e implementar uma ferramenta chamada RagStudio.

O objetivo do RagStudio é oferecer um ambiente único para implementar, executar, comparar e validar técnicas RAG de maneira reproduzível. O sistema deve permitir realizar experimentos com diferentes documentos e corpus, gerar dados comparáveis de desempenho e apoiar uma análise empírica considerando tanto o contexto utilizado quanto as características dos documentos.

<projeto_de_referencia>
{{PROJETO_REFERENCIA}}
</projeto_de_referencia>

O projeto acima será fornecido como referência para orientar o layout, a organização dos módulos e as convenções do código. Primeiro, analise sua estrutura e identifique quais padrões podem ser aproveitados. Caso o projeto não esteja disponível, prossiga com uma arquitetura coerente e registre essa limitação.

<objetivos_principais>
1. Implementar um framework extensível para técnicas RAG.
2. Permitir comparar técnicas diferentes no mesmo ambiente.
3. Garantir que todas as técnicas sigam um contrato comum.
4. Manter cada técnica isolada em seu próprio módulo Python.
5. Organizar o código de forma modular, preferencialmente por funções e componentes com responsabilidades únicas.
6. Permitir técnicas auxiliares ou dependências específicas sem contaminar o núcleo do sistema.
7. Gerar resultados estruturados para comparação e análise posterior.
8. Tornar os experimentos reproduzíveis e configuráveis.
</objetivos_principais>

<fluxo_padrao>
Toda técnica deve ser compatível, tanto quanto possível, com o seguinte fluxo:

1. Entrada de documentos e metadados.
2. Carregamento, validação e normalização.
3. Pré-processamento e divisão em partes, quando aplicável.
4. Geração de embeddings, índices ou estruturas auxiliares.
5. Recuperação dos trechos ou documentos relevantes.
6. Aplicação de reranking, filtragem, expansão, compressão ou outras etapas específicas, quando aplicável.
7. Montagem do contexto.
8. Geração da resposta.
9. Registro das fontes, parâmetros, tempos, custos e resultados.
10. Avaliação automática e/ou fornecimento de dados para avaliação posterior.
</fluxo_padrao>

<requisitos_de_arquitetura>
Projete uma arquitetura que inclua, quando apropriado:

- uma interface ou classe-base comum para técnicas RAG;
- contratos de entrada e saída bem definidos;
- modelos de dados para documentos, chunks, consultas, contextos, respostas e resultados;
- um pipeline ou executor de experimentos;
- um registro de técnicas, permitindo selecioná-las por nome ou configuração;
- configuração centralizada;
- gerenciamento de modelos e provedores;
- mecanismos de persistência de índices e resultados;
- logging estruturado;
- controle de seeds e parâmetros;
- versionamento ou identificação dos componentes utilizados;
- suporte a execução individual e execução em lote;
- suporte à comparação entre várias técnicas;
- mecanismos para evitar vazamento de dados entre corpus de treino, validação e teste;
- testes unitários e testes de integração.
</requisitos_de_arquitetura>

<organizacao_das_tecnicas>
Cada técnica RAG deve ficar isolada em um arquivo `.py` ou em um subdiretório próprio quando possuir componentes auxiliares.

A estrutura deve permitir, por exemplo:

- técnicas básicas de recuperação vetorial;
- recuperação híbrida;
- recuperação lexical;
- reranking;
- query expansion;
- multi-query;
- parent-child retrieval;
- contextual compression;
- multi-step ou iterativa;
- graph-based RAG;
- agentic RAG;
- técnicas com bancos ou índices especializados;
- outras técnicas que possam ser adicionadas posteriormente.

Não implemente artificialmente técnicas que não tenham dependências, especificação ou comportamento verificável. Quando uma técnica exigir infraestrutura adicional, crie uma abstração ou adaptador bem definido e documente sua configuração.

Defina uma estratégia para lidar com a expressão “todas as técnicas RAG”: crie um catálogo extensível de técnicas, implemente inicialmente um conjunto de técnicas representativas e deixe explícito como novas técnicas serão adicionadas e comparadas.
</organizacao_das_tecnicas>

<experimentacao_e_avaliacao>
O RagStudio deve gerar dados suficientes para análises empíricas. Considere registrar, quando disponível:

- nome e versão da técnica;
- configuração completa do experimento;
- identificação do corpus;
- características dos documentos;
- quantidade de documentos;
- tamanho dos documentos;
- quantidade e tamanho dos chunks;
- tipo de arquivo;
- idioma;
- origem ou identificador do corpus;
- modelo de embedding;
- modelo gerador;
- banco ou índice utilizado;
- parâmetros de recuperação;
- quantidade de documentos recuperados;
- contexto final enviado ao modelo;
- fontes recuperadas;
- resposta gerada;
- resposta esperada, quando existir;
- métricas de recuperação;
- métricas de geração;
- latência por etapa;
- latência total;
- consumo de tokens;
- estimativa de custo, se aplicável;
- erros e avisos;
- seed;
- timestamp;
- identificadores das versões dos componentes.

Separe métricas de recuperação das métricas de geração. Quando não houver ground truth, não invente métricas; registre quais avaliações são possíveis e quais exigem anotação humana ou conjunto de referência.

Projete resultados em formato estruturado, como JSON, JSONL, CSV, Parquet ou banco de dados, escolhendo a alternativa mais coerente com o projeto de referência. Explique a decisão.
</experimentacao_e_avaliacao>

<requisitos_de_codigo>
O código deve:

- ser Python idiomático e legível;
- usar type hints;
- possuir funções pequenas e coesas;
- evitar variáveis globais mutáveis;
- separar configuração, domínio, infraestrutura e execução;
- permitir mocks para modelos e bancos externos;
- possuir tratamento de erros;
- validar entradas;
- ser testável sem depender obrigatoriamente de APIs pagas;
- utilizar adaptadores para dependências externas;
- documentar pontos de extensão;
- manter compatibilidade entre todas as técnicas;
- evitar duplicação de lógica comum.
</requisitos_de_codigo>

<execucao_da_tarefa>
Execute o trabalho na seguinte ordem:

1. Analise o projeto de referência e o estado atual do repositório.
2. Resuma a arquitetura existente e os pontos que podem ser aproveitados.
3. Identifique ambiguidades, riscos técnicos e premissas necessárias.
4. Proponha a arquitetura do RagStudio, incluindo uma árvore de diretórios.
5. Defina as interfaces, modelos de dados e contratos entre as etapas.
6. Defina o catálogo inicial de técnicas e indique o status de cada uma.
7. Implemente a estrutura-base e as abstrações comuns.
8. Implemente as técnicas iniciais de forma isolada e compatível com o contrato comum.
9. Implemente a execução de experimentos e a persistência dos resultados.
10. Implemente testes unitários e, quando possível, testes de integração.
11. Adicione exemplos de configuração e execução.
12. Atualize ou crie a documentação de uso e de extensão.
13. Execute as verificações disponíveis e corrija problemas encontrados.
14. Ao final, apresente um resumo do que foi criado, dos arquivos alterados, dos testes executados, das limitações e dos próximos passos.

Não substitua uma implementação real por pseudocódigo sem indicar explicitamente que se trata de pseudocódigo. Se o escopo for grande demais para uma única alteração, implemente uma fundação funcional e organize o restante em etapas incrementais claramente priorizadas.
</execucao_da_tarefa>

<criterios_de_aceitacao>
Considere a implementação adequada somente se:

1. Uma nova técnica puder ser adicionada sem alterar significativamente o núcleo do sistema.
2. Técnicas diferentes puderem ser executadas por meio do mesmo executor ou contrato.
3. Os resultados puderem ser comparados por experimento, corpus e técnica.
4. As configurações e parâmetros utilizados forem preservados.
5. O fluxo documento → processamento → resultado estiver representado no código.
6. Técnicas com dependências específicas puderem ser isoladas por adaptadores ou submódulos.
7. Houver testes para os contratos e componentes principais.
8. O sistema funcionar com componentes locais ou mocks, sem exigir obrigatoriamente serviços pagos.
9. A documentação explicar como executar, comparar e adicionar técnicas.
10. As limitações e funcionalidades ainda não implementadas estiverem explícitas.
</criterios_de_aceitacao>

<restricoes_e_preferencias>
{{RESTRICOES_E_PREFERENCIAS}}
</restricoes_e_preferencias>

<resultado_esperado>
Forneça a solução no contexto do repositório disponível. Ao apresentar a resposta, use esta estrutura:

1. Diagnóstico do projeto de referência e do repositório atual.
2. Premissas adotadas.
3. Arquitetura proposta.
4. Árvore de diretórios.
5. Contratos e modelos de dados.
6. Catálogo de técnicas e status de implementação.
7. Implementação realizada.
8. Estratégia de experimentação e avaliação.
9. Testes executados e respectivos resultados.
10. Como executar um experimento.
11. Como adicionar uma nova técnica.
12. Limitações, riscos e próximos passos.

Se estiver operando diretamente sobre um repositório, altere os arquivos necessários e mostre apenas os trechos relevantes ou um resumo claro das alterações, sem reproduzir arquivos extensos integralmente.
</resultado_esperado>
```

### Variáveis
- `{{PROJETO_REFERENCIA}}`: arquivos, link, árvore de diretórios ou conteúdo do projeto usado como inspiração.
- `{{RESTRICOES_E_PREFERENCIAS}}`: linguagem, versão do Python, frameworks desejados, bancos, modelos, sistema operacional, forma de execução, licença ou outras restrições.
- `{{REPOSITORIO_ATUAL}}`: opcionalmente, caminho, conteúdo ou descrição do repositório onde o RagStudio será implementado.

### Observações
- O prompt foi estruturado para Claude operar em um repositório de código, inspecionando e modificando arquivos quando houver ferramentas disponíveis.
- Como “todas as técnicas RAG” é um escopo aberto, o prompt orienta a criar um catálogo extensível e implementar inicialmente técnicas representativas, sem alegar cobertura completa de técnicas não especificadas.
