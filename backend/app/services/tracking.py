"""Seguimiento de series por usuario (S2-3): seguir, dejar de seguir y listar.

La relación vive en la tabla `user_series`, cuya FK apunta a `series.tmdb_id`;
por eso seguir una serie exige que esté en la caché local, así que primero se
cachea con `series_cache.get_series` (que la trae de TMDB si hace falta).
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.series import Series
from app.models.user import User
from app.models.user_series import UserSeries
from app.schemas.series import FollowedSeries
from app.services.series_cache import get_series
from app.services.tmdb_client import TMDBClient

_POSTER_SIZE = "w342"


def _poster_url(image_base: str, path: str | None) -> str | None:
    if not path:
        return None
    return f"{image_base.rstrip('/')}/{_POSTER_SIZE}{path}"


def _pk(user_id: uuid.UUID, tmdb_id: int) -> dict[str, object]:
    return {"user_id": user_id, "series_tmdb_id": tmdb_id}


def is_following(db: Session, user_id: uuid.UUID, tmdb_id: int) -> bool:
    return db.get(UserSeries, _pk(user_id, tmdb_id)) is not None


async def follow_series(
    db: Session,
    client: TMDBClient,
    user: User,
    tmdb_id: int,
    *,
    language: str,
) -> tuple[Series, UserSeries]:
    """Sigue la serie (idempotente). Cachea la serie primero para respetar la FK."""
    series = await get_series(db, client, tmdb_id, language=language)
    link = db.get(UserSeries, _pk(user.id, tmdb_id))
    if link is None:
        link = UserSeries(user_id=user.id, series_tmdb_id=tmdb_id)
        db.add(link)
        db.commit()
        db.refresh(link)
    return series, link


def unfollow_series(db: Session, user: User, tmdb_id: int) -> None:
    """Deja de seguir la serie (idempotente: si no la seguía, no hace nada)."""
    link = db.get(UserSeries, _pk(user.id, tmdb_id))
    if link is not None:
        db.delete(link)
        db.commit()


def list_followed(db: Session, user: User) -> list[tuple[Series, datetime]]:
    """Series seguidas por el usuario, de la más reciente a la más antigua."""
    stmt = (
        select(Series, UserSeries.added_at)
        .join(UserSeries, UserSeries.series_tmdb_id == Series.tmdb_id)
        .where(UserSeries.user_id == user.id)
        .order_by(UserSeries.added_at.desc())
    )
    return [(series, added_at) for series, added_at in db.execute(stmt).all()]


def to_followed(series: Series, added_at: datetime, image_base: str) -> FollowedSeries:
    return FollowedSeries(
        tmdb_id=series.tmdb_id,
        name=series.name,
        poster_url=_poster_url(image_base, series.poster_path),
        status=series.status,
        added_at=added_at,
    )
