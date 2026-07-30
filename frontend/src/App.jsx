import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import AppShell from './components/layout/AppShell'
import Overlay from './components/ui/Overlay'
import {
  createChat,
  createPaymentOrder,
  deleteChat,
  getAuthToken,
  getCurrentUser,
  listChats,
  loadBootstrapData,
  loginWithGoogleCredential,
  logout,
  verifyPayment,
} from './lib/api'
import { fallbackRagVersions, getRagVersion, mergeRagVersions } from './lib/ragVersions'

function normalizeBasePath(basePath) {
  if (!basePath || basePath === '/') {
    return '/'
  }

  const prefixed = basePath.startsWith('/') ? basePath : `/${basePath}`
  return prefixed.endsWith('/') ? prefixed.slice(0, -1) : prefixed
}

function displayBasePath() {
  return import.meta.env.BASE_URL || '/'
}

function isMountedAtBasePath() {
  const basePath = normalizeBasePath(import.meta.env.BASE_URL)
  if (basePath === '/') {
    return window.location.pathname === '/'
  }

  return window.location.pathname === basePath || window.location.pathname === `${basePath}/`
}

function App() {
  const [view, setView] = useState('chat')
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState('')
  const [chatsMeta, setChatsMeta] = useState({
    max_chats_per_user: 2,
    max_prompts_per_chat: 10,
    is_admin: false,
  })
  const [chatsError, setChatsError] = useState('')
  const [bootstrap, setBootstrap] = useState({
    loading: true,
    error: '',
    health: null,
    config: null,
    capabilities: null,
    models: null,
    ragVersions: null,
  })
  const [selectedRagVersion, setSelectedRagVersion] = useState('v3.1')
  // Story-first: the overlay always shows on load, then auto-advances to the
  // workbench (see the auto-advance effect). No localStorage skip.
  const [showIntro, setShowIntro] = useState(true)
  const autoAdvancedRef = useRef(false)
  const [authUser, setAuthUser] = useState(null)
  const [hasStoredSession, setHasStoredSession] = useState(() => Boolean(getAuthToken()))
  const [authLoading, setAuthLoading] = useState(true)
  const [authError, setAuthError] = useState('')
  const [now, setNow] = useState(() => Date.now())
  const [paymentLoading, setPaymentLoading] = useState(false)
  const [paymentError, setPaymentError] = useState('')

  const pageTitle = view === 'config' ? 'Config' : 'Chats'

  useEffect(() => {
    let isMounted = true

    loadBootstrapData()
      .then(async (data) => {
        if (!isMounted) {
          return
        }

        const authRequired = Boolean(data.capabilities?.auth?.enabled)
        const user = authRequired
          ? await getCurrentUser()
          : {
              sub: 'local-development',
              email: 'local@contextforge.dev',
              name: '',
              picture: '',
              is_admin: true,
              exp: 0,
            }

        setBootstrap({
          loading: false,
          error: '',
          ...data,
        })
        setAuthUser(user)
        setAuthLoading(false)
      })
      .catch((error) => {
        if (!isMounted) {
          return
        }
        const message = error.message || 'Backend unavailable'

        setBootstrap((current) => ({
          ...current,
          loading: false,
          error: message,
        }))
        setAuthError(message)
        setAuthLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

  const authRequired = Boolean(bootstrap.capabilities?.auth?.enabled)
  const paymentsEnabled = Boolean(bootstrap.capabilities?.payments?.enabled)
  const paymentRequired = Boolean(
    authRequired
      && paymentsEnabled
      && authUser
      && !authUser.is_admin
      && !authUser.paid,
  )
  const shouldShowOverlay = !authLoading && (!authUser || showIntro || paymentRequired)
  const shouldShowAppShell = (authLoading && hasStoredSession) || (!authLoading && Boolean(authUser) && !paymentRequired)

  // Once per load: a logged-in, entitled user sees the story overlay for 2s, then
  // it auto-advances to the workbench. Manual re-opens of the story (via the Story
  // button) are left alone.
  useEffect(() => {
    if (authLoading || !authUser || paymentRequired || !showIntro || autoAdvancedRef.current) {
      return undefined
    }
    const timerId = window.setTimeout(() => {
      autoAdvancedRef.current = true
      setShowIntro(false)
    }, 2000)
    return () => window.clearTimeout(timerId)
  }, [authLoading, authUser, paymentRequired, showIntro])

  const applyChatList = (data) => {
    setChats(data.chats || [])
    setChatsMeta({
      max_chats_per_user: data.max_chats_per_user ?? 2,
      max_prompts_per_chat: data.max_prompts_per_chat ?? 10,
      is_admin: Boolean(data.is_admin),
    })
    return data
  }

  useEffect(() => {
    // Load chats as soon as the user is entitled, in parallel with the story
    // overlay, so the workbench is ready the moment the overlay auto-advances.
    if (!authUser || paymentRequired) {
      return undefined
    }

    let isMounted = true
    listChats()
      .then((data) => {
        if (!isMounted) {
          return
        }
        applyChatList(data)
        setActiveChatId((current) => current || data.chats?.[0]?.id || '')
      })
      .catch((error) => {
        if (isMounted) {
          setChatsError(error.message || 'Failed to load chats')
        }
      })

    return () => {
      isMounted = false
    }
  }, [authUser, paymentRequired, showIntro])

  async function refreshChats(selectId) {
    const data = applyChatList(await listChats())
    if (selectId) {
      setActiveChatId(selectId)
    }
    return data
  }

  async function handleNewChat() {
    setChatsError('')
    try {
      const chat = await createChat('New chat')
      await refreshChats(chat.id)
      setView('chat')
    } catch (error) {
      setChatsError(error.message || 'Could not create chat')
    }
  }

  function handleSelectChat(chatId) {
    setActiveChatId(chatId)
    setView('chat')
  }

  async function handleDeleteChat(chatId) {
    setChatsError('')
    try {
      await deleteChat(chatId)
      const data = await refreshChats()
      if (activeChatId === chatId) {
        setActiveChatId(data.chats?.[0]?.id || '')
      }
    } catch (error) {
      setChatsError(error.message || 'Could not delete chat')
    }
  }

  useEffect(() => {
    if (!authRequired || !authUser || authUser.is_admin || !authUser.exp) {
      return undefined
    }

    const intervalId = window.setInterval(() => {
      const currentTime = Date.now()
      const currentSeconds = Math.floor(currentTime / 1000)
      setNow(currentTime)

      if (Number(authUser.exp) <= currentSeconds) {
        window.clearInterval(intervalId)
        logout()
        setAuthUser(null)
        setShowIntro(true)
      }
    }, 1000)
    return () => window.clearInterval(intervalId)
  }, [authRequired, authUser])

  const usageSecondsRemaining = useMemo(() => {
    if (!authRequired || !authUser || authUser.is_admin || !authUser.exp) {
      return null
    }
    return Math.max(0, Number(authUser.exp) - Math.floor(now / 1000))
  }, [authRequired, authUser, now])

  function formatUsage(seconds) {
    if (paymentRequired) {
      return 'payment'
    }
    if (seconds === null) {
      return authRequired ? 'unlimited' : 'local'
    }
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`
  }

  // When inference runs on Modal, surface "Modal" instead of the generic "online"
  // (label comes from the backend, derived from OLLAMA_BASE_URL - single source).
  const inferenceLocationLabel = bootstrap.models?.ollama?.location_label
  const onlineLabel = inferenceLocationLabel === 'Modal' ? 'Modal' : 'online'
  const statusItems = [
    { label: 'Frontend', value: 'ready', tone: 'ok' },
    {
      label: 'Backend',
      value: bootstrap.loading ? 'checking' : bootstrap.error ? 'offline' : onlineLabel,
      tone: bootstrap.loading ? 'warn' : bootstrap.error ? 'bad' : 'ok',
    },
    {
      label: 'Usage',
      value: formatUsage(usageSecondsRemaining),
      tone: paymentRequired || (usageSecondsRemaining !== null && usageSecondsRemaining < 300) ? 'warn' : 'ok',
    },
  ]
  const ragVersions = useMemo(
    () => mergeRagVersions(bootstrap.ragVersions?.versions || fallbackRagVersions),
    [bootstrap.ragVersions],
  )
  const activeRagVersion = getRagVersion(ragVersions, selectedRagVersion)

  function enterWorkbench() {
    if (bootstrap.error) {
      setAuthError(`Backend unavailable: ${bootstrap.error}`)
      setShowIntro(true)
      return
    }
    if (!authUser) {
      setShowIntro(true)
      return
    }
    if (paymentRequired) {
      setShowIntro(true)
      return
    }
    autoAdvancedRef.current = true
    setShowIntro(false)
  }

  async function handleGoogleCredential(credential) {
    setAuthError('')
    try {
      const user = await loginWithGoogleCredential(credential)
      setAuthUser(user)
      setHasStoredSession(true)
      // Show the story overlay after sign-in; entitled users auto-advance via the
      // 2s timer, payment-required users stay on the overlay.
      autoAdvancedRef.current = false
      setShowIntro(true)
    } catch (error) {
      setAuthError(error.message || 'Google login failed')
      setShowIntro(true)
    }
  }

  function handleLogout() {
    logout()
    setAuthUser(null)
    setHasStoredSession(false)
    setAuthError('')
    setShowIntro(true)
  }

  function loadRazorpayCheckout() {
    if (window.Razorpay) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const existingScript = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]')
      if (existingScript) {
        existingScript.addEventListener('load', resolve, { once: true })
        existingScript.addEventListener('error', reject, { once: true })
        return
      }

      const script = document.createElement('script')
      script.src = 'https://checkout.razorpay.com/v1/checkout.js'
      script.async = true
      script.onload = resolve
      script.onerror = reject
      document.head.appendChild(script)
    })
  }

  async function handleStartPayment() {
    setPaymentError('')
    setPaymentLoading(true)
    try {
      const order = await createPaymentOrder()
      await loadRazorpayCheckout()
      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: order.name,
        description: order.description,
        order_id: order.order_id,
        prefill: {
          name: authUser?.name || '',
          email: authUser?.email || '',
        },
        handler: async (response) => {
          try {
            const user = await verifyPayment(response)
            setAuthUser(user)
            setHasStoredSession(true)
            autoAdvancedRef.current = true
            setShowIntro(false)
          } catch (error) {
            setPaymentError(error.message || 'Payment verification failed')
            setShowIntro(true)
          } finally {
            setPaymentLoading(false)
          }
        },
        modal: {
          ondismiss: () => setPaymentLoading(false),
        },
      })
      checkout.open()
    } catch (error) {
      setPaymentError(error.message || 'Payment setup failed')
      setPaymentLoading(false)
    }
  }

  if (!isMountedAtBasePath()) {
    const basePath = normalizeBasePath(import.meta.env.BASE_URL)
    const mountedPath = displayBasePath()
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-5 text-zinc-100">
        <section className="w-full max-w-md rounded-md border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">
            ContextForge
          </div>
          <h1 className="mt-3 text-2xl font-semibold">404 - Route not available</h1>
          <p className="mt-3 text-sm leading-6 text-zinc-400">
            This frontend is mounted at <span className="text-zinc-100">{mountedPath}</span>.
          </p>
          <a
            href={basePath}
            className="mt-5 inline-flex rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-zinc-950 hover:brightness-110"
          >
            Open ContextForge
          </a>
        </section>
      </main>
    )
  }

  return (
    <main className={`min-h-screen bg-zinc-950 text-zinc-100 ${activeRagVersion.theme}`}>
      {authLoading && !hasStoredSession ? (
        <div className="flex min-h-screen items-center justify-center bg-zinc-950">
          <div className="rounded-md border border-zinc-800 bg-zinc-900/70 px-4 py-3 text-sm text-zinc-400">
            Loading session...
          </div>
        </div>
      ) : null}
      {shouldShowOverlay && (
        <Overlay
          activeVersion={activeRagVersion}
          authError={authError}
          authUser={authUser}
          authRequired={authRequired}
          googleClientId={bootstrap.capabilities?.auth?.google_client_id || ''}
          onEnter={enterWorkbench}
          onGoogleCredential={handleGoogleCredential}
          onLogout={handleLogout}
          onStartPayment={handleStartPayment}
          payments={bootstrap.capabilities?.payments}
          paymentError={paymentError}
          paymentLoading={paymentLoading}
          paymentRequired={paymentRequired}
          onVersionChange={setSelectedRagVersion}
          versions={ragVersions}
        />
      )}
      {shouldShowAppShell && (
        <AppShell
          view={view}
          onViewChange={setView}
          chats={chats}
          activeChatId={activeChatId}
          chatsMeta={chatsMeta}
          chatsError={chatsError}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
          onChatMutated={refreshChats}
          activeRagVersion={activeRagVersion}
          bootstrap={bootstrap}
          onLogout={handleLogout}
          pageTitle={pageTitle}
          ragVersions={ragVersions}
          selectedRagVersion={selectedRagVersion}
          onRagVersionChange={setSelectedRagVersion}
          onShowIntro={() => setShowIntro(true)}
          statusItems={statusItems}
        />
      )}
    </main>
  )
}

export default App
