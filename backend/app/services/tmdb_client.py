"""Cliente asíncrono de TMDB con reintentos y limitador de tasa.

Especificación (arquitectura §5): `httpx.AsyncClient`, timeout 10 s, 3 reintentos
con backoff exponencial y limitador propio (token bucket, margen sobre el límite
de TMDB). Las llamadas aceptan `language`/`watch_region` del perfil del usuario.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.core.config import get_settings

# Estados que merece la pena reintentar (transitorios): throttling y errores 5xx.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class TMDBError(Exception):
    """Fallo al comunicarse con TMDB (tras agotar reintentos o error no recuperable)."""


class TMDBNotFoundError(TMDBError):
    """El recurso solicitado no existe en TMDB (404)."""


async def _default_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


class TokenBucket:
    """Limitador de tasa por *token bucket*.

    Se rellenan `rate` tokens por segundo hasta `capacity` (ráfaga máxima). Cada
    petición consume un token; si no hay, `acquire()` espera lo justo. El reloj y
    el `sleep` son inyectables para poder testear el comportamiento sin esperas reales.
    """

    def __init__(
        self,
        rate: float,
        capacity: float,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = _default_sleep,
    ) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._monotonic = monotonic
        self._sleep = sleep
        self._updated = monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._monotonic()
        elapsed = now - self._updated
        self._updated = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
                await self._sleep(wait)
                self._refill()
            self._tokens -= 1


class TMDBClient:
    """Cliente fino sobre la API v3 de TMDB."""

    def __init__(
        self,
        *,
        bearer_token: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        rate: float = 40.0,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = _default_sleep,
    ) -> None:
        settings = get_settings()
        base = (base_url if base_url is not None else settings.tmdb_base_url).rstrip("/") + "/"
        token = bearer_token if bearer_token is not None else settings.tmdb_bearer_token
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._bucket = TokenBucket(rate, rate)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base,
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "TMDBClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._bucket.acquire()
            try:
                response = await self._client.get(path, params=params)
            except httpx.RequestError as exc:  # red/timeout: reintentable
                last_error = exc
            else:
                if response.status_code == 404:
                    raise TMDBNotFoundError(path)
                if response.status_code not in _RETRYABLE_STATUS:
                    if not response.is_success:
                        raise TMDBError(f"TMDB {response.status_code} for {path}")
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise TMDBError(f"Unexpected TMDB payload for {path}")
                    return payload
                last_error = TMDBError(f"TMDB {response.status_code} for {path}")

            if attempt < self._max_retries:
                await self._sleep(self._backoff_base * (2**attempt))

        raise TMDBError(
            f"TMDB request failed after {self._max_retries} retries: {path}"
        ) from last_error

    async def search_tv(
        self, query: str, *, page: int = 1, language: str = "es-ES"
    ) -> dict[str, Any]:
        return await self._request(
            "search/tv", {"query": query, "page": page, "language": language}
        )

    async def get_tv(self, tmdb_id: int, *, language: str = "es-ES") -> dict[str, Any]:
        return await self._request(f"tv/{tmdb_id}", {"language": language})

    async def get_tv_season(
        self, tmdb_id: int, season_number: int, *, language: str = "es-ES"
    ) -> dict[str, Any]:
        return await self._request(f"tv/{tmdb_id}/season/{season_number}", {"language": language})

    async def get_tv_watch_providers(self, tmdb_id: int) -> dict[str, Any]:
        return await self._request(f"tv/{tmdb_id}/watch/providers")
