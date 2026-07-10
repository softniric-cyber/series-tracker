"""Endpoints de series: búsqueda vía TMDB (S1-4) y ficha/temporadas cacheadas (S2-1)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.api.deps import CurrentUser, DbSession, TmdbClient
from app.core.config import get_settings
from app.schemas.series import (
    SeasonDetail,
    SeriesDetail,
    SeriesProviders,
    SeriesSearchResponse,
)
from app.services import tracking
from app.services.series import build_series_providers, search_series
from app.services.series_cache import (
    get_season,
    get_series,
    to_season_detail,
    to_series_detail,
)
from app.services.tmdb_client import TMDBNotFoundError

router = APIRouter(prefix="/series", tags=["series"])


@router.get("/search", response_model=SeriesSearchResponse)
async def search(
    current_user: CurrentUser,
    client: TmdbClient,
    q: Annotated[str, Query(min_length=1, max_length=100, description="Texto a buscar")],
    page: Annotated[int, Query(ge=1, le=500)] = 1,
) -> SeriesSearchResponse:
    return await search_series(
        client,
        query=q,
        page=page,
        language=current_user.language,
        image_base=get_settings().tmdb_image_base_url,
    )


@router.get("/{tmdb_id}", response_model=SeriesDetail)
async def series_detail(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> SeriesDetail:
    try:
        series = await get_series(db, client, tmdb_id, language=current_user.language)
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie no encontrada"
        ) from exc
    detail = to_series_detail(series, get_settings().tmdb_image_base_url)
    detail.is_following = tracking.is_following(db, current_user.id, tmdb_id)
    return detail


@router.get("/{tmdb_id}/seasons/{season_number}", response_model=SeasonDetail)
async def season_detail(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
    season_number: Annotated[int, Path(ge=0)],
) -> SeasonDetail:
    try:
        series, episodes = await get_season(
            db, client, tmdb_id, season_number, language=current_user.language
        )
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie o temporada no encontrada"
        ) from exc
    watched = tracking.watched_ids_for_season(db, current_user.id, tmdb_id, season_number)
    return to_season_detail(series, season_number, episodes, watched)


@router.get("/{tmdb_id}/providers", response_model=SeriesProviders)
async def series_providers(
    current_user: CurrentUser,
    client: TmdbClient,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> SeriesProviders:
    try:
        payload = await client.get_tv_watch_providers(tmdb_id)
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie no encontrada"
        ) from exc
    return build_series_providers(
        payload,
        country=current_user.country,
        image_base=get_settings().tmdb_image_base_url,
    )
