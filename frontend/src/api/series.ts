import { apiFetch } from './client'
import type {
  SeasonDetail,
  SeriesDetail,
  SeriesProviders,
  SeriesSearchResponse,
} from './types'

export function searchSeries(query: string, page = 1): Promise<SeriesSearchResponse> {
  const params = new URLSearchParams({ q: query, page: String(page) })
  return apiFetch<SeriesSearchResponse>(`/series/search?${params.toString()}`)
}

export function getSeriesDetail(tmdbId: number): Promise<SeriesDetail> {
  return apiFetch<SeriesDetail>(`/series/${tmdbId}`)
}

export function getSeason(tmdbId: number, seasonNumber: number): Promise<SeasonDetail> {
  return apiFetch<SeasonDetail>(`/series/${tmdbId}/seasons/${seasonNumber}`)
}

export function getSeriesProviders(tmdbId: number): Promise<SeriesProviders> {
  return apiFetch<SeriesProviders>(`/series/${tmdbId}/providers`)
}
