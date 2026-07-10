"""Tests del job diario de refresco (S3-1).

Se siembra una serie seguida con una temporada cacheada con fechas antiguas y se
verifica que el job fuerza el re-fetch de TMDB y actualiza las fechas de emisión.
"""

from datetime import UTC, date, datetime, timedelta

import httpx
import respx
from sqlalchemy.orm import Session

from app.jobs.refresh import refresh_followed_series
from app.models.episode import Episode
from app.models.series import Series
from app.models.user import User
from app.models.user_series import UserSeries
from app.services.tmdb_client import TMDBClient

BASE = "https://api.themoviedb.org/3"
TODAY = date.today()


async def _nosleep(_seconds: float) -> None:
    return None


def _make_client() -> TMDBClient:
    return TMDBClient(bearer_token="test", base_url=BASE, sleep=_nosleep)


def _seed_followed_series(db: Session, *, status: str = "Returning Series") -> None:
    """Serie con una temporada cacheada hace tiempo, seguida por un usuario."""
    old = datetime.now(UTC) - timedelta(days=10)
    user = User(email="u@example.com", password_hash="x")
    db.add(user)
    series = Series(
        tmdb_id=1,
        name="Demo",
        status=status,
        poster_path="/p.jpg",
        metadata_={"number_of_seasons": 1},
        cached_at=old,
    )
    db.add(series)
    db.flush()
    db.add(UserSeries(user_id=user.id, series_tmdb_id=1))
    # Episodio con fecha antigua/desconocida que el job debe actualizar.
    db.add(
        Episode(
            tmdb_id=102,
            series_tmdb_id=1,
            season_number=1,
            episode_number=2,
            name="Antiguo",
            air_date=None,
        )
    )
    db.commit()


def _mock_updated_tmdb(new_air_date: str) -> None:
    respx.get(f"{BASE}/tv/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Demo",
                "status": "Returning Series",
                "poster_path": "/p.jpg",
                "number_of_seasons": 1,
                "seasons": [{"season_number": 1, "name": "T1", "episode_count": 2}],
            },
        )
    )
    respx.get(f"{BASE}/tv/1/season/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "season_number": 1,
                "episodes": [
                    {"id": 101, "season_number": 1, "episode_number": 1, "air_date": "2022-01-01"},
                    {"id": 102, "season_number": 1, "episode_number": 2, "air_date": new_air_date},
                ],
            },
        )
    )


@respx.mock
async def test_job_refreshes_air_dates_of_followed_in_emission(db: Session) -> None:
    _seed_followed_series(db)
    new_date = (TODAY + timedelta(days=7)).isoformat()
    _mock_updated_tmdb(new_date)

    async with _make_client() as client:
        summary = await refresh_followed_series(db, client)

    assert summary == {"candidates": 1, "refreshed": 1, "failed": 0}
    # La fecha del episodio 102 se actualizó y se creó el 101.
    db.expire_all()
    assert db.get(Episode, 102).air_date == date.fromisoformat(new_date)
    assert db.get(Episode, 101) is not None


@respx.mock
async def test_job_skips_finished_series(db: Session) -> None:
    _seed_followed_series(db, status="Ended")
    route = respx.get(f"{BASE}/tv/1").mock(return_value=httpx.Response(200, json={"id": 1}))

    async with _make_client() as client:
        summary = await refresh_followed_series(db, client)

    assert summary == {"candidates": 0, "refreshed": 0, "failed": 0}
    assert route.call_count == 0
