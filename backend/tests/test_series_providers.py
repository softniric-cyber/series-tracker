"""Tests del endpoint GET /series/{id}/providers ("dónde verla", S2-2).

Los watch providers de TMDB no se cachean; el filtrado por país se hace en el
servidor con el país del perfil (usuario recién registrado → country="ES").
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


def _auth_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/auth/register", json={"email": "u@example.com", "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _providers_payload() -> dict[str, object]:
    return {
        "id": 95396,
        "results": {
            "ES": {
                "link": "https://www.themoviedb.org/tv/95396/watch?locale=ES",
                "flatrate": [
                    {
                        "logo_path": "/apple.jpg",
                        "provider_id": 350,
                        "provider_name": "Apple TV+",
                        "display_priority": 5,
                    },
                    {
                        "logo_path": "/movistar.jpg",
                        "provider_id": 149,
                        "provider_name": "Movistar Plus+",
                        "display_priority": 2,
                    },
                ],
                "rent": [
                    {
                        "logo_path": "/rent.jpg",
                        "provider_id": 3,
                        "provider_name": "Google Play",
                        "display_priority": 1,
                    }
                ],
            },
            "US": {
                "link": "https://www.themoviedb.org/tv/95396/watch?locale=US",
                "flatrate": [
                    {
                        "logo_path": "/apple.jpg",
                        "provider_id": 350,
                        "provider_name": "Apple TV+",
                        "display_priority": 1,
                    }
                ],
            },
        },
    }


def test_providers_requires_auth(client: TestClient) -> None:
    assert client.get("/series/95396/providers").status_code == 401


@respx.mock
def test_providers_filtered_by_profile_country(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/95396/watch/providers").mock(
        return_value=httpx.Response(200, json=_providers_payload())
    )
    resp = client.get("/series/95396/providers", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["country"] == "ES"
    assert body["link"].endswith("locale=ES")
    # Ordenado por display_priority: Movistar (2) antes que Apple (5).
    assert [p["provider_name"] for p in body["flatrate"]] == ["Movistar Plus+", "Apple TV+"]
    assert body["flatrate"][0]["logo_url"] == "https://image.tmdb.org/t/p/w92/movistar.jpg"
    assert [p["provider_name"] for p in body["rent"]] == ["Google Play"]
    assert body["buy"] == []


@respx.mock
def test_providers_country_not_available(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/95396/watch/providers").mock(
        return_value=httpx.Response(200, json={"id": 95396, "results": {"FR": {"link": "x"}}})
    )
    resp = client.get("/series/95396/providers", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["country"] == "ES"
    assert body["link"] is None
    assert body["flatrate"] == []
    assert body["rent"] == []
    assert body["buy"] == []


@respx.mock
def test_providers_not_found(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/999/watch/providers").mock(
        return_value=httpx.Response(404, json={"status_code": 34})
    )
    assert client.get("/series/999/providers", headers=headers).status_code == 404
