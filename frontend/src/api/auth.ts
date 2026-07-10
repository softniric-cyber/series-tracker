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

export function forgotPassword(email: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/auth/forgot-password', {
    method: 'POST',
    body: { email },
    auth: false,
  })
}

export function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/auth/reset-password', {
    method: 'POST',
    body: { token, new_password: newPassword },
    auth: false,
  })
}
