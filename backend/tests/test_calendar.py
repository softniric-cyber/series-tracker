"""Tests del endpoint GET /me/calendar (S3-1).

El calendario es una consulta pura a BD: episodios de las series seguidas con
air_date en el rango. Se siembra la caché vía respx + follow + progress.
"""

from collections.abc import Iterator
from datetime import date, timedelta

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_tmdb_client
from app.main import app
from app.services.tmdb_client import TMDBClient

BASE = "https://api.themoviedb.org/3"
TODAY = date.today()
D = lambda days: (TODAY + timedelta(days=days)).isoformat()  # noqa: E731


async def _nosleep(_seconds: float) -> None:
    return None


@pytest.fixture
def with_tmdb() -> Iterator[None]:
    tmdb = TMDBClient(bearer_token="test", base_url=BASE, sleep=_nosleep)
    app.dependency_overrides[get_tmdb_client] = lambda: tmdb
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_tmdb_client, None)


def _auth_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/auth/register", json={"email": "u@example.com", "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _mock_series() -> None:
    respx.get(f"{BASE}/tv/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Demo",
                "status": "Returning Series",
                "poster_path": "/p.jpg",
                "number_of_seasons": 1,
                "seasons": [{"season_number": 1, "name": "T1", "episode_count": 3}],
            },
        )
    )
    respx.get(f"{BASE}/tv/1/season/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "season_number": 1,
                "episodes": [
                    {"id": 101, "season_number": 1, "episode_number": 1, "air_date": D(-40)},
                    {"id": 102, "season_number": 1, "episode_number": 2, "air_date": D(5)},
                    {"id": 103, "season_number": 1, "episode_number": 3, "air_date": D(60)},
                ],
            },
        )
    )


def test_calendar_requires_auth(client: TestClient) -> None:
    assert client.get("/me/calendar").status_code == 401


@respx.mock
def test_calendar_returns_upcoming_episodes_of_followed_series(
    client: TestClient, with_tmdb: None
) -> None:
    headers = _auth_headers(client)
    _mock_series()
    client.post("/me/series/1", headers=headers)
    # Cachea los episodios (en producción lo hace el job diario).
    client.get("/me/series/1/progress", headers=headers)

    # Rango por defecto (hoy .. +30 días): solo el episodio a +5 días.
    body = client.get("/me/calendar", headers=headers).json()
    assert [e["episode_tmdb_id"] for e in body] == [102]
    entry = body[0]
    assert entry["series_name"] == "Demo"
    assert entry["poster_url"] == "https://image.tmdb.org/t/p/w342/p.jpg"
    assert entry["air_date"] == D(5)

    # Rango amplio incluye el de +60 días pero nunca el pasado (-40).
    wide = client.get("/me/calendar", headers=headers, params={"to": D(90)}).json()
    assert [e["episode_tmdb_id"] for e in wide] == [102, 103]


@respx.mock
def test_calendar_only_shows_followed_series(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_series()
    # Cacheamos la serie y sus episodios SIN seguirla (vía la ficha).
    client.get("/series/1/seasons/1", headers=headers)
    assert client.get("/me/calendar", headers=headers, params={"to": D(90)}).json() == []


def test_calendar_rejects_inverted_range(client: TestClient) -> None:
    # Requiere auth; usamos un registro directo.
    token = client.post(
        "/auth/register", json={"email": "a@b.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/me/calendar", headers=headers, params={"from": D(10), "to": D(1)})
    assert resp.status_code == 400
