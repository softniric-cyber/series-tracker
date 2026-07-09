"""Tests de la caché de series/episodios (S2-1).

Se prueban tanto el servicio (`series_cache`) de forma aislada con la BD y TMDB
mockeado (respx), como los endpoints `GET /series/{id}` y `.../seasons/{n}`. El
criterio clave: una segunda visita fresca NO vuelve a llamar a TMDB.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_tmdb_client
from app.main import app
from app.models.episode import Episode
from app.services.series_cache import get_season, get_series
from app.services.tmdb_client import TMDBClient, TMDBNotFoundError

BASE = "https://api.themoviedb.org/3"


async def _nosleep(_seconds: float) -> None:
    return None


def make_client() -> TMDBClient:
    return TMDBClient(bearer_token="test", base_url=BASE, sleep=_nosleep)


def _tv_payload(*, status: str = "Returning Series") -> dict[str, object]:
    return {
        "id": 95396,
        "name": "Separación",
        "original_name": "Severance",
        "status": status,
        "poster_path": "/poster.jpg",
        "overview": "Mark lidera un equipo...",
        "first_air_date": "2022-02-17",
        "last_air_date": "2025-03-21",
        "in_production": True,
        "number_of_seasons": 2,
        "number_of_episodes": 19,
        "genres": [{"id": 18, "name": "Drama"}, {"id": 9648, "name": "Misterio"}],
        "seasons": [
            {
                "season_number": 1,
                "name": "Temporada 1",
                "episode_count": 9,
                "air_date": "2022-02-17",
                "poster_path": "/s1.jpg",
            },
            {
                "season_number": 2,
                "name": "Temporada 2",
                "episode_count": 10,
                "air_date": "2025-01-17",
                "poster_path": "/s2.jpg",
            },
        ],
    }


def _season_payload() -> dict[str, object]:
    return {
        "season_number": 1,
        "name": "Temporada 1",
        "episodes": [
            {
                "id": 2354251,
                "season_number": 1,
                "episode_number": 1,
                "name": "Buenas noticias sobre el infierno",
                "air_date": "2022-02-17",
            },
            {
                "id": 2354252,
                "season_number": 1,
                "episode_number": 2,
                "name": "Media Loyalty",
                "air_date": "2022-02-18",
            },
        ],
    }


# --- Servicio: get_series -------------------------------------------------


@respx.mock
async def test_get_series_caches_and_second_visit_skips_tmdb(db: Session) -> None:
    route = respx.get(f"{BASE}/tv/95396").mock(return_value=httpx.Response(200, json=_tv_payload()))
    async with make_client() as client:
        first = await get_series(db, client, 95396, language="es-ES")
        assert first.name == "Separación"
        assert first.status == "Returning Series"
        second = await get_series(db, client, 95396, language="es-ES")
    assert second.tmdb_id == 95396
    # Segunda visita servida de la BD: TMDB se llamó una sola vez.
    assert route.call_count == 1


@respx.mock
async def test_get_series_refreshes_when_stale(db: Session) -> None:
    route = respx.get(f"{BASE}/tv/95396").mock(return_value=httpx.Response(200, json=_tv_payload()))
    async with make_client() as client:
        past = datetime.now(UTC) - timedelta(hours=25)
        await get_series(db, client, 95396, language="es-ES", now=past)
        # 25 h después caducó el TTL de 24 h (serie en emisión) → refresca.
        await get_series(db, client, 95396, language="es-ES", now=datetime.now(UTC))
    assert route.call_count == 2


@respx.mock
async def test_finished_series_uses_7_day_ttl(db: Session) -> None:
    route = respx.get(f"{BASE}/tv/95396").mock(
        return_value=httpx.Response(200, json=_tv_payload(status="Ended"))
    )
    async with make_client() as client:
        past = datetime.now(UTC) - timedelta(days=2)
        await get_series(db, client, 95396, language="es-ES", now=past)
        # 2 días < 7 días: sigue fresca, no llama a TMDB.
        await get_series(db, client, 95396, language="es-ES", now=datetime.now(UTC))
    assert route.call_count == 1


@respx.mock
async def test_get_series_not_found(db: Session) -> None:
    respx.get(f"{BASE}/tv/1").mock(return_value=httpx.Response(404, json={"status_code": 34}))
    async with make_client() as client:
        with pytest.raises(TMDBNotFoundError):
            await get_series(db, client, 1, language="es-ES")


# --- Servicio: get_season -------------------------------------------------


@respx.mock
async def test_get_season_caches_episodes(db: Session) -> None:
    respx.get(f"{BASE}/tv/95396").mock(return_value=httpx.Response(200, json=_tv_payload()))
    season_route = respx.get(f"{BASE}/tv/95396/season/1").mock(
        return_value=httpx.Response(200, json=_season_payload())
    )
    async with make_client() as client:
        _, episodes = await get_season(db, client, 95396, 1, language="es-ES")
        assert [e.episode_number for e in episodes] == [1, 2]
        assert episodes[0].air_date == datetime(2022, 2, 17).date()
        # Segunda visita: temporada fresca, no vuelve a TMDB.
        _, again = await get_season(db, client, 95396, 1, language="es-ES")
        assert len(again) == 2
    assert season_route.call_count == 1
    assert db.query(Episode).count() == 2


# --- Endpoints ------------------------------------------------------------


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


def test_series_detail_requires_auth(client: TestClient) -> None:
    assert client.get("/series/95396").status_code == 401


@respx.mock
def test_series_detail_endpoint(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    route = respx.get(f"{BASE}/tv/95396").mock(return_value=httpx.Response(200, json=_tv_payload()))
    resp = client.get("/series/95396", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["tmdb_id"] == 95396
    assert body["name"] == "Separación"
    assert body["poster_url"] == "https://image.tmdb.org/t/p/w342/poster.jpg"
    assert body["genres"] == ["Drama", "Misterio"]
    assert len(body["seasons"]) == 2
    assert body["seasons"][0]["poster_url"] == "https://image.tmdb.org/t/p/w342/s1.jpg"

    # Segunda visita: servida de caché, sin nueva llamada a TMDB.
    assert client.get("/series/95396", headers=headers).status_code == 200
    assert route.call_count == 1


@respx.mock
def test_series_detail_404(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/999").mock(return_value=httpx.Response(404, json={"status_code": 34}))
    assert client.get("/series/999", headers=headers).status_code == 404


@respx.mock
def test_season_detail_endpoint(client: TestClient, with_tmdb: None) -> None:
    headers = _auth_headers(client)
    respx.get(f"{BASE}/tv/95396").mock(return_value=httpx.Response(200, json=_tv_payload()))
    respx.get(f"{BASE}/tv/95396/season/1").mock(
        return_value=httpx.Response(200, json=_season_payload())
    )
    resp = client.get("/series/95396/seasons/1", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["series_tmdb_id"] == 95396
    assert body["season_number"] == 1
    assert body["name"] == "Temporada 1"
    assert [e["episode_number"] for e in body["episodes"]] == [1, 2]
    assert body["episodes"][0]["air_date"] == "2022-02-17"
