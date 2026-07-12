"""Tests del login con Google (POST /auth/google).

El verificador del ID token de Google se sobreescribe con una dependencia falsa
para no llamar a Google: cada test decide qué identidad devuelve (o si falla).
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_google_verifier
from app.main import app
from app.services.google_auth import GoogleIdentity, GoogleTokenError, verify_google_token

GOOGLE = "/auth/google"


def test_verify_rejects_when_not_configured() -> None:
    # Sin client ID configurado, el verificador rechaza sin llamar a Google.
    with pytest.raises(GoogleTokenError):
        verify_google_token("whatever", client_id="")


def test_verify_rejects_malformed_credential() -> None:
    # Un token que no es un JWT válido falla antes de contactar con Google.
    with pytest.raises(GoogleTokenError):
        verify_google_token("not-a-jwt", client_id="some-client-id.apps.googleusercontent.com")


# --- Verificación criptográfica real (RS256) sin llamar a Google -----------
#
# Firmamos un ID token con un par RSA propio y sustituimos SOLO el cliente JWKS
# por uno que devuelve nuestra clave pública. Así se ejercita jwt.decode real y
# las comprobaciones de audiencia/emisor/email_verified.

_CLIENT_ID = "test-client.apps.googleusercontent.com"


def _make_token_and_key(**overrides: object) -> tuple[str, object]:
    import time

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": _CLIENT_ID,
        "sub": "g-real-1",
        "email": "carol@gmail.com",
        "email_verified": True,
        "name": "Carol",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    token = jwt.encode(claims, key, algorithm="RS256")
    return token, key.public_key()


def _patch_jwks(monkeypatch: pytest.MonkeyPatch, public_key: object) -> None:
    import app.services.google_auth as ga

    class _Stub:
        def get_signing_key_from_jwt(self, _credential: str) -> object:
            return type("_K", (), {"key": public_key})()

    monkeypatch.setattr(ga, "_jwk_client", _Stub())


def test_verify_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token, public_key = _make_token_and_key()
    _patch_jwks(monkeypatch, public_key)
    identity = verify_google_token(token, client_id=_CLIENT_ID)
    assert (identity.sub, identity.email, identity.name) == ("g-real-1", "carol@gmail.com", "Carol")


def test_verify_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    token, public_key = _make_token_and_key(aud="otra-app.apps.googleusercontent.com")
    _patch_jwks(monkeypatch, public_key)
    with pytest.raises(GoogleTokenError):
        verify_google_token(token, client_id=_CLIENT_ID)


def test_verify_rejects_unverified_email(monkeypatch: pytest.MonkeyPatch) -> None:
    token, public_key = _make_token_and_key(email_verified=False)
    _patch_jwks(monkeypatch, public_key)
    with pytest.raises(GoogleTokenError):
        verify_google_token(token, client_id=_CLIENT_ID)


def test_verify_rejects_wrong_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    token, public_key = _make_token_and_key(iss="https://evil.example.com")
    _patch_jwks(monkeypatch, public_key)
    with pytest.raises(GoogleTokenError):
        verify_google_token(token, client_id=_CLIENT_ID)


def _fake_verifier(identity: GoogleIdentity) -> Iterator[None]:
    """Instala un verificador que devuelve `identity` para cualquier credencial."""
    app.dependency_overrides[get_google_verifier] = lambda: lambda _credential: identity
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_google_verifier, None)


@pytest.fixture
def google_user() -> Iterator[None]:
    yield from _fake_verifier(GoogleIdentity(sub="g-123", email="alice@gmail.com", name="Alice"))


def _me(client: TestClient, token: str) -> dict[str, object]:
    return client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()


def test_google_login_creates_user(client: TestClient, google_user: None) -> None:
    resp = client.post(GOOGLE, json={"credential": "any"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert _me(client, body["access_token"])["email"] == "alice@gmail.com"


def test_google_login_is_idempotent_by_sub(client: TestClient, google_user: None) -> None:
    first = client.post(GOOGLE, json={"credential": "any"}).json()
    second = client.post(GOOGLE, json={"credential": "any"}).json()
    # Mismo usuario en ambos logins (mismo id en /users/me).
    assert _me(client, first["access_token"])["id"] == _me(client, second["access_token"])["id"]


def test_google_login_links_existing_password_account(client: TestClient) -> None:
    # El usuario ya existe con email/contraseña.
    reg = client.post(
        "/auth/register", json={"email": "bob@gmail.com", "password": "password123"}
    ).json()
    existing_id = _me(client, reg["access_token"])["id"]

    # Entra con Google usando el mismo email → se vincula, no crea otra cuenta.
    gen = _fake_verifier(GoogleIdentity(sub="g-bob", email="bob@gmail.com", name="Bob"))
    next(gen)
    try:
        resp = client.post(GOOGLE, json={"credential": "any"})
        assert resp.status_code == 200
        assert _me(client, resp.json()["access_token"])["id"] == existing_id
    finally:
        next(gen, None)

    # Y sigue pudiendo entrar con su contraseña.
    assert (
        client.post(
            "/auth/login", json={"email": "bob@gmail.com", "password": "password123"}
        ).status_code
        == 200
    )


def test_google_login_rejects_invalid_token(client: TestClient) -> None:
    def _raise() -> object:
        def _verify(_credential: str) -> GoogleIdentity:
            raise GoogleTokenError("bad token")

        return _verify

    app.dependency_overrides[get_google_verifier] = _raise
    try:
        assert client.post(GOOGLE, json={"credential": "bad"}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_google_verifier, None)


def test_google_only_user_cannot_login_with_password(client: TestClient, google_user: None) -> None:
    client.post(GOOGLE, json={"credential": "any"})
    # No tiene contraseña: el login por contraseña falla con 401 (no 500).
    resp = client.post("/auth/login", json={"email": "alice@gmail.com", "password": "whatever12"})
    assert resp.status_code == 401


def test_forgot_password_neutral_for_google_only_user(
    client: TestClient, google_user: None
) -> None:
    client.post(GOOGLE, json={"credential": "any"})
    # forgot-password no debe fallar aunque el usuario no tenga contraseña.
    resp = client.post("/auth/forgot-password", json={"email": "alice@gmail.com"})
    assert resp.status_code == 200
