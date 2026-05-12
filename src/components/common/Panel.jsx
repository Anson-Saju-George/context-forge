function Panel({ title, children }) {
  return (
    <section className="rounded-md border border-zinc-800 bg-zinc-900/60 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-zinc-400">
        {title}
      </h3>
      {children}
    </section>
  )
}

export default Panel
