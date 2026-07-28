import MarkdownMessage from './MarkdownMessage'

function ChatBubble({ role, children, meta, reasoning, citations, retrieval }) {
  const isAssistant = role === 'assistant'
  const isSystem = role === 'system'
  const visibleCitations = citations?.slice(0, 5) || []
  const hiddenCitations = citations?.slice(5) || []

  return (
    <div
      className={`relative max-w-3xl rounded-md border px-4 py-3 ${
        isAssistant
          ? 'ml-auto border-cyan-900/70 bg-cyan-950/40'
          : isSystem
            ? 'border-zinc-800 bg-zinc-950'
            : 'border-zinc-800 bg-zinc-900'
      }`}
    >
      <div className="mb-1 flex items-start justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
          {role}
        </div>
        {isAssistant && meta && (
          <div className="shrink-0 rounded bg-zinc-950/80 px-2 py-1 text-xs text-zinc-400">
            {meta}
          </div>
        )}
      </div>
      {reasoning && (
        <details className="mb-3 rounded-md border border-cyan-900/60 bg-cyan-950/30 px-3 py-2">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">
            Reasoning
          </summary>
          <div className="mt-3">
            <MarkdownMessage content={reasoning} />
          </div>
        </details>
      )}
      <MarkdownMessage content={children} />
      {citations?.length > 0 && (
        <div className="mt-4 rounded-md border border-zinc-800 bg-zinc-950/70 p-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
              Sources
            </div>
            {retrieval && (
              <div className="text-xs text-zinc-500">
                {retrieval.mode}
                {retrieval.intent ? `:${retrieval.intent}` : ''} / candidates{' '}
                {retrieval.candidate_count || retrieval.top_k || 0} /{' '}
                {retrieval.selected_count} selected / {retrieval.total_chunks} chunks /{' '}
                {retrieval.latency_ms}ms
              </div>
            )}
          </div>
          <div className="grid gap-2">
            {visibleCitations.map((citation, index) => (
              <CitationCard key={citation.chunk_id} citation={citation} index={index} />
            ))}
            {hiddenCitations.length > 0 && (
              <details className="rounded-md border border-zinc-800 bg-zinc-900/70 px-3 py-2">
                <summary className="cursor-pointer text-sm text-cyan-200">
                  Show {hiddenCitations.length} more sources
                </summary>
                <div className="mt-2 grid gap-2">
                  {hiddenCitations.map((citation, index) => (
                    <CitationCard
                      key={citation.chunk_id}
                      citation={citation}
                      index={index + visibleCitations.length}
                    />
                  ))}
                </div>
              </details>
            )}
          </div>
        </div>
      )}
      {!isAssistant && meta && <div className="mt-2 text-xs text-zinc-500">{meta}</div>}
    </div>
  )
}

function CitationCard({ citation, index }) {
  return (
    <details className="rounded-md border border-zinc-800 bg-zinc-900/70 px-3 py-2">
      <summary className="cursor-pointer text-sm text-zinc-200">
        [{index + 1}] {citation.source}{' '}
        <span className="text-xs text-cyan-300">score {citation.score}</span>
      </summary>
      {(citation.page || citation.section) && (
        <div className="mt-2 text-xs text-zinc-500">
          {citation.page ? `page ${citation.page}` : ''}
          {citation.page && citation.section ? ' / ' : ''}
          {citation.section || ''}
        </div>
      )}
      {(citation.rerank_score || citation.rerank_reasons?.length > 0) && (
        <div className="mt-2 text-xs text-zinc-500">
          {citation.rerank_score ? `rerank ${citation.rerank_score}` : ''}
          {citation.rerank_score && citation.rerank_reasons?.length > 0 ? ' / ' : ''}
          {citation.rerank_reasons?.join(' | ')}
        </div>
      )}
      <p className="mt-2 text-xs leading-5 text-zinc-400">{citation.text}</p>
    </details>
  )
}

export default ChatBubble
