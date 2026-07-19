"""Baja de cuenta y exportación de datos (RGPD — S3-3).

El borrado elimina la fila de `users`; las FK con ON DELETE CASCADE arrastran
`user_series`, `watched_episodes` y `series_ratings`, de modo que no queda rastro
del usuario. La caché compartida (`series`/`episodes`) no es dato personal y se
conserva.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.series import Series
from app.models.series_rating import SeriesRating
from app.models.user import User
from app.models.user_series import UserSeries
from app.models.watched_episode import WatchedEpisode
from app.schemas.user import (
    ExportedFollowedSeries,
    ExportedRating,
    ExportedWatchedEpisode,
    UserDataExport,
    UserPublic,
)


def delete_user(db: Session, user: User) -> None:
    """Elimina el usuario y, en cascada, sus series seguidas y episodios vistos."""
    db.delete(user)
    db.commit()


def export_user_data(db: Session, user: User) -> UserDataExport:
    followed_stmt = (
        select(Series.tmdb_id, Series.name, UserSeries.added_at)
        .join(UserSeries, UserSeries.series_tmdb_id == Series.tmdb_id)
        .where(UserSeries.user_id == user.id)
        .order_by(UserSeries.added_at)
    )
    followed = [
        ExportedFollowedSeries(tmdb_id=tmdb_id, name=name, added_at=added_at)
        for tmdb_id, name, added_at in db.execute(followed_stmt).all()
    ]

    watched_stmt = (
        select(
            WatchedEpisode.episode_tmdb_id,
            Episode.series_tmdb_id,
            Episode.season_number,
            Episode.episode_number,
            WatchedEpisode.watched_at,
        )
        .join(Episode, Episode.tmdb_id == WatchedEpisode.episode_tmdb_id)
        .where(WatchedEpisode.user_id == user.id)
        .order_by(Episode.series_tmdb_id, Episode.season_number, Episode.episode_number)
    )
    watched = [
        ExportedWatchedEpisode(
            episode_tmdb_id=episode_tmdb_id,
            series_tmdb_id=series_tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
            watched_at=watched_at,
        )
        for episode_tmdb_id, series_tmdb_id, season_number, episode_number, watched_at in (
            db.execute(watched_stmt).all()
        )
    ]

    ratings_stmt = (
        select(Series.tmdb_id, Series.name, SeriesRating.score, SeriesRating.updated_at)
        .join(SeriesRating, SeriesRating.series_tmdb_id == Series.tmdb_id)
        .where(SeriesRating.user_id == user.id)
        .order_by(Series.name)
    )
    ratings = [
        ExportedRating(tmdb_id=tmdb_id, name=name, score=score, updated_at=updated_at)
        for tmdb_id, name, score, updated_at in db.execute(ratings_stmt).all()
    ]

    return UserDataExport(
        exported_at=datetime.now(UTC),
        profile=UserPublic.model_validate(user),
        followed_series=followed,
        watched_episodes=watched,
        ratings=ratings,
    )
