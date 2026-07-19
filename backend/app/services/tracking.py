"""Seguimiento de series por usuario (S2-3): seguir, dejar de seguir y listar.

La relación vive en la tabla `user_series`, cuya FK apunta a `series.tmdb_id`;
por eso seguir una serie exige que esté en la caché local, así que primero se
cachea con `series_cache.get_series` (que la trae de TMDB si hace falta).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.series import Series
from app.models.user import User
from app.models.user_series import UserSeries
from app.models.watched_episode import WatchedEpisode
from app.schemas.series import (
    CalendarEntry,
    EpisodeSummary,
    FollowedCategory,
    FollowedSeries,
    SeasonProgress,
    SeriesProgress,
)
from app.services import ratings
from app.services.series_cache import (
    FINISHED_STATUSES,
    ensure_seasons_cached,
    get_season,
    get_series,
)
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


def categorize(status: str | None, total: int, aired: int, watched: int) -> FollowedCategory:
    """Clasifica una serie seguida según su progreso de visionado.

    - «not_started»: no se ha visto ningún episodio emitido.
    - «watching»: hay episodios emitidos sin ver (queda algo por ver ahora).
    - «up_to_date»: al día con lo emitido, pero habrá nuevos episodios (la serie no
      ha finalizado o hay episodios futuros ya cacheados).
    - «finished»: al día y la serie terminó (no habrá nuevas temporadas).

    Los conteos usan solo episodios emitidos y no especiales; `total` incluye además
    los no emitidos ya cacheados, para detectar contenido futuro conocido.
    """
    if watched == 0:
        return "not_started"
    if watched < aired:
        return "watching"
    # watched >= aired: el usuario ha visto todo lo emitido.
    more_coming = status not in FINISHED_STATUSES or total > aired
    return "up_to_date" if more_coming else "finished"


def _episode_counts(db: Session, user_id: uuid.UUID) -> dict[int, tuple[int, int]]:
    """Por serie seguida: (total episodios no especiales cacheados, ya emitidos)."""
    today = date.today()
    stmt = (
        select(
            Episode.series_tmdb_id,
            func.count().label("total"),
            func.count()
            .filter(Episode.air_date.is_not(None), Episode.air_date <= today)
            .label("aired"),
        )
        .join(UserSeries, UserSeries.series_tmdb_id == Episode.series_tmdb_id)
        .where(UserSeries.user_id == user_id, Episode.season_number >= 1)
        .group_by(Episode.series_tmdb_id)
    )
    return {row.series_tmdb_id: (row.total, row.aired) for row in db.execute(stmt)}


def _watched_aired_counts(db: Session, user_id: uuid.UUID) -> dict[int, int]:
    """Por serie: nº de episodios emitidos y no especiales que el usuario ha visto."""
    today = date.today()
    stmt = (
        select(Episode.series_tmdb_id, func.count())
        .join(WatchedEpisode, WatchedEpisode.episode_tmdb_id == Episode.tmdb_id)
        .where(
            WatchedEpisode.user_id == user_id,
            Episode.season_number >= 1,
            Episode.air_date.is_not(None),
            Episode.air_date <= today,
        )
        .group_by(Episode.series_tmdb_id)
    )
    return {series_tmdb_id: count for series_tmdb_id, count in db.execute(stmt)}


def to_followed(
    series: Series,
    added_at: datetime,
    image_base: str,
    total: int = 0,
    aired: int = 0,
    watched: int = 0,
    my_rating: int | None = None,
) -> FollowedSeries:
    return FollowedSeries(
        tmdb_id=series.tmdb_id,
        name=series.name,
        poster_url=_poster_url(image_base, series.poster_path),
        status=series.status,
        added_at=added_at,
        category=categorize(series.status, total, aired, watched),
        aired_episodes=aired,
        watched_episodes=watched,
        my_rating=my_rating,
    )


def list_my_series(db: Session, user: User, image_base: str) -> list[FollowedSeries]:
    """Series seguidas con su categoría y progreso, sin llamar a TMDB (solo caché)."""
    counts = _episode_counts(db, user.id)
    watched = _watched_aired_counts(db, user.id)
    # Todas las puntuaciones de una vez: una consulta en lugar de una por serie.
    scores = ratings.ratings_for_user(db, user.id)
    result = []
    for series, added_at in list_followed(db, user):
        total, aired = counts.get(series.tmdb_id, (0, 0))
        result.append(
            to_followed(
                series,
                added_at,
                image_base,
                total,
                aired,
                watched.get(series.tmdb_id, 0),
                scores.get(series.tmdb_id),
            )
        )
    return result


def followed_with_progress(
    db: Session, user: User, series: Series, added_at: datetime, image_base: str
) -> FollowedSeries:
    """Un único `FollowedSeries` con su categoría, para la respuesta de seguir."""
    total, aired = _episode_counts(db, user.id).get(series.tmdb_id, (0, 0))
    watched = _watched_aired_counts(db, user.id).get(series.tmdb_id, 0)
    my_rating = ratings.get_rating(db, user.id, series.tmdb_id)
    return to_followed(series, added_at, image_base, total, aired, watched, my_rating)


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
    number_of_seasons = int((series.metadata_ or {}).get("number_of_seasons") or 0)
    if number_of_seasons:
        await ensure_seasons_cached(
            db, client, tmdb_id, range(1, number_of_seasons + 1), language=language
        )

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

    # Completitud por temporada, con la misma semántica «al día» que la barra de
    # progreso: una temporada se marca cuando todos sus episodios EMITIDOS están
    # vistos. `episodes` incluye los no emitidos solo para distinguir en la UI una
    # temporada terminada («Vista») de una al día pero con estrenos pendientes.
    season_total: dict[int, int] = {}
    season_aired: dict[int, int] = {}
    season_watched: dict[int, int] = {}
    for ep in episodes:
        season_total[ep.season_number] = season_total.get(ep.season_number, 0) + 1
    for ep in aired:
        season_aired[ep.season_number] = season_aired.get(ep.season_number, 0) + 1
        if ep.tmdb_id in watched:
            season_watched[ep.season_number] = season_watched.get(ep.season_number, 0) + 1
    seasons = [
        SeasonProgress(
            season_number=n,
            episodes=total,
            aired=season_aired.get(n, 0),
            watched=season_watched.get(n, 0),
            completed=season_aired.get(n, 0) > 0
            and season_watched.get(n, 0) == season_aired.get(n, 0),
        )
        for n, total in sorted(season_total.items())
    ]

    return SeriesProgress(
        tmdb_id=tmdb_id,
        total_episodes=len(aired),
        watched_episodes=sum(1 for ep in aired if ep.tmdb_id in watched),
        next_episode=next_episode,
        seasons=seasons,
    )


# --- Calendario (S3-1) ----------------------------------------------------


def list_calendar(
    db: Session, user: User, start: date, end: date, image_base: str
) -> list[CalendarEntry]:
    """Episodios de las series seguidas por el usuario que se emiten en [start, end]."""
    stmt = (
        select(Episode, Series)
        .join(Series, Series.tmdb_id == Episode.series_tmdb_id)
        .join(UserSeries, UserSeries.series_tmdb_id == Episode.series_tmdb_id)
        .where(
            UserSeries.user_id == user.id,
            Episode.season_number >= 1,
            Episode.air_date.is_not(None),
            Episode.air_date >= start,
            Episode.air_date <= end,
        )
        .order_by(Episode.air_date, Episode.season_number, Episode.episode_number)
    )
    entries = []
    for episode, series in db.execute(stmt).all():
        assert episode.air_date is not None  # garantizado por el WHERE
        entries.append(
            CalendarEntry(
                series_tmdb_id=series.tmdb_id,
                series_name=series.name,
                poster_url=_poster_url(image_base, series.poster_path),
                episode_tmdb_id=episode.tmdb_id,
                season_number=episode.season_number,
                episode_number=episode.episode_number,
                episode_name=episode.name,
                air_date=episode.air_date,
            )
        )
    return entries
