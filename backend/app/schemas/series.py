"""Esquemas de búsqueda de series (respuesta normalizada al frontend)."""

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
