# Técnicas de RAG Implementadas no Projeto

Este documento lista as técnicas de Retrieval-Augmented Generation (RAG) que estão implementadas
no projeto, com links para os artigos acadêmicos que fundamentam cada técnica.

---

## 1. Naive RAG (RAG clássico)

**Descrição:** Recupera documentos relevantes e gera uma resposta condicionada a esses documentos.

**Artigo base:**
- *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* — Patrick Lewis et al. (NeurIPS 2020)  
  https://arxiv.org/abs/2005.11401

---

## 2. HyDE (Hypothetical Document Embeddings)

**Descrição:** Gera um documento hipotético que representa uma resposta ideal e usa seus embeddings para recuperação.

**Artigo base:**
- *Precise Zero-Shot Dense Retrieval without Relevance Labels* — L. Gao, X. Ma, J. Lin, J. Callan (ACL 2023)  
  https://aclanthology.org/2023.acl-long.99/

---

## 3. MMR (Maximal Marginal Relevance)

**Descrição:** Algoritmo de reranking que combina relevância com diversidade para evitar redundância na seleção de documentos.

**Artigo base (origem do MMR em IR):**
- *The Use of MMR Diversity-Based Reranking for Reordering Documents and Producing Summaries* — Carbonell & Goldstein (SIGIR 1998)  
  https://www.researchgate.net/publication/2269571_The_Use_of_MMR_Diversity-Based_Reranking_for_Reordering_Documents_and_Producing_Summaries

---

## 4. Iterative / Self-Refining RAG

**Descrição:** Processo de recuperação → geração → avaliação iterativa para refinar respostas.

**Artigo conceitual relacionado:**
- *Active Retrieval Augmented Generation (FLARE)* (descrição de método iterativo)  
  https://www.researchgate.net/publication/370688555_Active_Retrieval_Augmented_Generation

---

## 5. RAG-EVO (Evolutive Introspective RAG)

**Descrição:** Extensão iterativa com escore de confiança e fallback para refinamento progressivo de respostas.

**Artigo base (capítulo de livro):**
- RAG-EVO — capítulo em *Advances in Information Retrieval* (Springer)  
  https://link.springer.com/chapter/10.1007/978-3-032-05176-9_27

---

## 6. Multi-Query / Query Expansion RAG

**Descrição:** Gera múltiplas reformulações da query para ampliar a cobertura de recuperação.

**Artigo de suporte (survey que cobre query expansion):**
- *A Comprehensive Survey of Retrieval-Augmented Generation (RAG): Evolution, Current Landscape and Future Directions* — Gupta et al. (2024)  
  https://arxiv.org/abs/2410.12837

---

## 7. Survey Geral sobre RAG

**Descrição:** Artigo de revisão que categoriza técnicas e variações de RAG.

**Artigo:**
- *Retrieval-Augmented Generation for AI-Generated Content: A Survey* — Zhao et al. (2024)  
  https://arxiv.org/abs/2402.19473

---

## Referências Acadêmicas

| Técnica Implementada | Artigo Acadêmico | Link |
|----------------------|------------------|------|
| Naive RAG | *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* | https://arxiv.org/abs/2005.11401 |
| HyDE RAG | *Precise Zero-Shot Dense Retrieval without Relevance Labels* | https://aclanthology.org/2023.acl-long.99/ |
| MMR Diversity | *The Use of MMR Diversity-Based Reranking…* (SIGIR 1998) | https://www.researchgate.net/publication/2269571_The_Use_of_MMR_Diversity-Based_Reranking_for_Reordering_Documents_and_Producing_Summaries |
| Iterative RAG | Active RAG (FLARE) | https://www.researchgate.net/publication/370688555_Active_Retrieval_Augmented_Generation |
| RAG-EVO | Capítulo em *Advances in Information Retrieval* | https://link.springer.com/chapter/10.1007/978-3-032-05176-9_27 |
| Multi-Query RAG | *A Comprehensive Survey of RAG* | https://arxiv.org/abs/2410.12837 |
| Survey geral de RAG | *Retrieval-Augmented Generation for AI-Generated Content* | https://arxiv.org/abs/2402.19473 |

---

## Observações

- Algumas técnicas (como MMR) vêm de literatura clássica de IR e foram adaptadas para RAG.
- Nem todas as variações possuem um “paper único nomeado”; algumas são descritas em surveys ou trabalhos de aplicação.
- Os links incluídos são **links para as versões oficiais dos artigos** sempre que disponíveis publicamente.

---