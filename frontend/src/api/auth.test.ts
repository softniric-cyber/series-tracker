import { afterEach, describe, expect, it, vi } from 'vitest'
import { googleLogin } from './auth'

function tokenResponse(): Response {
  return new Response(
    JSON.stringify({ access_token: 'a', refresh_token: 'r', token_type: 'bearer' }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  )
}

describe('googleLogin', () => {
  afterEach(() => vi.restoreAllMocks())

  it('posts the credential to /auth/google', async () => {
    const fetchMock = vi.fn().mockResolvedValue(tokenResponse())
    vi.stubGlobal('fetch', fetchMock)

    const tokens = await googleLogin('cred-123')

    expect(tokens.access_token).toBe('a')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(String(url)).toContain('/auth/google')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ credential: 'cred-123' })
  })
})
