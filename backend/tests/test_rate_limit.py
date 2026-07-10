"""Test del rate limiting en auth (S3-4).

El limitador está desactivado para el resto de tests (conftest); aquí se reactiva
y se resetea su almacenamiento para comprobar que login bloquea tras superar el
límite por IP con un 429.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.ratelimit import limiter


@pytest.fixture
def rate_limiting_on() -> Iterator[None]:
    limiter.reset()
    limiter.enabled = True
    try:
        yield
    finally:
        limiter.enabled = False
        limiter.reset()


def test_login_is_rate_limited_per_ip(client: TestClient, rate_limiting_on: None) -> None:
    limit = int(get_settings().rate_limit_login.split("/")[0])  # p. ej. "10/minute" → 10
    creds = {"email": "nobody@example.com", "password": "whatever"}

    # Hasta el límite: credenciales inválidas → 401 (pero cuentan para el límite).
    for _ in range(limit):
        assert client.post("/auth/login", json=creds).status_code == 401

    # La siguiente petición supera el límite → 429.
    assert client.post("/auth/login", json=creds).status_code == 429


def test_limiter_disabled_by_default(client: TestClient) -> None:
    # Sin el fixture, el limitador está apagado: muchos intentos no dan 429.
    creds = {"email": "nobody@example.com", "password": "whatever"}
    for _ in range(30):
        assert client.post("/auth/login", json=creds).status_code == 401
