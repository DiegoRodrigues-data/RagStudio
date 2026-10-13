import type { TranslationKey } from './i18n'

/** Pipeline stages in flow order; techniques are grouped by the stage where they act. */
export const STAGES = ['indexing', 'query', 'retrieval', 'post_retrieval', 'orchestration'] as const
export type Stage = (typeof STAGES)[number]

export function stageKey(stage: string): TranslationKey {
  return `stage.${(STAGES as readonly string[]).includes(stage) ? stage : 'retrieval'}` as TranslationKey
}

/** Label key of a run setting a technique may ignore. */
export function axisKey(axis: string): TranslationKey {
  return `axis.${axis}` as TranslationKey
}
