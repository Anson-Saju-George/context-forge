import { useEffect, useRef, useState } from 'react'

function Overlay({
  activeVersion,
  authError,
  authRequired,
  authUser,
  googleClientId,
  onEnter,
  onGoogleCredential,
  onLogout,
  onStartPayment,
  onVersionChange,
  payments,
  paymentError,
  paymentLoading,
  paymentRequired,
  versions,
}) {
  // All labels derive from the backend capabilities payload (single source of
  // truth from env); never hardcode the price or duration here.
  const payLabel = payments?.amount_label && payments?.duration_label
    ? `Pay ${payments.amount_label} for ${payments.duration_label}`
    : 'Pay for access'
  const googleButtonRef = useRef(null)
  const [scriptReady, setScriptReady] = useState(Boolean(window.google?.accounts?.id))
  const [authPromptOpen, setAuthPromptOpen] = useState(false)
  const [headlineVisible, setHeadlineVisible] = useState(false)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setHeadlineVisible(true), 40)
    return () => window.clearTimeout(timeoutId)
  }, [])

  useEffect(() => {
    if (scriptReady || !googleClientId) {
      return undefined
    }

    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]')
    if (existingScript) {
      existingScript.addEventListener('load', () => setScriptReady(true), { once: true })
      return undefined
    }

    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => setScriptReady(true)
    document.head.appendChild(script)
    return undefined
  }, [googleClientId, scriptReady])

  useEffect(() => {
    if (!scriptReady || !googleClientId || authUser) {
      return
    }

    window.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: (response) => onGoogleCredential(response.credential),
    })
  }, [authUser, googleClientId, onGoogleCredential, scriptReady])

  useEffect(() => {
    if (!authPromptOpen || !scriptReady || !googleClientId || !googleButtonRef.current || authUser) {
      return
    }

    googleButtonRef.current.innerHTML = ''
    window.google.accounts.id.renderButton(googleButtonRef.current, {
      theme: 'filled_black',
      size: 'large',
      width: 280,
      text: 'signin_with',
    })
  }, [authPromptOpen, authUser, googleClientId, scriptReady])

  function handleEnter() {
    if (authRequired && !authUser) {
      if (scriptReady && googleClientId && window.google?.accounts?.id) {
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed?.() || notification.isSkippedMoment?.()) {
            setAuthPromptOpen(true)
          }
        })
      } else {
        setAuthPromptOpen(true)
      }
      return
    }
    onEnter()
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-zinc-950 text-white">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:52px_52px]" />
      <div className="absolute inset-x-0 top-0 h-px bg-[color:var(--theme-accent)] opacity-70" />

      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950/90 px-5 py-5 sm:px-8">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.32em] text-[color:var(--theme-accent)]">
              ContextForge
            </div>
            <div className="mt-1 text-sm text-zinc-500">RAG evolution workbench</div>
          </div>
          <button
            type="button"
            onClick={handleEnter}
            className="rounded-md border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:border-[color:var(--theme-accent)] hover:text-white"
          >
            Enter
          </button>
        </header>

        <section className="grid flex-1 gap-6 px-5 py-6 sm:px-8 lg:grid-cols-[minmax(360px,0.82fr)_minmax(0,1.18fr)]">
          <div className="flex min-h-0 flex-col justify-center">
            <div className="mb-5 flex flex-wrap gap-2">
              {['V0 similarity', 'BM25', 'routing', 'evidence-only V3.1'].map((item) => (
                <span
                  key={item}
                  className="rounded border border-[color:var(--theme-border)] bg-[color:var(--theme-surface)] px-3 py-1 text-xs font-medium text-zinc-200"
                >
                  {item}
                </span>
              ))}
            </div>
            <h1 className="max-w-4xl text-5xl font-semibold leading-[1.02] tracking-normal text-white sm:text-7xl">
              {[
                'Watch RAG mature',
                'from toy search',
                'to evidence architecture.',
              ].map((segment, index) => (
                <span
                  key={segment}
                  className={`mr-[0.28em] inline-block transition-all duration-700 ease-out ${
                    headlineVisible ? 'translate-y-0 opacity-100 blur-0' : 'translate-y-1.5 opacity-0 blur-[4px]'
                  }`}
                  style={{ transitionDelay: `${index * 140}ms` }}
                >
                  {segment}
                </span>
              ))}
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-400 sm:text-lg">
              Switch between saved retrieval generations, run the same document questions, and see
              how retrieval quality changes as routing, ranking, context selection, and extraction
              discipline improve.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleEnter}
                className="rounded-md bg-[color:var(--theme-accent)] px-5 py-3 text-sm font-semibold text-zinc-950 hover:brightness-110"
              >
                Open Workbench
              </button>
              <div className="rounded-md border border-zinc-800 bg-zinc-950/80 px-5 py-3 text-sm text-zinc-400">
                Current selection: <span className="font-medium text-zinc-100">{activeVersion.label}</span>
              </div>
            </div>

            {authError && (
              <div className="mt-5 rounded-md border border-red-900/70 bg-red-950/30 px-4 py-3 text-sm text-red-200">
                {authError}
              </div>
            )}

            {paymentRequired && (
              <div className="mt-5 rounded-md border border-zinc-800 bg-zinc-950/80 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-white">Access payment required</div>
                    <div className="truncate text-xs text-zinc-500">{authUser?.email || ''}</div>
                  </div>
                  <button
                    type="button"
                    onClick={onStartPayment}
                    disabled={paymentLoading}
                    className="rounded-md bg-[color:var(--theme-accent)] px-3 py-2 text-sm font-semibold text-zinc-950 hover:brightness-110 disabled:cursor-wait disabled:opacity-60"
                  >
                    {paymentLoading ? 'Opening payment...' : payLabel}
                  </button>
                  <button
                    type="button"
                    onClick={onLogout}
                    className="rounded-md border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:border-zinc-500 hover:text-zinc-100"
                  >
                    Sign out
                  </button>
                  {paymentError && (
                    <div className="rounded-md border border-red-900/70 bg-red-950/30 px-3 py-2 text-sm text-red-200 sm:col-span-2">
                      {paymentError}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="min-h-0 rounded-md border border-zinc-800 bg-zinc-950/90">
            <div className="border-b border-zinc-800 px-5 py-4">
              <div className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
                Retrieval Timeline
              </div>
              <div className="mt-1 text-lg font-semibold text-white">{activeVersion.headline}</div>
            </div>

            <div className="grid min-h-0 gap-0 lg:grid-cols-[300px_minmax(0,1fr)]">
              <div className="border-b border-zinc-800 p-4 lg:border-b-0 lg:border-r">
                <div className="space-y-2">
                  {versions.map((version) => {
                    const isActive = activeVersion.id === version.id
                    return (
                      <button
                        key={version.id}
                        type="button"
                        onClick={() => onVersionChange(version.id)}
                        className={`w-full rounded-md border px-3 py-3 text-left transition ${
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

              <VersionDiagram activeVersion={activeVersion} />
            </div>
          </div>
        </section>
      </div>

      {authPromptOpen && authRequired && !authUser && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/45 px-5">
          <div className="rounded-md border border-zinc-800 bg-zinc-950/95 p-4 shadow-2xl">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setAuthPromptOpen(false)}
                className="rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-400 hover:border-zinc-500 hover:text-zinc-100"
              >
                x
              </button>
            </div>
            {!googleClientId && (
              <div className="mt-2 max-w-xs text-sm text-red-200">
                Google sign-in is not configured on the backend.
              </div>
            )}
            {googleClientId && !scriptReady && (
              <div className="mt-2 max-w-xs text-sm text-zinc-300">
                Loading Google sign-in...
              </div>
            )}
            <div ref={googleButtonRef} className="mt-2 flex justify-center" />
          </div>
        </div>
      )}

    </div>
  )
}

function VersionDiagram({ activeVersion }) {
  const stages = activeVersion.process || [
    ['Query', 'user question'],
    ['Retrieve', activeVersion.shortLabel],
    ['Rank', activeVersion.chips[0]],
    ['Pack', activeVersion.chips[1] || 'context'],
    ['Answer', 'citations'],
  ]

  return (
    <div className="flex min-h-[460px] flex-col justify-center p-5">
      <div className="grid gap-3 xl:grid-cols-5">
        {stages.map(([label, detail], index) => (
          <div key={label} className="relative">
            {index < stages.length - 1 && (
              <div className="absolute left-[calc(100%-8px)] top-10 hidden h-px w-6 bg-[color:var(--theme-accent)] opacity-70 xl:block" />
            )}
            <div className="h-full rounded-md border border-zinc-800 bg-black/30 p-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
                {String(index + 1).padStart(2, '0')}
              </div>
              <div className="mt-3 text-base font-semibold text-white">{label}</div>
              <div className="mt-1 min-h-10 text-sm leading-5 text-zinc-400">{detail}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-md border border-[color:var(--theme-border)] bg-[color:var(--theme-surface)] p-5">
        <div className="text-sm font-semibold text-white">{activeVersion.label}</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-300">{activeVersion.description}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {activeVersion.chips.map((chip) => (
            <span key={chip} className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-300">
              {chip}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Overlay
