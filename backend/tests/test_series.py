"""Tests de integración del endpoint de búsqueda de series.

La autenticación usa la BD (fixture `client`); TMDB se mockea con respx y se
inyecta el cliente sobreescribiendo la dependencia `get_tmdb_client`.
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
SEARCH = "/series/search"


async def _nosleep(_seconds: float) -> None:
    return None


def _auth_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/auth/register", json={"email": "u@example.com", "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def with_tmdb() -> Iterator[None]:
    tmdb = TMDBClient(bearer_token="test", base_url=BASE, sleep=_nosleep)
    app.dependency_overrides[get_tmdb_client] = lambda: tmdb
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_tmdb_client, None)


def test_search_requires_authentication(client: TestClient) -> None:
    assert client.get(SEARCH, params={"q": "Severance"}).status_code == 401


def test_search_requires_query_param(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    assert client.get(SEARCH, headers=headers).status_code == 422


@respx.mock
def test_search_returns_normalized_results(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/search/tv").mock(
        return_value=httpx.Response(
            200,
            json={
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {
                        "id": 95396,
                        "name": "Separación",
                        "overview": "Mark lidera un equipo...",
                        "poster_path": "/abc.jpg",
                        "first_air_date": "2022-02-17",
                        "vote_average": 8.4,
                    }
                ],
            },
        )
    )
    resp = client.get(SEARCH, params={"q": "Severance"}, headers=headers)
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "private, max-age=300"
    body = resp.json()
    assert body["total_results"] == 1
    result = body["results"][0]
    assert result["tmdb_id"] == 95396
    assert result["name"] == "Separación"
    assert result["poster_url"] == "https://image.tmdb.org/t/p/w342/abc.jpg"
    assert result["first_air_date"] == "2022-02-17"


@respx.mock
def test_search_normalizes_missing_fields(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/search/tv").mock(
        return_value=httpx.Response(
            200,
            json={
                "page": 1,
                "total_pages": 1,
                "total_results": 1,
                "results": [
                    {"id": 1, "name": "Sin póster", "poster_path": None, "first_air_date": ""}
                ],
            },
        )
    )
    resp = client.get(SEARCH, params={"q": "x"}, headers=headers)
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["poster_url"] is None
    assert result["first_air_date"] is None


@respx.mock
def test_search_empty_results(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/search/tv").mock(
        return_value=httpx.Response(
            200, json={"page": 1, "total_pages": 0, "total_results": 0, "results": []}
        )
    )
    resp = client.get(SEARCH, params={"q": "asdkjhasd"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["results"] == []
