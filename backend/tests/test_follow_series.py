"""Tests de «Mis series» (S2-3): seguir, dejar de seguir y listar.

TMDB se mockea con respx; la persistencia usa Postgres (fixture `client`). Seguir
una serie la cachea primero (respeta la FK user_series → series).
"""

from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_tmdb_client
from app.main import app
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


def _tv_payload(tmdb_id: int = 95396, name: str = "Separación") -> dict[str, object]:
    return {
        "id": tmdb_id,
        "name": name,
        "status": "Returning Series",
        "poster_path": "/poster.jpg",
        "overview": "…",
        "seasons": [],
    }


def _mock_tv(tmdb_id: int = 95396, name: str = "Separación") -> None:
    respx.get(f"{BASE}/tv/{tmdb_id}").mock(
        return_value=httpx.Response(200, json=_tv_payload(tmdb_id, name))
    )


def test_my_series_requires_auth(client: TestClient) -> None:
    assert client.get("/me/series").status_code == 401


@respx.mock
def test_follow_list_and_unfollow(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_tv()

    # Al principio no sigue nada.
    assert client.get("/me/series", headers=headers).json() == []

    # Seguir.
    resp = client.post("/me/series/95396", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["tmdb_id"] == 95396
    assert body["name"] == "Separación"
    assert body["poster_url"] == "https://image.tmdb.org/t/p/w342/poster.jpg"

    # La lista ahora la contiene.
    listed = client.get("/me/series", headers=headers).json()
    assert [s["tmdb_id"] for s in listed] == [95396]

    # La ficha refleja el estado de seguimiento.
    detail = client.get("/series/95396", headers=headers).json()
    assert detail["is_following"] is True

    # Dejar de seguir.
    assert client.delete("/me/series/95396", headers=headers).status_code == 204
    assert client.get("/me/series", headers=headers).json() == []
    assert client.get("/series/95396", headers=headers).json()["is_following"] is False


@respx.mock
def test_follow_is_idempotent(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_tv()
    assert client.post("/me/series/95396", headers=headers).status_code == 201
    # Seguir dos veces no duplica ni falla.
    assert client.post("/me/series/95396", headers=headers).status_code == 201
    assert len(client.get("/me/series", headers=headers).json()) == 1


@respx.mock
def test_unfollow_when_not_following_is_noop(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    assert client.delete("/me/series/95396", headers=headers).status_code == 204


@respx.mock
def test_follow_unknown_series_returns_404(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/999").mock(return_value=httpx.Response(404, json={"status_code": 34}))
    assert client.post("/me/series/999", headers=headers).status_code == 404


@respx.mock
def test_lists_are_isolated_per_user(client: TestClient, with_tmdb: None) -> None:
    _mock_tv()
    _mock_tv(1399, "Juego de Tronos")
    alice = _auth_headers(client, "alice@example.com")
    bob = _auth_headers(client, "bob@example.com")

    client.post("/me/series/95396", headers=alice)
    client.post("/me/series/1399", headers=bob)

    assert [s["tmdb_id"] for s in client.get("/me/series", headers=alice).json()] == [95396]
    assert [s["tmdb_id"] for s in client.get("/me/series", headers=bob).json()] == [1399]
