import type { PageDict } from '@/components/shared/use-page-t'

const pt = {
  'pick.title': 'Runbooks',
  'pick.empty': 'Nenhum runbook. Crie e execute um em Experimentos.',
  'pick.runs': '{done}/{total} runs',
  'pick.hint': 'Selecione um ou mais runbooks com runs concluídos.',
  'tabs.axis': 'Por eixo de configuração',
  'tabs.characteristics': 'Características dos documentos',
  'axis.by': 'Agrupar por',
  'axis.metric': 'Métrica',
  'axis.runs': 'runs',
  'axis.chart': '{metric} por {axis}',
  'axis.table': 'Todas as métricas',
  'axis.group': 'Grupo',
  'axis.stdev': 'desvio entre runs',
  'axis.lower': 'menor é melhor',
  'axis.higher': 'maior é melhor',
  'axis.sameIndex':
    'Compare técnicas com a mesma indexação: mudar chunking ou embedding muda o índice, e a diferença deixa de ser só da técnica.',
  'char.summary': '{rows} respostas · {docs} documentos',
  'char.target': 'Documento-alvo: do trecho gold em {gold}, do primeiro recuperado em {top}.',
  'char.correlations': 'Correlação de Spearman entre característica e métrica',
  'char.technique': 'Técnica',
  'char.metric': 'Métrica',
  'char.feature': 'Característica',
  'char.spearman': 'ρ',
  'char.n': 'n',
  'char.docs': 'docs',
  'char.bins': 'Médias por tercil de tamanho do documento',
  'char.bin': 'Faixa',
  'char.byLanguage': 'Por idioma',
  'char.byFormat': 'Por formato',
  'char.byCorpus': 'Por corpus',
  'char.caution': 'Estatística descritiva. Com poucos documentos não leia como efeito.',
  'char.none': 'Sem variação suficiente para calcular.',
  'char.filter': 'Filtrar técnica ou métrica...',
  errorTitle: 'Falha ao consultar o backend'
} as const

export type AnKey = keyof typeof pt

const en: Record<AnKey, string> = {
  'pick.title': 'Runbooks',
  'pick.empty': 'No runbook. Create and run one in Experiments.',
  'pick.runs': '{done}/{total} runs',
  'pick.hint': 'Select one or more runbooks with completed runs.',
  'tabs.axis': 'By configuration axis',
  'tabs.characteristics': 'Document characteristics',
  'axis.by': 'Group by',
  'axis.metric': 'Metric',
  'axis.runs': 'runs',
  'axis.chart': '{metric} by {axis}',
  'axis.table': 'All metrics',
  'axis.group': 'Group',
  'axis.stdev': 'spread across runs',
  'axis.lower': 'lower is better',
  'axis.higher': 'higher is better',
  'axis.sameIndex':
    'Compare techniques on the same indexing: changing chunking or embedding changes the index, and the difference stops being about the technique alone.',
  'char.summary': '{rows} answers · {docs} documents',
  'char.target':
    'Target document: from the gold passage in {gold}, from the top retrieved chunk in {top}.',
  'char.correlations': 'Spearman correlation between characteristic and metric',
  'char.technique': 'Technique',
  'char.metric': 'Metric',
  'char.feature': 'Characteristic',
  'char.spearman': 'ρ',
  'char.n': 'n',
  'char.docs': 'docs',
  'char.bins': 'Means by tercile of document size',
  'char.bin': 'Bin',
  'char.byLanguage': 'By language',
  'char.byFormat': 'By format',
  'char.byCorpus': 'By corpus',
  'char.caution': 'Descriptive statistics. With few documents do not read them as effects.',
  'char.none': 'Not enough variation to compute.',
  'char.filter': 'Filter technique or metric...',
  errorTitle: 'Backend request failed'
}

export const dict: PageDict<AnKey> = { 'pt-BR': pt, en }
