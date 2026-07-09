import { apiFetch } from './client'
import type { SeriesSearchResponse } from './types'

export function searchSeries(query: string, page = 1): Promise<SeriesSearchResponse> {
  const params = new URLSearchParams({ q: query, page: String(page) })
  return apiFetch<SeriesSearchResponse>(`/series/search?${params.toString()}`)
}
