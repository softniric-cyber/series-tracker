import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAccessToken, setTokens } from '../auth/tokenStore'
import { ApiError, apiFetch } from './client'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('attaches the access token as a Bearer header', async () => {
    setTokens({ access_token: 'acc', refresh_token: 'ref', token_type: 'bearer' })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/users/me')

    const init = fetchMock.mock.calls[0][1] as RequestInit
    const headers = init.headers as Record<string, string>
    expect(headers['Authorization']).toBe('Bearer acc')
  })

  it('refreshes on 401 and retries the original request', async () => {
    setTokens({ access_token: 'old', refresh_token: 'ref', token_type: 'bearer' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 401 }))
      .mockResolvedValueOnce(
        jsonResponse({ access_token: 'new', refresh_token: 'ref2', token_type: 'bearer' }),
      )
      .mockResolvedValueOnce(jsonResponse({ email: 'a@b.com' }))
    vi.stubGlobal('fetch', fetchMock)

    const data = await apiFetch<{ email: string }>('/users/me')

    expect(data.email).toBe('a@b.com')
    expect(getAccessToken()).toBe('new')
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('clears the session when the refresh also fails', async () => {
    setTokens({ access_token: 'old', refresh_token: 'ref', token_type: 'bearer' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 401 }))
      .mockResolvedValueOnce(new Response('', { status: 401 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch('/users/me')).rejects.toBeInstanceOf(ApiError)
    expect(getAccessToken()).toBeNull()
  })
})
