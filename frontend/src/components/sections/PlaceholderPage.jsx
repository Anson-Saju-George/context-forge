function PlaceholderPage({ title }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-6">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
        This page is reserved for the next implementation pass after backend and API wiring are
        confirmed.
      </p>
    </div>
  )
}

export default PlaceholderPage
