"""Puntuación personal de series (1-5 estrellas).

La tabla `series_ratings` tiene FK a `series.tmdb_id`, así que puntuar exige que
la serie esté en la caché local: `set_rating` la cachea primero con
`series_cache.get_series`, igual que hace seguir en `tracking.follow_series`.

Puntuar es independiente de seguir: se puede valorar una serie que ya terminaste
y no sigues.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.series import Series
from app.models.series_rating import SeriesRating
from app.models.user import User
from app.services.series_cache import get_series
from app.services.tmdb_client import TMDBClient

MIN_SCORE = 1
MAX_SCORE = 5


def _pk(user_id: uuid.UUID, tmdb_id: int) -> dict[str, object]:
    return {"user_id": user_id, "series_tmdb_id": tmdb_id}


def get_rating(db: Session, user_id: uuid.UUID, tmdb_id: int) -> int | None:
    rating = db.get(SeriesRating, _pk(user_id, tmdb_id))
    return rating.score if rating is not None else None


def ratings_for_user(db: Session, user_id: uuid.UUID) -> dict[int, int]:
    """Todas las puntuaciones del usuario, por tmdb_id (para listados)."""
    stmt = select(SeriesRating.series_tmdb_id, SeriesRating.score).where(
        SeriesRating.user_id == user_id
    )
    return {row.series_tmdb_id: row.score for row in db.execute(stmt)}


async def set_rating(
    db: Session,
    client: TMDBClient,
    user: User,
    tmdb_id: int,
    score: int,
    *,
    language: str,
) -> tuple[Series, int]:
    """Crea o actualiza la puntuación (idempotente). Cachea la serie por la FK."""
    series = await get_series(db, client, tmdb_id, language=language)
    rating = db.get(SeriesRating, _pk(user.id, tmdb_id))
    if rating is None:
        rating = SeriesRating(user_id=user.id, series_tmdb_id=tmdb_id, score=score)
        db.add(rating)
    else:
        rating.score = score
    db.commit()
    db.refresh(rating)
    return series, rating.score


def delete_rating(db: Session, user: User, tmdb_id: int) -> None:
    """Quita la puntuación (idempotente: si no la había, no hace nada)."""
    rating = db.get(SeriesRating, _pk(user.id, tmdb_id))
    if rating is not None:
        db.delete(rating)
        db.commit()
