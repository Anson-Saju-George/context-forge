export const fallbackRagVersions = [
  {
    id: 'v0',
    label: 'V0 Similarity Toy',
    shortLabel: 'V0',
    theme: 'theme-v0',
    stage: 'Toy baseline',
    headline: 'Cosine-style similarity search',
    description: 'A simple overlap baseline that shows why most beginner RAG demos collapse on broad or extraction-heavy questions.',
    chips: ['single-stage', 'similarity', 'no routing'],
    process: [
      ['Query', 'raw user question'],
      ['Retrieve', 'token cosine similarity'],
      ['Rank', 'single-stage score sort'],
      ['Pack', 'top-k chunks only'],
      ['Answer', 'citation-backed generation'],
    ],
  },
  {
    id: 'v1',
    label: 'V1 Sparse Foundation',
    shortLabel: 'V1',
    theme: 'theme-v1',
    stage: 'Sparse retrieval',
    headline: 'BM25 and hierarchical context',
    description: 'The first serious retrieval layer: stronger exact-term recall, better chunk locality, and basic evidence selection.',
    chips: ['BM25', 'hierarchical', 'citations'],
    process: [
      ['Query', 'intent-light query terms'],
      ['Retrieve', 'BM25 sparse retrieval'],
      ['Rank', 'technical specificity rerank'],
      ['Pack', 'hierarchical parent context'],
      ['Answer', 'grounded citations'],
    ],
  },
  {
    id: 'v2',
    label: 'V2 Routed Retrieval',
    shortLabel: 'V2',
    theme: 'theme-v2',
    stage: 'Task awareness',
    headline: 'Intent-routed retrieval behavior',
    description: 'Extraction and synthesis stop sharing the same behavior, giving technical queries sharper evidence.',
    chips: ['intent routing', 'extraction', 'rerank'],
    process: [
      ['Query', 'extraction vs general routing'],
      ['Retrieve', 'BM25 plus technical density'],
      ['Rank', 'specificity-biased rerank'],
      ['Pack', 'compressed evidence chunks'],
      ['Answer', 'mode-aware response'],
    ],
  },
  {
    id: 'v3',
    label: 'V3 Benchmark Baseline',
    shortLabel: 'V3',
    theme: 'theme-v3',
    stage: 'Benchmark system',
    headline: 'Document-balanced synthesis',
    description: 'A stable benchmark baseline for cross-document synthesis, operational comparison, and algorithm extraction.',
    chips: ['benchmark checks', 'document coverage', 'reports'],
    process: [
      ['Query', 'synthesis / extraction classifier'],
      ['Retrieve', 'document-balanced BM25'],
      ['Rank', 'mechanism-density scoring'],
      ['Pack', 'per-document evidence matrix'],
      ['Answer', 'deterministic benchmark answer'],
    ],
  },
  {
    id: 'v3.1',
    label: 'V3.1 Clean Baseline',
    shortLabel: 'V3.1',
    theme: 'theme-v31',
    stage: 'Final clean baseline',
    headline: 'Evidence-only extraction',
    description: 'The final research baseline: cleaner mechanism recall, document-balanced context, and stricter quality gates.',
    chips: ['evidence-first', 'term diversity', 'production polish'],
    process: [
      ['Query', 'clean intent routing'],
      ['Retrieve', 'evidence-only BM25 hierarchy'],
      ['Rank', 'MMR plus term diversity'],
      ['Pack', 'document-balanced context'],
      ['Answer', 'strict cited extraction / synthesis'],
    ],
  },
]

export function mergeRagVersions(apiVersions) {
  const byId = new Map(fallbackRagVersions.map((version) => [version.id, version]))
  ;(apiVersions || []).forEach((version) => {
    const local = byId.get(version.id)
    if (local) {
      byId.set(version.id, { ...local, ...version })
    }
  })
  return fallbackRagVersions.map((version) => byId.get(version.id))
}

export function getRagVersion(versions, id) {
  return versions.find((version) => version.id === id) || versions[versions.length - 1]
}
