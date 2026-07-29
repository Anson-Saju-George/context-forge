import { FiLogOut, FiPlus, FiSettings, FiTrash2, FiMessageSquare } from 'react-icons/fi'
import ConfigPage from '../sections/ConfigPage'
import Workbench from '../sections/Workbench'

function AppShell({
  view,
  onViewChange,
  chats,
  activeChatId,
  chatsMeta,
  chatsError,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onChatMutated,
  activeRagVersion,
  bootstrap,
  onLogout,
  pageTitle,
  ragVersions,
  selectedRagVersion,
  onRagVersionChange,
  onShowIntro,
  statusItems,
}) {
  const chatCount = chats.length
  const maxChats = chatsMeta?.max_chats_per_user ?? 2
  const isAdmin = Boolean(chatsMeta?.is_admin)
  const atChatLimit = !isAdmin && chatCount >= maxChats

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden w-80 shrink-0 flex-col border-r border-[color:var(--theme-border)] bg-zinc-950/95 lg:flex">
        <div className="border-b border-zinc-800 px-6 py-5">
          <div className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--theme-accent)]">
            ContextForge
          </div>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal text-white">RAG Workbench</h1>
        </div>

        <div className="flex items-center justify-between px-4 pt-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Chats {isAdmin ? '' : `(${chatCount}/${maxChats})`}
          </div>
          <button
            type="button"
            onClick={onNewChat}
            disabled={atChatLimit}
            title={atChatLimit ? `Chat limit reached (${maxChats})` : 'New chat'}
            className="inline-flex items-center gap-1 rounded-md bg-[color:var(--theme-accent)] px-2.5 py-1.5 text-xs font-semibold text-zinc-950 hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
          >
            <FiPlus className="h-3.5 w-3.5" />
            New
          </button>
        </div>

        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3 py-3" aria-label="Chats">
          {chatsError && (
            <div className="mb-2 rounded-md border border-red-900/60 bg-red-950/30 px-3 py-2 text-xs text-red-200">
              {chatsError}
            </div>
          )}
          {chatCount === 0 && (
            <p className="px-3 py-2 text-sm text-zinc-500">No chats yet. Create one to begin.</p>
          )}
          {chats.map((chat) => {
            const isActive = view === 'chat' && activeChatId === chat.id
            return (
              <div
                key={chat.id}
                className={`group flex items-center gap-2 rounded-md px-2 transition ${
                  isActive ? 'bg-[color:var(--theme-surface)]' : 'hover:bg-zinc-900'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectChat(chat.id)}
                  className="flex min-w-0 flex-1 items-center gap-2 py-2.5 text-left"
                >
                  <FiMessageSquare
                    className={`h-4 w-4 shrink-0 ${isActive ? 'text-[color:var(--theme-accent)]' : 'text-zinc-500'}`}
                  />
                  <span className={`truncate text-sm ${isActive ? 'text-white' : 'text-zinc-300'}`}>
                    {chat.title || 'New chat'}
                  </span>
                  <span className="ml-auto shrink-0 text-[10px] text-zinc-600">{chat.message_count}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onDeleteChat(chat.id)}
                  aria-label="Delete chat"
                  title="Delete chat"
                  className="shrink-0 rounded p-1.5 text-zinc-600 opacity-0 transition hover:text-red-300 group-hover:opacity-100"
                >
                  <FiTrash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
        </nav>

        <div className="border-t border-zinc-800 px-3 py-3">
          <button
            type="button"
            onClick={() => onViewChange(view === 'config' ? 'chat' : 'config')}
            className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition ${
              view === 'config'
                ? 'bg-[color:var(--theme-accent)] text-zinc-950'
                : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
            }`}
          >
            <FiSettings className="h-4 w-4" />
            <span>Config</span>
          </button>
        </div>

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
            <button
              type="button"
              onClick={onNewChat}
              disabled={atChatLimit}
              className="inline-flex shrink-0 items-center gap-1 rounded-md bg-[color:var(--theme-accent)] px-3 py-2 text-sm font-semibold text-zinc-950 disabled:bg-zinc-800 disabled:text-zinc-500"
            >
              <FiPlus className="h-4 w-4" />
              New
            </button>
            {chats.map((chat) => (
              <button
                key={chat.id}
                type="button"
                onClick={() => onSelectChat(chat.id)}
                className={`max-w-[9rem] shrink-0 truncate rounded-md px-3 py-2 text-sm ${
                  view === 'chat' && activeChatId === chat.id
                    ? 'bg-[color:var(--theme-surface)] text-white'
                    : 'bg-zinc-900 text-zinc-300'
                }`}
              >
                {chat.title || 'New chat'}
              </button>
            ))}
            <button
              type="button"
              onClick={() => onViewChange(view === 'config' ? 'chat' : 'config')}
              className={`inline-flex shrink-0 items-center gap-1 rounded-md px-3 py-2 text-sm ${
                view === 'config' ? 'bg-[color:var(--theme-accent)] text-zinc-950' : 'bg-zinc-900 text-zinc-300'
              }`}
            >
              <FiSettings className="h-4 w-4" />
              Config
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-hidden px-4 py-5 sm:px-6">
          {view === 'config' ? (
            <ConfigPage bootstrap={bootstrap} />
          ) : (
            <Workbench
              key={activeChatId || 'no-chat'}
              activeRagVersion={activeRagVersion}
              bootstrap={bootstrap}
              selectedRagVersion={selectedRagVersion}
              chatId={activeChatId}
              maxPromptsPerChat={chatsMeta?.max_prompts_per_chat ?? 10}
              isAdmin={isAdmin}
              onNewChat={onNewChat}
              onChatMutated={onChatMutated}
            />
          )}
        </div>
      </section>
    </div>
  )
}

export default AppShell
