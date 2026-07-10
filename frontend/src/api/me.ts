import { apiFetch } from './client'
import type { FollowedSeries } from './types'

export function getMySeries(): Promise<FollowedSeries[]> {
  return apiFetch<FollowedSeries[]>('/me/series')
}

export function followSeries(tmdbId: number): Promise<FollowedSeries> {
  return apiFetch<FollowedSeries>(`/me/series/${tmdbId}`, { method: 'POST' })
}

export function unfollowSeries(tmdbId: number): Promise<void> {
  return apiFetch<void>(`/me/series/${tmdbId}`, { method: 'DELETE' })
}
