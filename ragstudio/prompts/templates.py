"""Versioned prompt templates, by language and task.

Origin: `ragkit/prompts.py` (answer, multi_queries, hypo_doc, decompose, extract_essential, gap_query) plus the
control prompts required by reranking, confidence, step-back, corrective, contextual, RAPTOR, the knowledge-graph
techniques (GraphRAG, LightRAG, HippoRAG), Self-RAG, RankRAG, Adaptive RAG, Multi-Hop RAG, RECOMP, the agent
and the LLM judge. Changing a template changes its hash, which is stored with every run.
"""
from __future__ import annotations

PROMPT_SET_VERSION = "2026.10-2"

SYSTEM = {
    "pt": {
        "answer": "Você responde perguntas usando SOMENTE o contexto fornecido. Cite os trechos usados com [n]. "
                  "Se o contexto não contiver a resposta, diga que não encontrou a informação.",
        "answer_direct": "Você responde perguntas de forma direta e curta com o seu próprio conhecimento. "
                         "Se não souber, diga que não sabe.",
        "_default": "Você é um componente de um pipeline de recuperação de informação. Siga o formato pedido "
                    "exatamente, sem comentários adicionais.",
    },
    "en": {
        "answer": "You answer questions using ONLY the provided context. Cite the passages you used as [n]. "
                  "If the context does not contain the answer, say the information was not found.",
        "answer_direct": "You answer questions directly and briefly from your own knowledge. If you do not know, "
                         "say so.",
        "_default": "You are a component of an information retrieval pipeline. Follow the requested format "
                    "exactly, with no additional commentary.",
    },
}

TEMPLATES = {
    "pt": {
        "answer": "Contexto:\n{context}\n\nPergunta: {query}",
        "multi_queries": "Gere {n} reformulações diferentes da pergunta abaixo para busca em uma base de documentos. "
                         "Uma por linha, sem numeração.\n\nPergunta: {query}",
        "hypo_doc": "Escreva um parágrafo curto e factual que responderia à pergunta abaixo, como se fosse um trecho "
                    "de um documento. Não diga que é hipotético.\n\nPergunta: {query}",
        "decompose": "Decomponha a pergunta abaixo em até {n} subperguntas mais simples e independentes. "
                     "Uma por linha, sem numeração.\n\nPergunta: {query}",
        "extract_essential": "Extraia do texto apenas as frases que ajudam a responder à pergunta, copiando-as "
                             "literalmente. Se nada for relevante, responda com uma linha vazia.\n\n"
                             "Pergunta: {query}\n\nTexto:\n{text}",
        "gap_query": "Pergunta original: {query}\n\nResposta parcial:\n{answer}\n\nEscreva UMA consulta de busca "
                     "para encontrar a informação que ainda falta. Apenas a consulta.",
        "rerank": "Ordene os trechos do mais ao menos relevante para a pergunta. Responda só com os números "
                  "separados por vírgula.\n\nPergunta: {query}\n\nTrechos:\n{passages}",
        "confidence": "Avalie de 0 a 1 o quanto a resposta está sustentada pelo contexto e responde à pergunta. "
                      "Responda apenas com o número.\n\nPergunta: {query}\n\nResposta: {answer}\n\n"
                      "Contexto:\n{context}",
        "step_back": "Reescreva a pergunta abaixo como uma pergunta mais geral, sobre o conceito ou princípio por "
                     "trás dela. Apenas a pergunta.\n\nPergunta: {query}",
        "relevance": "O trecho abaixo ajuda a responder à pergunta? Responda apenas 'sim' ou 'não'.\n\n"
                     "Pergunta: {query}\n\nTrecho:\n{text}",
        "context_prefix": "Documento:\n{document}\n\nTrecho:\n{chunk}\n\nEscreva uma frase curta que situe este "
                          "trecho dentro do documento, para melhorar a busca. Apenas a frase.",
        "summarize": "Resuma o texto abaixo em um parágrafo, preservando nomes, números e datas.\n\n{text}",
        "entities": "Liste as entidades nomeadas (pessoas, organizações, lugares, leis, conceitos-chave) do texto. "
                    "Uma por linha, sem comentários.\n\n{text}",
        "kg_extract": "Extraia do texto as entidades e as relações entre elas. Uma linha por item, exatamente "
                      "nestes formatos:\nENTITY | nome | tipo | descrição curta\n"
                      "REL | entidade de origem | entidade de destino | relação em poucas palavras | descrição curta"
                      "\nUse tipos como pessoa, organização, lugar, lei, data, valor, conceito. Use os mesmos nomes "
                      "nas linhas ENTITY e REL. No máximo {max_entities} entidades. Sem comentários.\n\n"
                      "Texto:\n{text}",
        "community_report": "As entidades e relações abaixo formam um grupo relacionado em uma base de documentos. "
                            "Escreva um relatório: na primeira linha um título curto, depois um parágrafo que resuma "
                            "quem são as entidades, como se relacionam e os fatos principais, preservando nomes, "
                            "números e datas.\n\nEntidades:\n{entities}\n\nRelações:\n{relations}",
        "community_points": "Use o relatório abaixo para ajudar a responder à pergunta. Na primeira linha escreva "
                            "'SCORE: n', com n de 0 a 100 indicando o quanto o relatório ajuda. Depois liste, um por "
                            "linha, os pontos do relatório que respondem à pergunta. Se nada ajudar, escreva apenas "
                            "'SCORE: 0'.\n\nPergunta: {query}\n\nRelatório:\n{report}",
        "lightrag_keywords": "Extraia palavras-chave da pergunta para busca em um grafo de conhecimento. Responda "
                             "com exatamente duas linhas:\nHIGH: temas e conceitos gerais, separados por vírgula\n"
                             "LOW: entidades e termos específicos, separados por vírgula\n\nPergunta: {query}",
        "needs_retrieval": "Para responder à pergunta abaixo com precisão é necessário consultar documentos? "
                           "Responda apenas 'sim' ou 'não'.\n\nPergunta: {query}",
        "answer_direct": "Pergunta: {query}",
        "support": "Avalie a resposta em relação ao trecho. Responda com exatamente duas linhas:\n"
                   "SUPPORT: full, partial ou none (o quanto o trecho sustenta as afirmações da resposta)\n"
                   "USEFUL: de 1 a 5 (o quanto a resposta é útil para a pergunta)\n\n"
                   "Pergunta: {query}\n\nTrecho:\n{passage}\n\nResposta: {answer}",
        "rank_passages": "Dê a cada trecho uma nota de 0 a 10 pela utilidade para responder à pergunta. "
                         "Uma linha por trecho, no formato 'número: nota'. Sem comentários.\n\n"
                         "Pergunta: {query}\n\nTrechos:\n{passages}",
        "complexity": "Classifique a pergunta pelo esforço necessário para respondê-la:\n"
                      "A: pode ser respondida sem consultar documentos\n"
                      "B: exige uma única busca em documentos\n"
                      "C: exige várias buscas encadeadas ou a combinação de fatos de trechos diferentes\n"
                      "Responda apenas com a letra.\n\nPergunta: {query}",
        "next_hop": "Você responde a uma pergunta em etapas. Etapa {hop} de {max_hops}.\n\n"
                    "Pergunta: {query}\n\nFatos já encontrados:\n{facts}\n\nEscreva a próxima subpergunta, "
                    "simples e autocontida, que falta responder. Se os fatos já bastam, responda apenas DONE.",
        "hop_answer": "Responda à pergunta em uma frase, usando somente o contexto. Se o contexto não contiver a "
                      "resposta, responda 'não encontrado'.\n\nContexto:\n{context}\n\nPergunta: {query}",
        "recomp_summary": "Resuma os trechos abaixo em um parágrafo que contenha apenas o que ajuda a responder à "
                          "pergunta, preservando nomes, números e datas. Se nenhum trecho ajudar, responda apenas "
                          "NONE.\n\nPergunta: {query}\n\nTrechos:\n{passages}",
        "agent_plan": "Escreva um plano curto, com no máximo {n} passos, para encontrar em uma base de documentos a "
                      "informação necessária para responder à pergunta. Um passo por linha, sem numeração.\n\n"
                      "Pergunta: {query}",
        "agent_step": "Você pesquisa em uma base de documentos para responder à pergunta. Passo {step} de "
                      "{max_steps}.\n\nPergunta: {query}\n\nPlano:\n{plan}\n\nAnotações até agora:\n{notes}"
                      "\n\nEscolha a próxima ferramenta. Chame finish quando as anotações forem suficientes.",
        "agent_step_text": "Você pesquisa em uma base de documentos para responder à pergunta. Passo {step} de "
                           "{max_steps}.\n\nPergunta: {query}\n\nPlano:\n{plan}\n\nAnotações até agora:\n"
                           "{notes}\n\nFerramentas:\n{tools}\n\nResponda com uma única linha JSON: "
                           '{{"tool": "<nome>", "arguments": {{...}}}}',
        "judge_accuracy": "Pergunta: {query}\n\nResposta esperada: {expected}\n\nResposta avaliada: {answer}\n\n"
                          "De 0 a 1, o quanto a resposta avaliada está correta em relação à esperada? "
                          "Responda apenas com o número.",
        "judge_faithfulness": "Pergunta: {query}\n\nContexto:\n{context}\n\nResposta: {answer}\n\nDe 0 a 1, que "
                              "fração das afirmações da resposta é sustentada pelo contexto? "
                              "Responda apenas com o número.",
    },
    "en": {
        "answer": "Context:\n{context}\n\nQuestion: {query}",
        "multi_queries": "Write {n} different reformulations of the question below for searching a document base. "
                         "One per line, no numbering.\n\nQuestion: {query}",
        "hypo_doc": "Write a short factual paragraph that would answer the question below, as if it were a passage "
                    "from a document. Do not say it is hypothetical.\n\nQuestion: {query}",
        "decompose": "Decompose the question below into at most {n} simpler, independent sub-questions. "
                     "One per line, no numbering.\n\nQuestion: {query}",
        "extract_essential": "Extract from the text only the sentences that help answer the question, copied "
                             "verbatim. If nothing is relevant, answer with an empty line.\n\n"
                             "Question: {query}\n\nText:\n{text}",
        "gap_query": "Original question: {query}\n\nPartial answer:\n{answer}\n\nWrite ONE search query to find the "
                     "information still missing. Only the query.",
        "rerank": "Order the passages from most to least relevant to the question. Answer only with the numbers "
                  "separated by commas.\n\nQuestion: {query}\n\nPassages:\n{passages}",
        "confidence": "Rate from 0 to 1 how well the answer is supported by the context and answers the question. "
                      "Answer only with the number.\n\nQuestion: {query}\n\nAnswer: {answer}\n\nContext:\n{context}",
        "step_back": "Rewrite the question below as a more general question about the concept or principle behind "
                     "it. Only the question.\n\nQuestion: {query}",
        "relevance": "Does the passage below help answer the question? Answer only 'yes' or 'no'.\n\n"
                     "Question: {query}\n\nPassage:\n{text}",
        "context_prefix": "Document:\n{document}\n\nPassage:\n{chunk}\n\nWrite one short sentence situating this "
                          "passage within the document, to improve search. Only the sentence.",
        "summarize": "Summarize the text below in one paragraph, keeping names, numbers and dates.\n\n{text}",
        "entities": "List the named entities (people, organizations, places, laws, key concepts) in the text. "
                    "One per line, no commentary.\n\n{text}",
        "kg_extract": "Extract the entities in the text and the relations between them. One line per item, exactly "
                      "in these formats:\nENTITY | name | type | short description\n"
                      "REL | source entity | target entity | relation in a few words | short description\n"
                      "Use types such as person, organization, place, law, date, amount, concept. Use the same names "
                      "in ENTITY and REL lines. At most {max_entities} entities. No commentary.\n\nText:\n{text}",
        "community_report": "The entities and relations below form a related group in a document base. Write a "
                            "report: a short title on the first line, then one paragraph summarizing who the "
                            "entities are, how they relate and the main facts, keeping names, numbers and dates."
                            "\n\nEntities:\n{entities}\n\nRelations:\n{relations}",
        "community_points": "Use the report below to help answer the question. On the first line write 'SCORE: n', "
                            "with n from 0 to 100 for how much the report helps. Then list, one per line, the "
                            "points of the report that answer the question. If nothing helps, write only "
                            "'SCORE: 0'.\n\nQuestion: {query}\n\nReport:\n{report}",
        "lightrag_keywords": "Extract keywords from the question for searching a knowledge graph. Answer with "
                             "exactly two lines:\nHIGH: broad themes and concepts, comma separated\n"
                             "LOW: specific entities and terms, comma separated\n\nQuestion: {query}",
        "needs_retrieval": "Does answering the question below accurately require consulting documents? Answer only "
                           "'yes' or 'no'.\n\nQuestion: {query}",
        "answer_direct": "Question: {query}",
        "support": "Assess the answer against the passage. Answer with exactly two lines:\n"
                   "SUPPORT: full, partial or none (how much the passage supports the claims of the answer)\n"
                   "USEFUL: 1 to 5 (how useful the answer is for the question)\n\n"
                   "Question: {query}\n\nPassage:\n{passage}\n\nAnswer: {answer}",
        "rank_passages": "Give each passage a score from 0 to 10 for how useful it is to answer the question. One "
                         "line per passage, in the format 'number: score'. No commentary.\n\n"
                         "Question: {query}\n\nPassages:\n{passages}",
        "complexity": "Classify the question by the effort needed to answer it:\n"
                      "A: can be answered without consulting documents\n"
                      "B: needs a single search in documents\n"
                      "C: needs several chained searches or combining facts from different passages\n"
                      "Answer only with the letter.\n\nQuestion: {query}",
        "next_hop": "You answer a question in steps. Step {hop} of {max_hops}.\n\n"
                    "Question: {query}\n\nFacts found so far:\n{facts}\n\nWrite the next simple, self-contained "
                    "sub-question still to be answered. If the facts are enough, answer only DONE.",
        "hop_answer": "Answer the question in one sentence, using only the context. If the context does not contain "
                      "the answer, reply 'not found'.\n\nContext:\n{context}\n\nQuestion: {query}",
        "recomp_summary": "Summarize the passages below in one paragraph containing only what helps answer the "
                          "question, keeping names, numbers and dates. If no passage helps, answer only NONE."
                          "\n\nQuestion: {query}\n\nPassages:\n{passages}",
        "agent_plan": "Write a short plan, with at most {n} steps, to find in a document base the information "
                      "needed to answer the question. One step per line, no numbering.\n\nQuestion: {query}",
        "agent_step": "You search a document base to answer the question. Step {step} of {max_steps}.\n\n"
                      "Question: {query}\n\nPlan:\n{plan}\n\nNotes so far:\n{notes}\n\nChoose the next tool. "
                      "Call finish when the notes are sufficient.",
        "agent_step_text": "You search a document base to answer the question. Step {step} of {max_steps}.\n\n"
                           "Question: {query}\n\nPlan:\n{plan}\n\nNotes so far:\n{notes}\n\nTools:\n{tools}"
                           "\n\nAnswer with a single JSON line: "
                           '{{"tool": "<name>", "arguments": {{...}}}}',
        "judge_accuracy": "Question: {query}\n\nExpected answer: {expected}\n\nEvaluated answer: {answer}\n\n"
                          "From 0 to 1, how correct is the evaluated answer with respect to the expected one? "
                          "Answer only with the number.",
        "judge_faithfulness": "Question: {query}\n\nContext:\n{context}\n\nAnswer: {answer}\n\nFrom 0 to 1, what "
                              "fraction of the claims in the answer is supported by the context? "
                              "Answer only with the number.",
    },
}
