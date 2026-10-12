import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../auth/tokenStore'
import { API_URL } from '../lib/config'
import type { TokenPair } from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

interface ApiFetchOptions {
  method?: string
  body?: unknown
  /** Adjuntar el access token y activar el refresco en 401. Por defecto true. */
  auth?: boolean
}

function rawFetch(path: string, token: string | null, options: ApiFetchOptions): Promise<Response> {
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`
  return fetch(`${API_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })
}

type RefreshResult = 'refreshed' | 'rejected' | 'unavailable'

// Refresco en curso compartido: si varias peticiones reciben 401 a la vez, todas
// esperan al mismo /auth/refresh en lugar de lanzar uno cada una.
let refreshInFlight: Promise<RefreshResult> | null = null

async function doRefresh(): Promise<RefreshResult> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return 'rejected'
  let resp: Response
  try {
    resp = await rawFetch('/auth/refresh', null, {
      method: 'POST',
      body: { refresh_token: refreshToken },
    })
  } catch {
    return 'unavailable'
  }
  if (resp.status === 401) {
    // Solo un 401 significa que el refresh token ya no vale: entonces sí cerramos sesión.
    clearTokens()
    return 'rejected'
  }
  // 5xx, 429 o el backend despertando (arranque en frío): conservamos la sesión.
  if (!resp.ok) return 'unavailable'
  setTokens((await resp.json()) as TokenPair)
  return 'refreshed'
}

function tryRefresh(): Promise<RefreshResult> {
  refreshInFlight ??= doRefresh().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function extractMessage(resp: Response): Promise<string> {
  try {
    const data: unknown = await resp.json()
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
    }
  } catch {
    // respuesta sin cuerpo JSON
  }
  return resp.statusText || 'Request failed'
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const useAuth = options.auth ?? true
  let resp = await rawFetch(path, useAuth ? getAccessToken() : null, options)

  if (resp.status === 401 && useAuth) {
    const result = await tryRefresh()
    if (result === 'refreshed') {
      resp = await rawFetch(path, getAccessToken(), options)
    } else if (result === 'unavailable') {
      throw new ApiError(503, 'Service unavailable')
    }
  }

  if (!resp.ok) {
    const message = await extractMessage(resp)
    if (resp.status === 401 && useAuth) clearTokens()
    throw new ApiError(resp.status, message)
  }

  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}
