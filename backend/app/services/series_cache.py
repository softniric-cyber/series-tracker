"""Caché-first de series y episodios (S2-1).

La ficha se sirve de la BD si está fresca; si no, se refresca de TMDB en la misma
petición y se actualiza la caché (arquitectura §5). TTL: 24 h por defecto, 7 días
para series finalizadas. La freshness de cada temporada se guarda por separado en
`series.metadata["_seasons_cached_at"]` para no reconsultar episodios ya cacheados.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.series import Series
from app.schemas.series import (
    EpisodeSummary,
    SeasonDetail,
    SeasonSummary,
    SeriesDetail,
)
from app.services.tmdb_client import TMDBClient

# Estados de TMDB en los que la serie ya no cambia (TTL largo, no se refresca en el job).
FINISHED_STATUSES = frozenset({"Ended", "Canceled", "Cancelled"})
_DEFAULT_TTL = timedelta(hours=24)
_FINISHED_TTL = timedelta(days=7)

_POSTER_SIZE = "w342"


def _ttl_for(status: str | None) -> timedelta:
    return _FINISHED_TTL if status in FINISHED_STATUSES else _DEFAULT_TTL


def _is_fresh(cached_at: datetime, status: str | None, now: datetime) -> bool:
    return now - cached_at < _ttl_for(status)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _image_url(image_base: str, path: str | None, size: str = _POSTER_SIZE) -> str | None:
    if not path:
        return None
    return f"{image_base.rstrip('/')}/{size}{path}"


def _extract_metadata(payload: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """Metadatos compactos que caben en el JSONB (arquitectura §10: caché acotada)."""
    seasons = [
        {
            "season_number": s["season_number"],
            "name": s.get("name"),
            "episode_count": s.get("episode_count"),
            "air_date": s.get("air_date") or None,
            "poster_path": s.get("poster_path"),
        }
        for s in payload.get("seasons") or []
        if s.get("season_number") is not None
    ]
    meta: dict[str, Any] = {
        "genres": [g["name"] for g in payload.get("genres") or [] if g.get("name")],
        "number_of_seasons": payload.get("number_of_seasons"),
        "number_of_episodes": payload.get("number_of_episodes"),
        "first_air_date": payload.get("first_air_date") or None,
        "last_air_date": payload.get("last_air_date") or None,
        "in_production": payload.get("in_production"),
        "seasons": seasons,
    }
    # Preservamos la freshness por temporada al refrescar la serie.
    if previous and previous.get("_seasons_cached_at"):
        meta["_seasons_cached_at"] = dict(previous["_seasons_cached_at"])
    return meta


def _upsert_series(db: Session, payload: dict[str, Any], now: datetime) -> Series:
    tmdb_id = int(payload["id"])
    series = db.get(Series, tmdb_id)
    previous = series.metadata_ if series is not None else None
    if series is None:
        series = Series(tmdb_id=tmdb_id)
        db.add(series)
    series.name = payload.get("name") or payload.get("original_name") or ""
    series.status = payload.get("status")
    series.poster_path = payload.get("poster_path")
    series.overview = payload.get("overview") or None
    series.metadata_ = _extract_metadata(payload, previous)
    series.cached_at = now
    db.commit()
    db.refresh(series)
    return series


async def get_series(
    db: Session,
    client: TMDBClient,
    tmdb_id: int,
    *,
    language: str,
    now: datetime | None = None,
    force: bool = False,
) -> Series:
    """Devuelve la serie desde la caché; llama a TMDB si falta, caduca o `force`."""
    now = now or datetime.now(UTC)
    series = db.get(Series, tmdb_id)
    if not force and series is not None and _is_fresh(series.cached_at, series.status, now):
        return series
    payload = await client.get_tv(tmdb_id, language=language)
    return _upsert_series(db, payload, now)


def _upsert_episodes(
    db: Session, series_tmdb_id: int, season_number: int, episodes: list[dict[str, Any]]
) -> None:
    for ep in episodes:
        ep_id = ep.get("id")
        if ep_id is None or ep.get("episode_number") is None:
            continue
        episode = db.get(Episode, int(ep_id))
        if episode is None:
            episode = Episode(tmdb_id=int(ep_id), series_tmdb_id=series_tmdb_id)
            db.add(episode)
        episode.series_tmdb_id = series_tmdb_id
        episode.season_number = int(ep.get("season_number") or season_number)
        episode.episode_number = int(ep["episode_number"])
        episode.name = ep.get("name") or None
        episode.air_date = _parse_date(ep.get("air_date"))


def _season_is_fresh(series: Series, season_number: int, now: datetime) -> bool:
    cached = (series.metadata_ or {}).get("_seasons_cached_at") or {}
    stamp = cached.get(str(season_number))
    if not stamp:
        return False
    try:
        cached_at = datetime.fromisoformat(stamp)
    except ValueError:
        return False
    return _is_fresh(cached_at, series.status, now)


def _mark_season_cached(series: Series, season_number: int, now: datetime) -> None:
    meta = dict(series.metadata_ or {})
    seasons_cached = dict(meta.get("_seasons_cached_at") or {})
    seasons_cached[str(season_number)] = now.isoformat()
    meta["_seasons_cached_at"] = seasons_cached
    # Reasignamos el dict entero: SQLAlchemy no rastrea mutaciones in-place del JSONB.
    series.metadata_ = meta


def _load_season_episodes(db: Session, series_tmdb_id: int, season_number: int) -> list[Episode]:
    stmt = (
        select(Episode)
        .where(
            Episode.series_tmdb_id == series_tmdb_id,
            Episode.season_number == season_number,
        )
        .order_by(Episode.episode_number)
    )
    return list(db.scalars(stmt))


async def get_season(
    db: Session,
    client: TMDBClient,
    tmdb_id: int,
    season_number: int,
    *,
    language: str,
    now: datetime | None = None,
    force: bool = False,
) -> tuple[Series, list[Episode]]:
    """Episodios de una temporada, caché-first; TMDB en miss/stale de la temporada o `force`."""
    now = now or datetime.now(UTC)
    series = await get_series(db, client, tmdb_id, language=language, now=now, force=force)
    if not force and _season_is_fresh(series, season_number, now):
        return series, _load_season_episodes(db, tmdb_id, season_number)
    payload = await client.get_tv_season(tmdb_id, season_number, language=language)
    _upsert_episodes(db, tmdb_id, season_number, payload.get("episodes") or [])
    _mark_season_cached(series, season_number, now)
    db.commit()
    db.refresh(series)
    return series, _load_season_episodes(db, tmdb_id, season_number)


def to_series_detail(series: Series, image_base: str) -> SeriesDetail:
    meta = series.metadata_ or {}
    seasons = [
        SeasonSummary(
            season_number=s["season_number"],
            name=s.get("name"),
            episode_count=s.get("episode_count"),
            air_date=s.get("air_date"),
            poster_url=_image_url(image_base, s.get("poster_path")),
        )
        for s in meta.get("seasons") or []
    ]
    return SeriesDetail(
        tmdb_id=series.tmdb_id,
        name=series.name,
        overview=series.overview,
        poster_url=_image_url(image_base, series.poster_path),
        status=series.status,
        first_air_date=meta.get("first_air_date"),
        last_air_date=meta.get("last_air_date"),
        genres=list(meta.get("genres") or []),
        number_of_seasons=meta.get("number_of_seasons"),
        number_of_episodes=meta.get("number_of_episodes"),
        in_production=meta.get("in_production"),
        seasons=seasons,
        cached_at=series.cached_at,
    )


def to_season_detail(
    series: Series,
    season_number: int,
    episodes: list[Episode],
    watched_ids: frozenset[int] = frozenset(),
) -> SeasonDetail:
    name = next(
        (
            s.get("name")
            for s in (series.metadata_ or {}).get("seasons") or []
            if s.get("season_number") == season_number
        ),
        None,
    )
    return SeasonDetail(
        series_tmdb_id=series.tmdb_id,
        season_number=season_number,
        name=name,
        episodes=[
            EpisodeSummary(
                tmdb_id=ep.tmdb_id,
                season_number=ep.season_number,
                episode_number=ep.episode_number,
                name=ep.name,
                air_date=ep.air_date,
                watched=ep.tmdb_id in watched_ids,
            )
            for ep in episodes
        ],
    )
