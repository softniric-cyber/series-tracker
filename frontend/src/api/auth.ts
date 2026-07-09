import { apiFetch } from './client'
import type { TokenPair, UserPublic } from './types'

export function login(email: string, password: string): Promise<TokenPair> {
  return apiFetch<TokenPair>('/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
}

export function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<TokenPair> {
  return apiFetch<TokenPair>('/auth/register', {
    method: 'POST',
    body: { email, password, display_name: displayName ?? null },
    auth: false,
  })
}

export function getMe(): Promise<UserPublic> {
  return apiFetch<UserPublic>('/users/me')
}
