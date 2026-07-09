export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserPublic {
  id: string
  email: string
  display_name: string | null
  country: string
  language: string
  created_at: string
}

export interface SeriesSearchResult {
  tmdb_id: number
  name: string
  overview: string | null
  poster_url: string | null
  first_air_date: string | null
  vote_average: number | null
}

export interface SeriesSearchResponse {
  query: string
  page: number
  total_pages: number
  total_results: number
  results: SeriesSearchResult[]
}
