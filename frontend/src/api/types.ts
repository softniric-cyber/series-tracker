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

export interface SeasonSummary {
  season_number: number
  name: string | null
  episode_count: number | null
  air_date: string | null
  poster_url: string | null
}

export interface SeriesDetail {
  tmdb_id: number
  name: string
  overview: string | null
  poster_url: string | null
  status: string | null
  first_air_date: string | null
  last_air_date: string | null
  genres: string[]
  number_of_seasons: number | null
  number_of_episodes: number | null
  in_production: boolean | null
  seasons: SeasonSummary[]
  cached_at: string
  is_following: boolean
}

export interface FollowedSeries {
  tmdb_id: number
  name: string
  poster_url: string | null
  status: string | null
  added_at: string
}

export interface EpisodeSummary {
  tmdb_id: number
  season_number: number
  episode_number: number
  name: string | null
  air_date: string | null
  watched: boolean
}

export interface SeasonProgress {
  season_number: number
  episodes: number
  aired: number
  watched: number
  completed: boolean
}

export interface SeriesProgress {
  tmdb_id: number
  total_episodes: number
  watched_episodes: number
  next_episode: EpisodeSummary | null
  seasons: SeasonProgress[]
}

export interface UserDataExport {
  exported_at: string
  profile: UserPublic
  followed_series: { tmdb_id: number; name: string; added_at: string }[]
  watched_episodes: {
    episode_tmdb_id: number
    series_tmdb_id: number
    season_number: number
    episode_number: number
    watched_at: string
  }[]
}

export interface CalendarEntry {
  series_tmdb_id: number
  series_name: string
  poster_url: string | null
  episode_tmdb_id: number
  season_number: number
  episode_number: number
  episode_name: string | null
  air_date: string
}

export interface SeasonDetail {
  series_tmdb_id: number
  season_number: number
  name: string | null
  episodes: EpisodeSummary[]
}

export interface WatchProvider {
  provider_id: number
  provider_name: string
  logo_url: string | null
  display_priority: number
}

export interface SeriesProviders {
  country: string
  link: string | null
  flatrate: WatchProvider[]
  rent: WatchProvider[]
  buy: WatchProvider[]
}
