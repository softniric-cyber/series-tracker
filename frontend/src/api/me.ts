import { apiFetch } from './client'
import type { CalendarEntry, FollowedSeries, SeriesProgress } from './types'

export function getCalendar(from: string, to: string): Promise<CalendarEntry[]> {
  const params = new URLSearchParams({ from, to })
  return apiFetch<CalendarEntry[]>(`/me/calendar?${params.toString()}`)
}

export function getMySeries(): Promise<FollowedSeries[]> {
  return apiFetch<FollowedSeries[]>('/me/series')
}

export function followSeries(tmdbId: number): Promise<FollowedSeries> {
  return apiFetch<FollowedSeries>(`/me/series/${tmdbId}`, { method: 'POST' })
}

export function unfollowSeries(tmdbId: number): Promise<void> {
  return apiFetch<void>(`/me/series/${tmdbId}`, { method: 'DELETE' })
}

export function getProgress(tmdbId: number): Promise<SeriesProgress> {
  return apiFetch<SeriesProgress>(`/me/series/${tmdbId}/progress`)
}

export function markEpisodeWatched(episodeId: number): Promise<void> {
  return apiFetch<void>(`/me/episodes/${episodeId}/watched`, { method: 'PUT' })
}

export function unmarkEpisodeWatched(episodeId: number): Promise<void> {
  return apiFetch<void>(`/me/episodes/${episodeId}/watched`, { method: 'DELETE' })
}

export function markSeasonWatched(tmdbId: number, seasonNumber: number): Promise<void> {
  return apiFetch<void>(`/me/series/${tmdbId}/seasons/${seasonNumber}/watched`, { method: 'PUT' })
}

export function unmarkSeasonWatched(tmdbId: number, seasonNumber: number): Promise<void> {
  return apiFetch<void>(`/me/series/${tmdbId}/seasons/${seasonNumber}/watched`, {
    method: 'DELETE',
  })
}
