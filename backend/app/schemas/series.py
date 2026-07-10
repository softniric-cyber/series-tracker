"""Esquemas de series: búsqueda (S1-4) y ficha/temporadas cacheadas (S2-1)."""

from datetime import date, datetime

from pydantic import BaseModel


class SeriesSearchResult(BaseModel):
    tmdb_id: int
    name: str
    overview: str | None
    poster_url: str | None
    first_air_date: str | None
    vote_average: float | None


class SeriesSearchResponse(BaseModel):
    query: str
    page: int
    total_pages: int
    total_results: int
    results: list[SeriesSearchResult]


class SeasonSummary(BaseModel):
    """Resumen de una temporada tal como aparece en la ficha de la serie."""

    season_number: int
    name: str | None
    episode_count: int | None
    air_date: str | None
    poster_url: str | None


class SeriesDetail(BaseModel):
    """Ficha de una serie servida desde la caché local (caché-first)."""

    tmdb_id: int
    name: str
    overview: str | None
    poster_url: str | None
    status: str | None
    first_air_date: str | None
    last_air_date: str | None
    genres: list[str]
    number_of_seasons: int | None
    number_of_episodes: int | None
    in_production: bool | None
    seasons: list[SeasonSummary]
    cached_at: datetime


class EpisodeSummary(BaseModel):
    tmdb_id: int
    season_number: int
    episode_number: int
    name: str | None
    air_date: date | None


class SeasonDetail(BaseModel):
    series_tmdb_id: int
    season_number: int
    name: str | None
    episodes: list[EpisodeSummary]


class WatchProvider(BaseModel):
    provider_id: int
    provider_name: str
    logo_url: str | None
    display_priority: int


class SeriesProviders(BaseModel):
    """Dónde ver la serie según el país del perfil (TMDB watch/providers)."""

    country: str
    link: str | None
    flatrate: list[WatchProvider]
    rent: list[WatchProvider]
    buy: list[WatchProvider]
