"""Tests de RGPD: exportación de datos y baja de cuenta (S3-3).

El criterio clave: DELETE /users/me elimina todo rastro del usuario (perfil,
series seguidas y episodios vistos), mientras que la caché compartida se conserva.
"""

from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_tmdb_client
from app.main import app
from app.models.series import Series
from app.models.user import User
from app.models.user_series import UserSeries
from app.models.watched_episode import WatchedEpisode
from app.services.tmdb_client import TMDBClient

BASE = "https://api.themoviedb.org/3"


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


def _auth_headers(client: TestClient, email: str = "u@example.com") -> dict[str, str]:
    token = client.post("/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _mock_series_and_season() -> None:
    respx.get(f"{BASE}/tv/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Demo",
                "status": "Returning Series",
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
                    {"id": 102, "season_number": 1, "episode_number": 2, "air_date": "2022-01-08"},
                ],
            },
        )
    )


def _seed_user_with_data(client: TestClient) -> dict[str, str]:
    headers = _auth_headers(client)
    client.post("/me/series/1", headers=headers)
    client.get("/series/1/seasons/1", headers=headers)  # cachea los episodios
    client.put("/me/episodes/101/watched", headers=headers)
    return headers


@respx.mock
def test_export_returns_all_user_data(client: TestClient, with_tmdb: None) -> None:
    _mock_series_and_season()
    headers = _seed_user_with_data(client)

    body = client.get("/users/me/export", headers=headers).json()
    assert body["profile"]["email"] == "u@example.com"
    assert [s["tmdb_id"] for s in body["followed_series"]] == [1]
    assert [w["episode_tmdb_id"] for w in body["watched_episodes"]] == [101]
    assert "exported_at" in body


@respx.mock
def test_delete_me_removes_all_traces(client: TestClient, with_tmdb: None, db: Session) -> None:
    _mock_series_and_season()
    headers = _seed_user_with_data(client)

    # Estado sembrado.
    assert db.scalar(select(func.count()).select_from(UserSeries)) == 1
    assert db.scalar(select(func.count()).select_from(WatchedEpisode)) == 1
    assert db.scalar(select(func.count()).select_from(User)) == 1

    assert client.delete("/users/me", headers=headers).status_code == 204

    # No queda rastro del usuario ni de sus datos…
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(UserSeries)) == 0
    assert db.scalar(select(func.count()).select_from(WatchedEpisode)) == 0
    # …pero la caché compartida se conserva.
    assert db.scalar(select(func.count()).select_from(Series)) == 1

    # El token deja de servir (el usuario ya no existe).
    assert client.get("/users/me", headers=headers).status_code == 401


def test_export_requires_auth(client: TestClient) -> None:
    assert client.get("/users/me/export").status_code == 401


def test_delete_requires_auth(client: TestClient) -> None:
    assert client.delete("/users/me").status_code == 401
