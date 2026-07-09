"""Tests de integración de los endpoints de autenticación."""

from fastapi.testclient import TestClient

REGISTER = "/auth/register"
LOGIN = "/auth/login"
REFRESH = "/auth/refresh"
ME = "/users/me"


def _register(client: TestClient, email: str = "user@example.com", password: str = "password123"):
    return client.post(REGISTER, json={"email": email, "password": password})


def test_register_returns_token_pair(client: TestClient) -> None:
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409


def test_register_normalizes_email_case(client: TestClient) -> None:
    assert _register(client, email="User@Example.com").status_code == 201
    # Mismo email en otra caja debe considerarse duplicado.
    assert _register(client, email="user@example.com").status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post(REGISTER, json={"email": "a@b.com", "password": "short"})
    assert resp.status_code == 422


def test_login_with_valid_credentials(client: TestClient) -> None:
    _register(client)
    resp = client.post(LOGIN, json={"email": "user@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password(client: TestClient) -> None:
    _register(client)
    resp = client.post(LOGIN, json={"email": "user@example.com", "password": "nope-nope-nope"})
    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    resp = client.post(LOGIN, json={"email": "ghost@example.com", "password": "whatever12"})
    assert resp.status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get(ME).status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    token = _register(client).json()["access_token"]
    resp = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert body["country"] == "ES"
    assert "password_hash" not in body


def test_me_rejects_invalid_token(client: TestClient) -> None:
    resp = client.get(ME, headers={"Authorization": "Bearer garbage.token.value"})
    assert resp.status_code == 401


def test_refresh_returns_new_tokens(client: TestClient) -> None:
    refresh_token = _register(client).json()["refresh_token"]
    resp = client.post(REFRESH, json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    # El nuevo access token debe servir para autenticarse.
    me = client.get(ME, headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_refresh_rejects_access_token(client: TestClient) -> None:
    access_token = _register(client).json()["access_token"]
    resp = client.post(REFRESH, json={"refresh_token": access_token})
    assert resp.status_code == 401


def test_refresh_rejects_garbage(client: TestClient) -> None:
    resp = client.post(REFRESH, json={"refresh_token": "not-a-token"})
    assert resp.status_code == 401
