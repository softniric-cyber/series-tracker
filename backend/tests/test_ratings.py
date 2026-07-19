"""Tests de la puntuación personal (1-5 estrellas).

TMDB se mockea con respx; la persistencia usa Postgres (fixture `client`).
Puntuar cachea la serie primero (respeta la FK series_ratings → series).
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


def _mock_tv(tmdb_id: int = 95396) -> None:
    payload = {
        "id": tmdb_id,
        "name": "Separación",
        "status": "Returning Series",
        "poster_path": "/poster.jpg",
        "overview": "…",
        "seasons": [],
    }
    respx.get(f"{BASE}/tv/{tmdb_id}").mock(return_value=httpx.Response(200, json=payload))


def test_rating_requires_auth(client: TestClient) -> None:
    assert client.put("/me/series/95396/rating", json={"score": 4}).status_code == 401


@respx.mock
def test_rate_update_and_delete(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_tv()

    # Sin puntuar, la ficha la devuelve vacía.
    assert client.get("/series/95396", headers=headers).json()["my_rating"] is None

    assert (
        client.put("/me/series/95396/rating", json={"score": 4}, headers=headers).status_code == 204
    )
    assert client.get("/series/95396", headers=headers).json()["my_rating"] == 4

    # Volver a puntuar sobrescribe en vez de duplicar.
    assert (
        client.put("/me/series/95396/rating", json={"score": 2}, headers=headers).status_code == 204
    )
    assert client.get("/series/95396", headers=headers).json()["my_rating"] == 2

    # Quitar la puntuación es idempotente.
    assert client.delete("/me/series/95396/rating", headers=headers).status_code == 204
    assert client.delete("/me/series/95396/rating", headers=headers).status_code == 204
    assert client.get("/series/95396", headers=headers).json()["my_rating"] is None


@respx.mock
@pytest.mark.parametrize("score", [0, 6, -1])
def test_rating_rejects_out_of_range(client: TestClient, with_tmdb: None, score: int) -> None:
    headers = _auth_headers(client)
    _mock_tv()
    resp = client.put("/me/series/95396/rating", json={"score": score}, headers=headers)
    assert resp.status_code == 422


@respx.mock
def test_rating_is_independent_of_following(client: TestClient, with_tmdb: None) -> None:
    """Se puede puntuar una serie sin seguirla."""
    headers = _auth_headers(client)
    _mock_tv()

    client.put("/me/series/95396/rating", json={"score": 5}, headers=headers)
    detail = client.get("/series/95396", headers=headers).json()
    assert detail["my_rating"] == 5
    assert detail["is_following"] is False
    # Y no aparece en «Mis series», que solo lista lo seguido.
    assert client.get("/me/series", headers=headers).json() == []


@respx.mock
def test_rating_appears_in_my_series(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_tv()

    client.post("/me/series/95396", headers=headers)
    client.put("/me/series/95396/rating", json={"score": 3}, headers=headers)

    listed = client.get("/me/series", headers=headers).json()
    assert [s["my_rating"] for s in listed] == [3]


@respx.mock
def test_rating_unknown_series_is_404(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/1").mock(return_value=httpx.Response(404, json={}))
    resp = client.put("/me/series/1/rating", json={"score": 4}, headers=headers)
    assert resp.status_code == 404


@respx.mock
def test_ratings_are_per_user(client: TestClient, with_tmdb: None) -> None:
    _mock_tv()
    alice = _auth_headers(client, "alice@example.com")
    bob = _auth_headers(client, "bob@example.com")

    client.put("/me/series/95396/rating", json={"score": 5}, headers=alice)

    assert client.get("/series/95396", headers=alice).json()["my_rating"] == 5
    assert client.get("/series/95396", headers=bob).json()["my_rating"] is None


@respx.mock
def test_rating_included_in_gdpr_export(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    _mock_tv()
    client.put("/me/series/95396/rating", json={"score": 4}, headers=headers)

    export = client.get("/users/me/export", headers=headers).json()
    assert [(r["tmdb_id"], r["score"]) for r in export["ratings"]] == [(95396, 4)]


@respx.mock
def test_ratings_deleted_with_account(client: TestClient, with_tmdb: None) -> None:
    """La baja RGPD debe arrastrar las puntuaciones (FK ON DELETE CASCADE)."""
    headers = _auth_headers(client)
    _mock_tv()
    client.put("/me/series/95396/rating", json={"score": 4}, headers=headers)

    assert client.delete("/users/me", headers=headers).status_code == 204

    # La serie sigue en la caché compartida, pero un usuario nuevo no ve nota.
    fresh = _auth_headers(client, "otro@example.com")
    assert client.get("/series/95396", headers=fresh).json()["my_rating"] is None
