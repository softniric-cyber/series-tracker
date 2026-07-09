"""Lógica de búsqueda de series: llama a TMDB y normaliza la respuesta.

Se mantiene separada del endpoint para poder testear el mapeo de forma aislada.
"""

from typing import Any

from app.schemas.series import SeriesSearchResponse, SeriesSearchResult
from app.services.tmdb_client import TMDBClient

_POSTER_SIZE = "w342"


def _image_url(image_base: str, path: str | None, size: str = _POSTER_SIZE) -> str | None:
    if not path:
        return None
    return f"{image_base.rstrip('/')}/{size}{path}"


def _to_result(raw: dict[str, Any], image_base: str) -> SeriesSearchResult:
    return SeriesSearchResult(
        tmdb_id=raw["id"],
        name=raw.get("name") or raw.get("original_name") or "",
        overview=raw.get("overview") or None,
        poster_url=_image_url(image_base, raw.get("poster_path")),
        # TMDB devuelve "" cuando no hay fecha; lo normalizamos a None.
        first_air_date=(raw.get("first_air_date") or None),
        vote_average=raw.get("vote_average"),
    )


async def search_series(
    client: TMDBClient,
    *,
    query: str,
    page: int,
    language: str,
    image_base: str,
) -> SeriesSearchResponse:
    data = await client.search_tv(query, page=page, language=language)
    raw_results = data.get("results") or []
    results = [_to_result(item, image_base) for item in raw_results if item.get("id") is not None]
    return SeriesSearchResponse(
        query=query,
        page=int(data.get("page", page)),
        total_pages=int(data.get("total_pages", 0)),
        total_results=int(data.get("total_results", len(results))),
        results=results,
    )
