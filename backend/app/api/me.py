"""Endpoints «Mis series»: seguir, dejar de seguir y listar (S2-3)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from app.api.deps import CurrentUser, DbSession, TmdbClient
from app.core.config import get_settings
from app.schemas.series import FollowedSeries
from app.services import tracking
from app.services.tmdb_client import TMDBNotFoundError

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/series", response_model=list[FollowedSeries])
def list_my_series(current_user: CurrentUser, db: DbSession) -> list[FollowedSeries]:
    image_base = get_settings().tmdb_image_base_url
    return [
        tracking.to_followed(series, added_at, image_base)
        for series, added_at in tracking.list_followed(db, current_user)
    ]


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
    return tracking.to_followed(series, link.added_at, get_settings().tmdb_image_base_url)


@router.delete("/series/{tmdb_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_series(
    current_user: CurrentUser,
    db: DbSession,
    tmdb_id: Annotated[int, Path(ge=1)],
) -> None:
    tracking.unfollow_series(db, current_user, tmdb_id)
