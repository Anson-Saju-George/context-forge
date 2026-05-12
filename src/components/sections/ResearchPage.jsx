function ResearchPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {['BM25', 'Document balancing', 'Evidence extraction'].map((name) => (
        <div key={name} className="rounded-md border border-zinc-800 bg-zinc-900/60 p-5">
          <h3 className="font-semibold text-white">{name}</h3>
          <p className="mt-2 text-sm leading-6 text-zinc-400">
            Tracked as part of the current local retrieval baseline.
          </p>
        </div>
      ))}
    </div>
  )
}

export default ResearchPage
