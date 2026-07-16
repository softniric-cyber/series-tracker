"""Job diario de refresco de series (S3-1).

Refresca desde TMDB todas las series **en emisión** que algún usuario sigue, para
mantener al día las fechas de emisión de episodios futuros (el calendario es una
consulta a BD, así que no depende del tráfico). Se invoca desde un cron de GitHub
Actions (06:00 UTC) con `python -m app.jobs.refresh`.
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.series import Series
from app.models.user_series import UserSeries
from app.services.series_cache import FINISHED_STATUSES, ensure_seasons_cached, get_series
from app.services.tmdb_client import TMDBClient, TMDBError

# Idioma con el que se cachea en el job (la caché es compartida, un solo idioma).
_REFRESH_LANGUAGE = "es-ES"


def _followed_in_emission(db: Session) -> list[Series]:
    """Series seguidas por algún usuario que aún no han terminado."""
    stmt = select(Series).join(UserSeries, UserSeries.series_tmdb_id == Series.tmdb_id).distinct()
    return [s for s in db.scalars(stmt) if s.status not in FINISHED_STATUSES]


async def refresh_followed_series(
    db: Session, client: TMDBClient, *, now: datetime | None = None
) -> dict[str, int]:
    """Fuerza el refresco de cada serie en emisión seguida y de sus temporadas."""
    now = now or datetime.now(UTC)
    series_list = _followed_in_emission(db)
    refreshed = 0
    failed = 0
    for series in series_list:
        tmdb_id = series.tmdb_id
        try:
            fresh = await get_series(
                db, client, tmdb_id, language=_REFRESH_LANGUAGE, now=now, force=True
            )
            number_of_seasons = int((fresh.metadata_ or {}).get("number_of_seasons") or 0)
            if number_of_seasons:
                await ensure_seasons_cached(
                    db,
                    client,
                    tmdb_id,
                    range(1, number_of_seasons + 1),
                    language=_REFRESH_LANGUAGE,
                    now=now,
                    force=True,
                )
            refreshed += 1
        except TMDBError:
            # Una serie que falla no debe abortar el job entero.
            failed += 1
    return {"candidates": len(series_list), "refreshed": refreshed, "failed": failed}


async def _amain() -> dict[str, int]:
    db = SessionLocal()
    async with TMDBClient() as client:
        try:
            return await refresh_followed_series(db, client)
        finally:
            db.close()


def main() -> None:
    summary = asyncio.run(_amain())
    print(f"[refresh] {summary}")


if __name__ == "__main__":
    main()
