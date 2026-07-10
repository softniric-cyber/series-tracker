"""Lógica de búsqueda de series: llama a TMDB y normaliza la respuesta.

Se mantiene separada del endpoint para poder testear el mapeo de forma aislada.
"""

from typing import Any

from app.schemas.series import (
    SeriesProviders,
    SeriesSearchResponse,
    SeriesSearchResult,
    WatchProvider,
)
from app.services.tmdb_client import TMDBClient

_POSTER_SIZE = "w342"
_LOGO_SIZE = "w92"


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


def _to_provider(raw: dict[str, Any], image_base: str) -> WatchProvider:
    return WatchProvider(
        provider_id=raw["provider_id"],
        provider_name=raw.get("provider_name") or "",
        logo_url=_image_url(image_base, raw.get("logo_path"), size=_LOGO_SIZE),
        display_priority=raw.get("display_priority", 0),
    )


def build_series_providers(
    payload: dict[str, Any], *, country: str, image_base: str
) -> SeriesProviders:
    """Filtra los watch providers de TMDB por país y ordena por prioridad.

    TMDB devuelve `results` con una entrada por país (ISO-2); si el país del
    perfil no está, se devuelve una estructura vacía (no es un error).
    """
    entry = (payload.get("results") or {}).get(country) or {}

    def category(key: str) -> list[WatchProvider]:
        items = [
            _to_provider(p, image_base)
            for p in entry.get(key) or []
            if p.get("provider_id") is not None
        ]
        return sorted(items, key=lambda p: p.display_priority)

    return SeriesProviders(
        country=country,
        link=entry.get("link"),
        flatrate=category("flatrate"),
        rent=category("rent"),
        buy=category("buy"),
    )
