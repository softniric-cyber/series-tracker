"""Tests del perfil de usuario: PATCH /users/me (S1-2)."""

from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_tmdb_client
from app.main import app
from app.services.tmdb_client import TMDBClient

ME = "/users/me"
BASE = "https://api.themoviedb.org/3"


async def _nosleep(_seconds: float) -> None:
    return None


def _register(client: TestClient) -> dict[str, str]:
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


def test_patch_requires_authentication(client: TestClient) -> None:
    assert client.patch(ME, json={"country": "US"}).status_code == 401


def test_patch_updates_country_and_language(client: TestClient) -> None:
    headers = _register(client)
    resp = client.patch(ME, json={"country": "US", "language": "en-US"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["country"] == "US"
    assert body["language"] == "en-US"
    # Persiste: un GET posterior devuelve lo mismo.
    assert client.get(ME, headers=headers).json()["country"] == "US"


def test_patch_normalizes_case(client: TestClient) -> None:
    headers = _register(client)
    resp = client.patch(ME, json={"country": "us", "language": "EN-us"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["country"] == "US"
    assert body["language"] == "en-US"


def test_patch_partial_leaves_other_field(client: TestClient) -> None:
    headers = _register(client)
    client.patch(ME, json={"country": "FR", "language": "fr-FR"}, headers=headers)
    resp = client.patch(ME, json={"language": "de-DE"}, headers=headers)
    body = resp.json()
    assert body["country"] == "FR"  # intacto
    assert body["language"] == "de-DE"


def test_patch_rejects_invalid_country(client: TestClient) -> None:
    headers = _register(client)
    assert client.patch(ME, json={"country": "USA"}, headers=headers).status_code == 422


def test_patch_rejects_invalid_language(client: TestClient) -> None:
    headers = _register(client)
    assert client.patch(ME, json={"language": "spanish"}, headers=headers).status_code == 422


@respx.mock
def test_language_change_affects_tmdb_calls(client: TestClient, with_tmdb: None) -> None:
    headers = _register(client)
    route = respx.get(f"{BASE}/search/tv").mock(
        return_value=httpx.Response(200, json={"page": 1, "total_pages": 0, "results": []})
    )
    # Nuevo idioma en el perfil...
    client.patch(ME, json={"language": "en-US"}, headers=headers)
    # ...y la búsqueda debe pedir a TMDB con ese language.
    client.get("/series/search", params={"q": "Severance"}, headers=headers)
    assert route.calls.last.request.url.params["language"] == "en-US"
