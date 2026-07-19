"""Endpoints «Mis series»: seguir, dejar de seguir y listar (S2-3)."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.api.deps import CurrentUser, DbSession, TmdbClient
from app.core.config import get_settings
from app.schemas.series import (
    CalendarEntry,
    FollowedSeries,
    RatingInput,
    SeriesProgress,
)
from app.services import ratings, tracking
from app.services.tmdb_client import TMDBNotFoundError

router = APIRouter(prefix="/me", tags=["me"])

# Tope del rango del calendario para evitar consultas desmedidas.
_MAX_CALENDAR_DAYS = 366


@router.get("/series", response_model=list[FollowedSeries])
def list_my_series(current_user: CurrentUser, db: DbSession) -> list[FollowedSeries]:
    return tracking.list_my_series(db, current_user, get_settings().tmdb_image_base_url)


@router.post(
    "/series/{tmdb_id}",
    response_model=FollowedSeries,
    status_code=status.HTTP_201_CREATED,
)
async def follow_series(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> FollowedSeries:
    try:
        series, link = await tracking.follow_series(
            db, client, current_user, tmdb_id, language=current_user.language
        )
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie no encontrada"
        ) from exc
    return tracking.followed_with_progress(
        db, current_user, series, link.added_at, get_settings().tmdb_image_base_url
    )


@router.delete("/series/{tmdb_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_series(
    current_user: CurrentUser,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> None:
    tracking.unfollow_series(db, current_user, tmdb_id)


# --- Puntuación personal ---------------------------------------------------


@router.put("/series/{tmdb_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
async def rate_series(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    payload: RatingInput,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> None:
    """Puntúa la serie de 1 a 5 estrellas (idempotente; sobrescribe la anterior).

    No exige seguir la serie: se puede valorar algo que ya terminaste.
    """
    try:
        await ratings.set_rating(
            db, client, current_user, tmdb_id, payload.score, language=current_user.language
        )
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie no encontrada"
        ) from exc


@router.delete("/series/{tmdb_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
def unrate_series(
    current_user: CurrentUser,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> None:
    ratings.delete_rating(db, current_user, tmdb_id)


# --- Episodios vistos y progreso (S2-4) -----------------------------------


@router.put("/episodes/{episode_id}/watched", status_code=status.HTTP_204_NO_CONTENT)
def mark_episode_watched(
    current_user: CurrentUser,
    db: DbSession,
    episode_id: Annotated[int, Path(ge=1)],
) -> None:
    if not tracking.mark_episode_watched(db, current_user, episode_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episodio no encontrado")


@router.delete("/episodes/{episode_id}/watched", status_code=status.HTTP_204_NO_CONTENT)
def unmark_episode_watched(
    current_user: CurrentUser,
    db: DbSession,
    episode_id: Annotated[int, Path(ge=1)],
) -> None:
    tracking.unmark_episode_watched(db, current_user, episode_id)


@router.put(
    "/series/{tmdb_id}/seasons/{season_number}/watched", status_code=status.HTTP_204_NO_CONTENT
)
async def mark_season_watched(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
    season_number: Annotated[int, Path(ge=0)],
) -> None:
    try:
        await tracking.mark_season_watched(
            db, client, current_user, tmdb_id, season_number, language=current_user.language
        )
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie o temporada no encontrada"
        ) from exc


@router.delete(
    "/series/{tmdb_id}/seasons/{season_number}/watched",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unmark_season_watched(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
    season_number: Annotated[int, Path(ge=0)],
) -> None:
    try:
        await tracking.unmark_season_watched(
            db, client, current_user, tmdb_id, season_number, language=current_user.language
        )
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie o temporada no encontrada"
        ) from exc


@router.get("/calendar", response_model=list[CalendarEntry])
def calendar(
    current_user: CurrentUser,
    db: DbSession,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: Annotated[date | None, Query()] = None,
) -> list[CalendarEntry]:
    start = from_ or date.today()
    end = to or start + timedelta(days=30)
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="«to» no puede ser anterior a «from»"
        )
    if (end - start).days > _MAX_CALENDAR_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rango no puede superar {_MAX_CALENDAR_DAYS} días",
        )
    return tracking.list_calendar(db, current_user, start, end, get_settings().tmdb_image_base_url)


@router.get("/series/{tmdb_id}/progress", response_model=SeriesProgress)
async def series_progress(
    current_user: CurrentUser,
    client: TmdbClient,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> SeriesProgress:
    try:
        return await tracking.get_progress(
            db, client, current_user, tmdb_id, language=current_user.language
        )
    except TMDBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serie no encontrada"
        ) from exc
