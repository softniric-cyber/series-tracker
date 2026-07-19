"""Esquemas de series: búsqueda (S1-4) y ficha/temporadas cacheadas (S2-1)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# Categoría de una serie seguida en «Mis series», según el progreso de visionado
# y si la serie tendrá nuevos episodios (ver `tracking.categorize`).
FollowedCategory = Literal["watching", "not_started", "up_to_date", "finished"]


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
    # Estado de seguimiento del usuario autenticado (S2-3).
    is_following: bool = False
    # Valoración global de TMDB. Opcionales porque las series cacheadas antes de
    # esta versión no las tienen en el JSONB hasta que caduque su TTL.
    vote_average: float | None = None
    vote_count: int | None = None
    # Puntuación del usuario autenticado (1-5); None si aún no la ha valorado.
    my_rating: int | None = None


class EpisodeSummary(BaseModel):
    tmdb_id: int
    season_number: int
    episode_number: int
    name: str | None
    air_date: date | None
    # Visto por el usuario autenticado (S2-4).
    watched: bool = False


class SeasonDetail(BaseModel):
    series_tmdb_id: int
    season_number: int
    name: str | None
    episodes: list[EpisodeSummary]


class SeasonProgress(BaseModel):
    """Progreso de una temporada, para marcarla como vista sin abrir el detalle.

    `episodes` cuenta todos los episodios no especiales cacheados de la temporada
    (emitidos o no); `aired` los ya emitidos (air_date ≤ hoy); `watched` los
    vistos entre los emitidos. `completed` es True cuando el usuario está «al día»
    con la temporada: hay episodios emitidos y todos están vistos.
    """

    season_number: int
    episodes: int
    aired: int
    watched: int
    completed: bool


class SeriesProgress(BaseModel):
    """Progreso de visionado de una serie (S2-4).

    `total_episodes` y `watched_episodes` cuentan solo episodios ya emitidos
    (air_date ≤ hoy) y no especiales. `next_episode` es el primer episodio
    emitido sin ver, en orden; None si no queda nada por ver. `seasons` desglosa
    la completitud por temporada (todos los episodios, para marcar «vista»).
    """

    tmdb_id: int
    total_episodes: int
    watched_episodes: int
    next_episode: EpisodeSummary | None
    seasons: list[SeasonProgress]


class FollowedSeries(BaseModel):
    """Serie que el usuario sigue, para la página «Mis series» (S2-3).

    `category` clasifica la serie según el progreso de visionado (En curso, Sin
    comenzar, Al día, Finalizada); `aired_episodes`/`watched_episodes` cuentan solo
    episodios emitidos y no especiales, con la misma semántica que `SeriesProgress`.
    """

    tmdb_id: int
    name: str
    poster_url: str | None
    status: str | None
    added_at: datetime
    category: FollowedCategory
    aired_episodes: int
    watched_episodes: int
    my_rating: int | None = None


class RatingInput(BaseModel):
    """Puntuación que envía el usuario: estrellas enteras de 1 a 5."""

    score: int = Field(ge=1, le=5)


class CalendarEntry(BaseModel):
    """Un episodio de una serie seguida que se emite en el rango consultado (S3-1)."""

    series_tmdb_id: int
    series_name: str
    poster_url: str | None
    episode_tmdb_id: int
    season_number: int
    episode_number: int
    episode_name: str | None
    air_date: date


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
