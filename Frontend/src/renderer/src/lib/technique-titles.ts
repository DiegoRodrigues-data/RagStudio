import { createContext } from 'react'

/** Technique identifier -> display name ("corrective" -> "Corrective RAG"), loaded once from the registry. */
export const TechniqueTitlesContext = createContext<Record<string, string>>({})
