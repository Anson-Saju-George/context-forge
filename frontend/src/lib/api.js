import appConfig from '../../../config.json'

const routing = appConfig.routing || {}
const API_BASE_URL = routing.api_base_url || (import.meta.env.DEV ? 'http://localhost:8000' : '')
const API_PREFIX = routing.api_prefix || '/context-forge/api'
const AUTH_TOKEN_KEY = 'contextforge_auth_token'

export function getAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function setAuthToken(token) {
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token)
    return
  }
  window.localStorage.removeItem(AUTH_TOKEN_KEY)
}

function authHeaders() {
  const token = getAuthToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function buildUrl(path) {
  const normalizedBase = API_BASE_URL.replace(/\/$/, '')
  const normalizedPrefix = API_PREFIX.startsWith('/') ? API_PREFIX : `/${API_PREFIX}`
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  return `${normalizedBase}${normalizedPrefix}${normalizedPath}`
}

async function readError(response) {
  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    const payload = await response.json().catch(() => null)
    const detail = payload?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (detail && typeof detail === 'object') {
      return JSON.stringify(detail)
    }
  }

  const message = await response.text().catch(() => '')
  return message || `Request failed with status ${response.status}`
}

export async function getApiJson(path) {
  const response = await fetch(buildUrl(path), {
    headers: authHeaders(),
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function postApiJson(path, payload) {
  const response = await fetch(buildUrl(path), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function postApiForm(path, formData) {
  const response = await fetch(buildUrl(path), {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json()
}

export async function loadBootstrapData() {
  const [health, config, capabilities, models, ragVersions] = await Promise.all([
    getApiJson('/health'),
    getApiJson('/config'),
    getApiJson('/capabilities'),
    getApiJson('/models'),
    getApiJson('/rag-versions'),
  ])

  return { health, config, capabilities, models, ragVersions }
}

export async function getCurrentUser() {
  if (!getAuthToken()) {
    return null
  }

  try {
    return await getApiJson('/auth/me')
  } catch {
    setAuthToken('')
    return null
  }
}

export async function loginWithGoogleCredential(credential) {
  const response = await postApiJson('/auth/google', { credential })
  setAuthToken(response.token)
  return response.user
}

export async function createPaymentOrder() {
  return postApiJson('/payment/order', {})
}

export async function verifyPayment(payload) {
  const response = await postApiJson('/payment/verify', payload)
  setAuthToken(response.token)
  return response.user
}

export function logout() {
  setAuthToken('')
}
