import { apiFetch } from './client'
import type { UserDataExport } from './types'

export function exportMyData(): Promise<UserDataExport> {
  return apiFetch<UserDataExport>('/users/me/export')
}

export function deleteAccount(): Promise<void> {
  return apiFetch<void>('/users/me', { method: 'DELETE' })
}
