import type { PageDict } from '@/components/shared/use-page-t'

const pt = {
  'filter.placeholder': 'Filtrar por nome, família ou descrição...',
  'filter.status': 'Status',
  'col.name': 'Técnica',
  'col.family': 'Família',
  'col.stage': 'Etapa do pipeline',
  'col.axes': 'Eixos do runbook',
  'axes.all': 'usa todos',
  'axes.ignores': 'ignora: {axes}',
  'axes.needs': 'exige índice {index}',
  'col.status': 'Status',
  'col.version': 'Versão',
  'col.description': 'O que faz',
  'col.params': 'Parâmetros (padrão)',
  'col.reference': 'Referência',
  'status.implemented': 'implementada',
  'status.prototype': 'protótipo',
  'status.adapter': 'adaptador',
  'status.mock': 'mock',
  'status.pending': 'pendente',
  'legend.implemented':
    'Código completo no contrato comum, com testes passando no provider simulado.',
  'legend.prototype':
    'Escopo reduzido em relação ao artigo; a própria técnica avisa em cada resposta.',
  'legend.note':
    'Nenhum status aqui afirma validação com um modelo real: isso depende dos seus experimentos.',
  summary: '{n} técnicas · {impl} implementadas · {proto} protótipos',
  empty: 'Nenhuma técnica corresponde ao filtro',
  noParams: 'sem parâmetros',
  open: 'abrir referência',
  errorTitle: 'Falha ao carregar o catálogo'
} as const

export type TechKey = keyof typeof pt

const en: Record<TechKey, string> = {
  'filter.placeholder': 'Filter by name, family or description...',
  'filter.status': 'Status',
  'col.name': 'Technique',
  'col.family': 'Family',
  'col.stage': 'Pipeline stage',
  'col.axes': 'Runbook axes',
  'axes.all': 'uses all',
  'axes.ignores': 'ignores: {axes}',
  'axes.needs': 'needs {index} index',
  'col.status': 'Status',
  'col.version': 'Version',
  'col.description': 'What it does',
  'col.params': 'Parameters (default)',
  'col.reference': 'Reference',
  'status.implemented': 'implemented',
  'status.prototype': 'prototype',
  'status.adapter': 'adapter',
  'status.mock': 'mock',
  'status.pending': 'pending',
  'legend.implemented':
    'Complete code under the common contract, with tests passing on the mock provider.',
  'legend.prototype':
    'Reduced scope compared with the paper; the technique itself warns in every answer.',
  'legend.note':
    'No status here claims validation with a real model: that depends on your experiments.',
  summary: '{n} techniques · {impl} implemented · {proto} prototypes',
  empty: 'No technique matches the filter',
  noParams: 'no parameters',
  open: 'open reference',
  errorTitle: 'Failed to load the catalog'
}

export const dict: PageDict<TechKey> = { 'pt-BR': pt, en }
