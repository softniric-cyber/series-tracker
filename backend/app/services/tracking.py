"""Seguimiento de series por usuario (S2-3): seguir, dejar de seguir y listar.

La relación vive en la tabla `user_series`, cuya FK apunta a `series.tmdb_id`;
por eso seguir una serie exige que esté en la caché local, así que primero se
cachea con `series_cache.get_series` (que la trae de TMDB si hace falta).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.series import Series
from app.models.user import User
from app.models.user_series import UserSeries
from app.models.watched_episode import WatchedEpisode
from app.schemas.series import EpisodeSummary, FollowedSeries, SeriesProgress
from app.services.series_cache import get_season, get_series
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


# --- Episodios vistos y progreso (S2-4) -----------------------------------


def _watched_ids_for_series(db: Session, user_id: uuid.UUID, tmdb_id: int) -> set[int]:
    stmt = (
        select(WatchedEpisode.episode_tmdb_id)
        .join(Episode, Episode.tmdb_id == WatchedEpisode.episode_tmdb_id)
        .where(WatchedEpisode.user_id == user_id, Episode.series_tmdb_id == tmdb_id)
    )
    return set(db.scalars(stmt))


def watched_ids_for_season(
    db: Session, user_id: uuid.UUID, tmdb_id: int, season_number: int
) -> frozenset[int]:
    stmt = (
        select(WatchedEpisode.episode_tmdb_id)
        .join(Episode, Episode.tmdb_id == WatchedEpisode.episode_tmdb_id)
        .where(
            WatchedEpisode.user_id == user_id,
            Episode.series_tmdb_id == tmdb_id,
            Episode.season_number == season_number,
        )
    )
    return frozenset(db.scalars(stmt))


def mark_episode_watched(db: Session, user: User, episode_id: int) -> bool:
    """Marca un episodio como visto (idempotente). False si no está cacheado."""
    if db.get(Episode, episode_id) is None:
        return False
    pk = {"user_id": user.id, "episode_tmdb_id": episode_id}
    if db.get(WatchedEpisode, pk) is None:
        db.add(WatchedEpisode(user_id=user.id, episode_tmdb_id=episode_id))
        db.commit()
    return True


def unmark_episode_watched(db: Session, user: User, episode_id: int) -> None:
    row = db.get(WatchedEpisode, {"user_id": user.id, "episode_tmdb_id": episode_id})
    if row is not None:
        db.delete(row)
        db.commit()


async def mark_season_watched(
    db: Session,
    client: TMDBClient,
    user: User,
    tmdb_id: int,
    season_number: int,
    *,
    language: str,
) -> None:
    """Marca todos los episodios de una temporada como vistos (los cachea primero)."""
    _, episodes = await get_season(db, client, tmdb_id, season_number, language=language)
    existing = watched_ids_for_season(db, user.id, tmdb_id, season_number)
    added = False
    for ep in episodes:
        if ep.tmdb_id not in existing:
            db.add(WatchedEpisode(user_id=user.id, episode_tmdb_id=ep.tmdb_id))
            added = True
    if added:
        db.commit()


async def unmark_season_watched(
    db: Session,
    client: TMDBClient,
    user: User,
    tmdb_id: int,
    season_number: int,
    *,
    language: str,
) -> None:
    await get_season(db, client, tmdb_id, season_number, language=language)
    ids = watched_ids_for_season(db, user.id, tmdb_id, season_number)
    if ids:
        for episode_id in ids:
            row = db.get(WatchedEpisode, {"user_id": user.id, "episode_tmdb_id": episode_id})
            if row is not None:
                db.delete(row)
        db.commit()


async def get_progress(
    db: Session,
    client: TMDBClient,
    user: User,
    tmdb_id: int,
    *,
    language: str,
) -> SeriesProgress:
    """Progreso sobre episodios emitidos y no especiales; cachea todas las temporadas."""
    series = await get_series(db, client, tmdb_id, language=language)
    number_of_seasons = (series.metadata_ or {}).get("number_of_seasons") or 0
    for season_number in range(1, int(number_of_seasons) + 1):
        await get_season(db, client, tmdb_id, season_number, language=language)

    stmt = (
        select(Episode)
        .where(Episode.series_tmdb_id == tmdb_id, Episode.season_number >= 1)
        .order_by(Episode.season_number, Episode.episode_number)
    )
    episodes = list(db.scalars(stmt))
    watched = _watched_ids_for_series(db, user.id, tmdb_id)
    today = date.today()

    aired = [ep for ep in episodes if ep.air_date is not None and ep.air_date <= today]
    next_episode = next(
        (
            EpisodeSummary(
                tmdb_id=ep.tmdb_id,
                season_number=ep.season_number,
                episode_number=ep.episode_number,
                name=ep.name,
                air_date=ep.air_date,
                watched=False,
            )
            for ep in aired
            if ep.tmdb_id not in watched
        ),
        None,
    )
    return SeriesProgress(
        tmdb_id=tmdb_id,
        total_episodes=len(aired),
        watched_episodes=sum(1 for ep in aired if ep.tmdb_id in watched),
        next_episode=next_episode,
    )
