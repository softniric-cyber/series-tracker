"""Tests del cliente TMDB. Todas las llamadas HTTP se mockean con respx; el
limitador se testea con un reloj falso (sin esperas reales)."""

import httpx
import pytest
import respx

from app.services.tmdb_client import (
    TMDBClient,
    TMDBError,
    TMDBNotFoundError,
    TokenBucket,
)

BASE = "https://api.themoviedb.org/3"


async def _nosleep(_seconds: float) -> None:
    return None


def make_client(**kwargs: object) -> TMDBClient:
    params: dict[str, object] = {
        "bearer_token": "test-token",
        "base_url": BASE,
        "backoff_base": 0.0,
        "sleep": _nosleep,
    }
    params.update(kwargs)
    return TMDBClient(**params)  # type: ignore[arg-type]


# --- TokenBucket -----------------------------------------------------------


class _FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.t += seconds


async def test_token_bucket_allows_burst_up_to_capacity() -> None:
    clock = _FakeClock()
    bucket = TokenBucket(rate=10, capacity=3, monotonic=clock.monotonic, sleep=clock.sleep)
    for _ in range(3):
        await bucket.acquire()
    assert clock.t == 0.0  # no ha tenido que esperar


async def test_token_bucket_throttles_when_empty() -> None:
    clock = _FakeClock()
    bucket = TokenBucket(rate=10, capacity=1, monotonic=clock.monotonic, sleep=clock.sleep)
    await bucket.acquire()  # consume el único token
    await bucket.acquire()  # debe esperar 1/10 s a que se rellene uno
    assert clock.t == pytest.approx(0.1)


# --- Peticiones y reintentos ----------------------------------------------


@respx.mock
async def test_search_tv_success() -> None:
    route = respx.get(f"{BASE}/search/tv").mock(
        return_value=httpx.Response(
            200, json={"page": 1, "results": [{"id": 95396, "name": "Severance"}]}
        )
    )
    async with make_client() as client:
        data = await client.search_tv("Severance")
    assert route.called
    assert data["results"][0]["name"] == "Severance"


@respx.mock
async def test_retries_on_500_then_succeeds() -> None:
    route = respx.get(f"{BASE}/tv/1").mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json={"id": 1, "name": "OK"})]
    )
    async with make_client() as client:
        data = await client.get_tv(1)
    assert data["id"] == 1
    assert route.call_count == 2


@respx.mock
async def test_retries_on_network_error() -> None:
    route = respx.get(f"{BASE}/search/tv").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.Response(200, json={"results": []})]
    )
    async with make_client() as client:
        data = await client.search_tv("x")
    assert data["results"] == []
    assert route.call_count == 2


@respx.mock
async def test_gives_up_after_max_retries() -> None:
    route = respx.get(f"{BASE}/tv/1").mock(return_value=httpx.Response(503))
    async with make_client(max_retries=2) as client:
        with pytest.raises(TMDBError):
            await client.get_tv(1)
    assert route.call_count == 3  # intento inicial + 2 reintentos


@respx.mock
async def test_404_raises_not_found_without_retry() -> None:
    route = respx.get(f"{BASE}/tv/999999").mock(return_value=httpx.Response(404, json={}))
    async with make_client() as client:
        with pytest.raises(TMDBNotFoundError):
            await client.get_tv(999999)
    assert route.call_count == 1


@respx.mock
async def test_non_retryable_status_raises_immediately() -> None:
    route = respx.get(f"{BASE}/tv/1").mock(return_value=httpx.Response(401, json={}))
    async with make_client() as client:
        with pytest.raises(TMDBError):
            await client.get_tv(1)
    assert route.call_count == 1


@respx.mock
async def test_season_and_providers_paths() -> None:
    season = respx.get(f"{BASE}/tv/1/season/2").mock(
        return_value=httpx.Response(200, json={"season_number": 2, "episodes": []})
    )
    providers = respx.get(f"{BASE}/tv/1/watch/providers").mock(
        return_value=httpx.Response(200, json={"results": {"ES": {}}})
    )
    async with make_client() as client:
        s = await client.get_tv_season(1, 2)
        p = await client.get_tv_watch_providers(1)
    assert season.called and providers.called
    assert s["season_number"] == 2
    assert "ES" in p["results"]
