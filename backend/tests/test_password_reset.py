"""Tests de recuperación de contraseña (S3-6).

`forgot-password` es anti-enumeración (200 exista o no el email) y encola el
envío del email solo si existe. `reset-password` valida el token stateless y su
huella (uso único de facto). El envío real se mockea.
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.api.auth as auth_api
from app.models.user import User
from app.services.security import create_reset_token


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> Iterator[AsyncMock]:
    """Sustituye el envío real por un mock que captura (email, enlace)."""
    mock = AsyncMock()
    monkeypatch.setattr(auth_api, "send_password_reset", mock)
    yield mock


def _register(
    client: TestClient, email: str = "u@example.com", password: str = "password123"
) -> None:
    client.post("/auth/register", json={"email": email, "password": password})


def _reset_token_for(db: Session, email: str) -> str:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return create_reset_token(str(user.id), user.password_hash)


def test_forgot_password_is_anti_enumeration(client: TestClient, sent_emails: AsyncMock) -> None:
    _register(client)
    # Email existente y no existente devuelven lo mismo (200).
    r1 = client.post("/auth/forgot-password", json={"email": "u@example.com"})
    r2 = client.post("/auth/forgot-password", json={"email": "nadie@example.com"})
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    # Pero solo se encola el email para el que existe.
    assert sent_emails.await_count == 1
    to_email, link = sent_emails.await_args.args
    assert to_email == "u@example.com"
    assert "/reset-password?token=" in link


def test_reset_password_changes_the_password(client: TestClient, db: Session) -> None:
    _register(client, password="oldpassword1")
    token = _reset_token_for(db, "u@example.com")

    resp = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "newpassword1"}
    )
    assert resp.status_code == 200

    # La antigua ya no vale; la nueva sí.
    assert (
        client.post(
            "/auth/login", json={"email": "u@example.com", "password": "oldpassword1"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "u@example.com", "password": "newpassword1"}
        ).status_code
        == 200
    )


def test_reset_token_is_single_use(client: TestClient, db: Session) -> None:
    _register(client, password="oldpassword1")
    token = _reset_token_for(db, "u@example.com")

    assert (
        client.post(
            "/auth/reset-password", json={"token": token, "new_password": "newpassword1"}
        ).status_code
        == 200
    )
    # Reutilizar el mismo enlace tras el cambio → inválido (la huella ya no coincide).
    assert (
        client.post(
            "/auth/reset-password", json={"token": token, "new_password": "another12345"}
        ).status_code
        == 400
    )


def test_reset_password_rejects_garbage_token(client: TestClient) -> None:
    assert (
        client.post(
            "/auth/reset-password", json={"token": "not-a-jwt", "new_password": "whatever12"}
        ).status_code
        == 400
    )


def test_reset_password_requires_min_length(client: TestClient) -> None:
    assert (
        client.post(
            "/auth/reset-password", json={"token": "x", "new_password": "short"}
        ).status_code
        == 422
    )
