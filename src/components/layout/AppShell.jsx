import { FiLogOut } from 'react-icons/fi'
import ConfigPage from '../sections/ConfigPage'
import Workbench from '../sections/Workbench'
import { navItems } from './navigation'

function AppShell({
  activePage,
  activeRagVersion,
  bootstrap,
  onLogout,
  onPageChange,
  pageTitle,
  ragVersions,
  selectedRagVersion,
  onRagVersionChange,
  onShowIntro,
  statusItems,
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden w-80 shrink-0 border-r border-[color:var(--theme-border)] bg-zinc-950/95 lg:flex lg:flex-col">
        <div className="border-b border-zinc-800 px-6 py-5">
          <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--theme-accent)]">
            ContextForge
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-white">
            RAG Workbench
          </h1>
          <p className="mt-2 text-sm leading-6 text-zinc-400">
            Ingest documents, inspect retrieval, and generate grounded answers.
          </p>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Primary">
          {navItems.map((item) => {
            const isActive = activePage === item.id

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onPageChange(item.id)}
                className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition ${
                  isActive
                    ? 'bg-[color:var(--theme-accent)] text-zinc-950'
                    : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
                }`}
              >
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="border-t border-zinc-800 p-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Retrieval Story
          </div>
          <div className="mt-3 space-y-2">
            {ragVersions.map((version) => {
              const isActive = selectedRagVersion === version.id
              return (
                <button
                  key={version.id}
                  type="button"
                  onClick={() => onRagVersionChange(version.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left transition ${
                    isActive
                      ? 'border-[color:var(--theme-accent)] bg-[color:var(--theme-surface)]'
                      : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold text-zinc-100">{version.shortLabel}</span>
                    <span className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                      {version.stage}
                    </span>
                  </div>
                  <div className="mt-1 text-xs leading-5 text-zinc-400">{version.headline}</div>
                </button>
              )
            })}
          </div>
        </div>
      </aside>

      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="border-b border-zinc-800 bg-zinc-950/90 px-4 py-4 sm:px-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-zinc-500">
                {pageTitle} / {activeRagVersion.shortLabel}
              </div>
              <h2 className="mt-1 text-xl font-semibold text-white sm:text-2xl">
                {activeRagVersion.headline}
              </h2>
              <p className="mt-1 max-w-3xl text-sm text-zinc-400">{activeRagVersion.description}</p>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center">
              <label className="col-span-2 min-w-44 sm:col-span-1">
                <span className="sr-only">RAG version</span>
                <select
                  value={selectedRagVersion}
                  onChange={(event) => onRagVersionChange(event.target.value)}
                  className="h-full w-full rounded-md border border-[color:var(--theme-border)] bg-zinc-900 px-3 py-2 text-sm font-medium text-zinc-100 outline-none"
                >
                  {ragVersions.map((version) => (
                    <option key={version.id} value={version.id}>
                      {version.shortLabel} - {version.stage}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={onShowIntro}
                className="rounded-md border border-[color:var(--theme-border)] bg-[color:var(--theme-surface)] px-3 py-2 text-left text-sm font-medium text-zinc-100 hover:brightness-110"
              >
                Story
              </button>
              {statusItems.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={item.onClick}
                  disabled={!item.onClick}
                  className={`rounded-md border px-3 py-2 text-left ${
                    item.tone === 'action'
                      ? 'border-cyan-400/50 bg-cyan-400/10 hover:bg-cyan-400/20'
                      : 'border-zinc-800 bg-zinc-900'
                  }`}
                >
                  <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                    {item.label}
                  </div>
                  <div
                    className={`mt-1 text-sm font-medium ${
                      item.tone === 'ok'
                        ? 'text-emerald-300'
                        : item.tone === 'warn'
                          ? 'text-amber-300'
                          : item.tone === 'action'
                            ? 'text-cyan-200'
                            : 'text-zinc-400'
                    }`}
                  >
                    {item.value}
                  </div>
                </button>
              ))}
              <button
                type="button"
                onClick={onLogout}
                aria-label="Logout"
                title="Logout"
                className="inline-flex h-[54px] w-11 items-center justify-center rounded-md border border-red-900/70 bg-red-950/20 text-red-200 hover:bg-red-950/40"
              >
                <FiLogOut className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="mt-4 flex gap-2 overflow-x-auto pb-1 lg:hidden">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onPageChange(item.id)}
                className={`shrink-0 rounded-md px-3 py-2 text-sm ${
                  activePage === item.id
                    ? 'bg-[color:var(--theme-accent)] text-zinc-950'
                    : 'bg-zinc-900 text-zinc-300'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-hidden px-4 py-5 sm:px-6">
          {activePage === 'workbench' && (
            <Workbench
              activeRagVersion={activeRagVersion}
              bootstrap={bootstrap}
              selectedRagVersion={selectedRagVersion}
            />
          )}
          {activePage === 'config' && <ConfigPage bootstrap={bootstrap} />}
        </div>
      </section>
    </div>
  )
}

export default AppShell
