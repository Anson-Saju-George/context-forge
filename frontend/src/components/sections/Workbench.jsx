import { useEffect, useRef, useState } from 'react'
import ChatBubble from '../common/ChatBubble'
import Panel from '../common/Panel'
import { getApiJson, postApiForm, postApiJson } from '../../lib/api'

function Workbench({ activeRagVersion, bootstrap, selectedRagVersion }) {
  const apiCapabilities = bootstrap.capabilities
  const maxUploadFiles = Number(apiCapabilities?.scheduler?.max_upload_files || 5)
  const defaultModel = apiCapabilities?.generation?.default_model || 'qwen3:4b-instruct'
  const availableModels = bootstrap.models?.ollama?.models ?? []
  const allowedModels = bootstrap.models?.ollama?.allowed_models ?? []
  const visibleModels = allowedModels.length ? availableModels.filter((model) => allowedModels.includes(model)) : availableModels
  const modelOptions = [defaultModel, ...visibleModels].filter(
    (model, index, models) => model && models.indexOf(model) === index,
  )
  const [selectedModel, setSelectedModel] = useState('')
  const activeModel = selectedModel || modelOptions[0] || defaultModel
  const [deterministicMode, setDeterministicMode] = useState(false)
  const activeProvider = deterministicMode ? 'auto' : 'ollama'
  const providerLabel = deterministicMode ? 'deterministic' : 'ollama'
  const [query, setQuery] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [elapsedMs, setElapsedMs] = useState(0)
  const [activePrompt, setActivePrompt] = useState('')
  const [chatError, setChatError] = useState('')
  const [messages, setMessages] = useState([])
  const [documents, setDocuments] = useState([])
  const [totalChunks, setTotalChunks] = useState(0)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [dragActive, setDragActive] = useState(false)
  const [uploadingFileNames, setUploadingFileNames] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const messagesEndRef = useRef(null)

  function mergeFiles(files) {
    const nextFiles = Array.from(files || [])
    if (!nextFiles.length) {
      return
    }

    setSelectedFiles((current) => {
      const seen = new Set(current.map((file) => `${file.name}:${file.size}:${file.lastModified}`))
      const merged = [...current]
      const remainingSlots = Math.max(0, maxUploadFiles - documents.length - current.length)
      if (nextFiles.length > remainingSlots) {
        setUploadError(`Document limit is ${maxUploadFiles} files. You can add ${remainingSlots} more.`)
      }
      nextFiles.forEach((file) => {
        if (merged.length >= maxUploadFiles - documents.length) {
          return
        }
        const key = `${file.name}:${file.size}:${file.lastModified}`
        if (!seen.has(key)) {
          merged.push(file)
          seen.add(key)
        }
      })
      return merged
    })
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isSending])

  useEffect(() => {
    let isMounted = true

    getApiJson('/documents')
      .then((response) => {
        if (!isMounted) {
          return
        }

        setDocuments(response.documents || [])
        setTotalChunks(response.total_chunks || 0)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }

        setDocuments([])
        setTotalChunks(0)
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (!isSending) {
      return undefined
    }

    const startedAt = Date.now()
    const intervalId = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAt)
    }, 250)

    return () => window.clearInterval(intervalId)
  }, [isSending])

  const thinkingDetails = [
    { label: 'version', value: activeRagVersion.shortLabel },
    { label: 'provider', value: providerLabel },
    { label: 'model', value: deterministicMode ? 'benchmark path' : activeModel },
    { label: 'elapsed', value: `${(elapsedMs / 1000).toFixed(1)}s` },
    { label: 'request', value: 'waiting for backend response' },
    { label: 'mode', value: deterministicMode ? 'retrieval + deterministic answer' : 'retrieval + generation' },
    { label: 'prompt', value: activePrompt || 'pending' },
  ]

  async function uploadDocuments() {
    if (!selectedFiles.length || isUploading) {
      return
    }

    const filesToUpload = [...selectedFiles]
    if (documents.length + filesToUpload.length > maxUploadFiles) {
      setUploadError(`Document limit is ${maxUploadFiles} files.`)
      return
    }
    const formData = new FormData()
    formData.append('chat_id', 'default')
    filesToUpload.forEach((file) => formData.append('files', file))

    setIsUploading(true)
    setUploadingFileNames(filesToUpload.map((file) => file.name))
    setUploadError('')

    try {
      const response = await postApiForm('/ingest', formData)
      setDocuments(response.documents ? [...documents, ...response.documents] : documents)
      setTotalChunks(response.total_chunks || 0)
      setSelectedFiles([])
    } catch (error) {
      setUploadError(error.message || 'Upload failed')
    } finally {
      setIsUploading(false)
      setUploadingFileNames([])
    }
  }

  async function clearDocuments() {
    if (!documents.length && !totalChunks) {
      return
    }

    setIsUploading(true)
    setUploadError('')

    try {
      const response = await postApiJson('/documents/clear', { chat_id: 'default' })
      setDocuments(response.documents || [])
      setTotalChunks(response.total_chunks || 0)
    } catch (error) {
      setUploadError(error.message || 'Clear failed')
    } finally {
      setIsUploading(false)
    }
  }

  async function sendMessage() {
    const message = query.trim()

    if (!message || isSending) {
      return
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
    }
    const conversationMessages = [...messages, userMessage]

    setMessages(conversationMessages)
    setQuery('')
    setChatError('')
    setElapsedMs(0)
    setActivePrompt(message)
    setIsSending(true)

    try {
      const response = await postApiJson('/chat', {
        message,
        chat_id: 'default',
        use_retrieval: true,
        messages: conversationMessages
          .filter((item) => item.role === 'user' || item.role === 'assistant')
          .slice(-10)
          .map((item) => ({
            role: item.role,
            content: item.content,
          })),
        provider: activeProvider,
        model: deterministicMode ? null : activeModel,
        rag_version: selectedRagVersion,
      })
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
          reasoning: response.reasoning_summary,
          citations: response.citations,
          retrieval: response.retrieval,
          meta: `${response.latency_ms}ms`,
        },
      ])
    } catch (error) {
      const message = error.message || 'Chat request failed'
      setChatError(message)
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: message,
          meta: 'error',
        },
      ])
    } finally {
      setIsSending(false)
      setActivePrompt('')
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  function handleDragOver(event) {
    event.preventDefault()
    setDragActive(true)
  }

  function handleDragLeave(event) {
    event.preventDefault()
    const nextTarget = event.relatedTarget
    if (nextTarget && event.currentTarget.contains(nextTarget)) {
      return
    }
    setDragActive(false)
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragActive(false)
    mergeFiles(event.dataTransfer?.files)
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="flex h-[calc(100vh-132px)] min-h-[620px] flex-col rounded-md border border-zinc-800 bg-zinc-900/60">
        <div className="border-b border-zinc-800 px-5 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Chat</h3>
              <p className="mt-1 text-sm text-zinc-400">
                {activeRagVersion.label} / {providerLabel} / {bootstrap.error ? 'Backend offline' : bootstrap.loading ? 'Checking backend' : 'Backend connected'}
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label className="flex h-10 items-center gap-2 rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200">
                <input
                  type="checkbox"
                  checked={deterministicMode}
                  onChange={(event) => setDeterministicMode(event.target.checked)}
                  className="h-4 w-4 accent-[color:var(--theme-accent)]"
                />
                Deterministic
              </label>
              <select
                value={activeModel}
                onChange={(event) => setSelectedModel(event.target.value)}
                disabled={deterministicMode}
                className="h-10 rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-200 disabled:cursor-not-allowed disabled:text-zinc-600"
              >
                {modelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="rounded-md border border-zinc-800 bg-zinc-950/70 p-5">
              <h3 className="text-base font-semibold text-white">Start a grounded query</h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
                Ask questions over the uploaded documents. Retrieval context, citations, and
                extraction mode details appear with assistant responses.
              </p>
            </div>
          )}
          {messages.map((message) => (
            <ChatBubble
              key={message.id}
              role={message.role}
              meta={message.meta}
              reasoning={message.reasoning}
              citations={message.citations}
              retrieval={message.retrieval}
            >
              {message.content}
            </ChatBubble>
          ))}
          {isSending && (
            <ChatBubble
              role="assistant"
              meta={`${providerLabel} / ${deterministicMode ? 'benchmark path' : activeModel} / waiting`}
              detailsTitle="Generation status"
              details={thinkingDetails}
            >
              {deterministicMode ? 'Building deterministic response...' : 'Generating response...'}
            </ChatBubble>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="shrink-0 border-t border-zinc-800 bg-zinc-900/95 p-4">
          {chatError && (
            <div className="mb-3 rounded-md border border-red-900/60 bg-red-950/30 px-3 py-2 text-sm text-red-200">
              {chatError}
            </div>
          )}
          <div className="flex flex-col gap-3 rounded-md border border-zinc-800 bg-zinc-950 p-3 md:flex-row md:items-end">
            <label className="flex-1">
              <span className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
                Message
              </span>
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                rows="3"
                className="mt-2 w-full resize-none rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-[color:var(--theme-accent)]"
                placeholder="Ask the backend chat service..."
              />
            </label>
            <button
              type="button"
              onClick={sendMessage}
              disabled={isSending || !query.trim()}
              className="h-10 rounded-md bg-[color:var(--theme-accent)] px-4 text-sm font-semibold text-zinc-950 hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-400"
            >
              {isSending ? 'Sending' : 'Ask'}
            </button>
          </div>
        </div>
      </section>

      <aside className="space-y-5">
        <Panel title="Version">
          <div className="space-y-3">
            <div>
              <div className="text-sm font-semibold text-white">{activeRagVersion.label}</div>
              <p className="mt-2 text-sm leading-6 text-zinc-400">{activeRagVersion.description}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {activeRagVersion.chips.map((chip) => (
                <span
                  key={chip}
                  className="rounded border border-[color:var(--theme-border)] bg-[color:var(--theme-surface)] px-2 py-1 text-xs text-zinc-200"
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Documents">
          <div className="space-y-3">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`rounded-md border border-dashed p-3 transition ${
                dragActive
                  ? 'border-[color:var(--theme-accent)] bg-[color:var(--theme-surface)]'
                  : 'border-zinc-700 bg-zinc-950/70'
              }`}
            >
              <div className="mb-3 text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
                Upload .md / .mdx / .txt / .pdf / .docx
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <label className="inline-flex cursor-pointer items-center rounded-md bg-[color:var(--theme-accent)] px-3 py-2 text-sm font-semibold text-zinc-950 hover:brightness-110">
                  Choose files
                  <input
                    type="file"
                    multiple
                    accept=".md,.mdx,.txt,.pdf,.docx,text/markdown,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(event) => mergeFiles(event.target.files)}
                    className="sr-only"
                  />
                </label>
                <p className="text-sm text-zinc-400">Drag n drop file here</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={uploadDocuments}
                disabled={!selectedFiles.length || isUploading}
                className="h-9 rounded-md bg-[color:var(--theme-accent)] px-3 text-sm font-semibold text-zinc-950 hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-400"
              >
                {isUploading ? 'Working' : 'Ingest'}
              </button>
              <button
                type="button"
                onClick={clearDocuments}
                disabled={isUploading || (!documents.length && !totalChunks)}
                className="h-9 rounded-md border border-red-900/70 px-3 text-sm font-semibold text-red-200 hover:bg-red-950/40 disabled:cursor-not-allowed disabled:border-zinc-800 disabled:text-zinc-600"
              >
                Clear
              </button>
            </div>
            {uploadError && (
              <div className="rounded-md border border-red-900/60 bg-red-950/30 px-3 py-2 text-xs text-red-200">
                {uploadError}
              </div>
            )}
            <div className="text-xs text-zinc-500">
              File slots: {documents.length + selectedFiles.length}/{maxUploadFiles}
            </div>
            <div className="flex items-center gap-2">
              <div className="flex min-w-0 flex-1 items-center justify-between rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2">
                <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">Docs</div>
                <div className="text-base font-semibold text-zinc-100">{documents.length}</div>
              </div>
              <div className="flex min-w-0 flex-1 items-center justify-between rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2">
                <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">Chunks</div>
                <div className="text-base font-semibold text-zinc-100">{totalChunks}</div>
              </div>
            </div>
            <div className="max-h-48 space-y-2 overflow-y-auto">
              {selectedFiles.length > 0 ? (
                selectedFiles.map((file) => {
                  const isFileUploading = uploadingFileNames.includes(file.name)
                  return (
                    <div
                      key={`${file.name}:${file.size}:${file.lastModified}`}
                      className="rounded-md border border-zinc-800 bg-zinc-950 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium text-zinc-100">{file.name}</div>
                          <div className="mt-1 text-xs text-zinc-500">
                            {(file.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                        <div className={`shrink-0 text-xs font-medium ${isFileUploading ? 'text-amber-300' : 'text-zinc-400'}`}>
                          {isFileUploading ? 'Uploading...' : 'Ready'}
                        </div>
                      </div>
                    </div>
                  )
                })
              ) : documents.length ? (
                documents.map((document) => (
                  <div
                    key={document.id}
                    className="rounded-md border border-zinc-800 bg-zinc-950 p-3"
                  >
                    <div className="truncate text-sm font-medium text-zinc-100">
                      {document.stored_filename}
                    </div>
                    <div className="mt-1 text-xs text-zinc-500">
                      {document.chunk_count} chunks
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-zinc-500">No documents ingested yet.</p>
              )}
            </div>
          </div>
        </Panel>

      </aside>
    </div>
  )
}

export default Workbench
