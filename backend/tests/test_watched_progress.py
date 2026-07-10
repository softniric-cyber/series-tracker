"""Tests de episodios vistos y progreso (S2-4).

TMDB se mockea con respx; la persistencia usa Postgres (fixture `client`). El
criterio clave: marcar una temporada completa actualiza el progreso al instante.
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
PAST = (TODAY - timedelta(days=30)).isoformat()
FUTURE = (TODAY + timedelta(days=30)).isoformat()


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
    """Serie con 2 temporadas: T1 con 2 eps emitidos, T2 con 1 emitido + 1 futuro."""
    respx.get(f"{BASE}/tv/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Demo",
                "status": "Returning Series",
                "number_of_seasons": 2,
                "seasons": [
                    {"season_number": 0, "name": "Especiales", "episode_count": 1},
                    {"season_number": 1, "name": "T1", "episode_count": 2},
                    {"season_number": 2, "name": "T2", "episode_count": 2},
                ],
            },
        )
    )
    respx.get(f"{BASE}/tv/1/season/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "season_number": 1,
                "episodes": [
                    {"id": 101, "season_number": 1, "episode_number": 1, "air_date": PAST},
                    {"id": 102, "season_number": 1, "episode_number": 2, "air_date": PAST},
                ],
            },
        )
    )
    respx.get(f"{BASE}/tv/1/season/2").mock(
        return_value=httpx.Response(
            200,
            json={
                "season_number": 2,
                "episodes": [
                    {"id": 201, "season_number": 2, "episode_number": 1, "air_date": PAST},
                    {"id": 202, "season_number": 2, "episode_number": 2, "air_date": FUTURE},
                ],
            },
        )
    )


def test_watched_requires_auth(client: TestClient) -> None:
    assert client.put("/me/episodes/101/watched").status_code == 401


@respx.mock
def test_progress_counts_only_aired_and_tracks_next(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_series()

    # Sin nada visto: 3 emitidos (101,102,201), 0 vistos, siguiente = 101.
    prog = client.get("/me/series/1/progress", headers=headers).json()
    assert prog["total_episodes"] == 3
    assert prog["watched_episodes"] == 0
    assert prog["next_episode"]["tmdb_id"] == 101

    # Marcar el primer episodio: siguiente pasa a 102.
    assert client.put("/me/episodes/101/watched", headers=headers).status_code == 204
    prog = client.get("/me/series/1/progress", headers=headers).json()
    assert prog["watched_episodes"] == 1
    assert prog["next_episode"]["tmdb_id"] == 102


@respx.mock
def test_mark_season_updates_progress_instantly(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_series()

    # Marcar T1 completa (criterio de aceptación).
    assert client.put("/me/series/1/seasons/1/watched", headers=headers).status_code == 204
    prog = client.get("/me/series/1/progress", headers=headers).json()
    assert prog["watched_episodes"] == 2  # 101 y 102
    assert prog["total_episodes"] == 3
    assert prog["next_episode"]["tmdb_id"] == 201  # primer emitido sin ver de T2

    # La temporada refleja los episodios vistos.
    season = client.get("/series/1/seasons/1", headers=headers).json()
    assert all(ep["watched"] for ep in season["episodes"])

    # Desmarcar la temporada revierte el progreso.
    assert client.delete("/me/series/1/seasons/1/watched", headers=headers).status_code == 204
    prog = client.get("/me/series/1/progress", headers=headers).json()
    assert prog["watched_episodes"] == 0


@respx.mock
def test_mark_all_aired_leaves_no_next(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_series()
    # Cachea todas las temporadas (necesario para marcar episodios sueltos).
    client.get("/me/series/1/progress", headers=headers)
    for ep in (101, 102, 201):
        assert client.put(f"/me/episodes/{ep}/watched", headers=headers).status_code == 204
    prog = client.get("/me/series/1/progress", headers=headers).json()
    assert prog["watched_episodes"] == 3
    assert prog["total_episodes"] == 3
    assert prog["next_episode"] is None  # el 202 aún no se ha emitido


@respx.mock
def test_unmark_and_idempotency(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_series()
    # Cachear la temporada para que exista el episodio.
    client.get("/series/1/seasons/1", headers=headers)

    assert client.put("/me/episodes/101/watched", headers=headers).status_code == 204
    # Marcar dos veces no falla.
    assert client.put("/me/episodes/101/watched", headers=headers).status_code == 204
    assert client.delete("/me/episodes/101/watched", headers=headers).status_code == 204
    # Desmarcar lo ya no visto es no-op.
    assert client.delete("/me/episodes/101/watched", headers=headers).status_code == 204


@respx.mock
def test_mark_uncached_episode_returns_404(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    assert client.put("/me/episodes/999999/watched", headers=headers).status_code == 404
