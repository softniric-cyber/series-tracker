"""Tests unitarios de las primitivas de seguridad (sin BD)."""

import pytest

from app.services.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("s3cr3t-passw0rd")
    assert hashed != "s3cr3t-passw0rd"
    assert verify_password("s3cr3t-passw0rd", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct-horse")
    assert verify_password("wrong-password", hashed) is False


def test_hash_is_salted_unique_per_call() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-123")
    assert decode_token(token, "access") == "user-123"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token("user-456")
    assert decode_token(token, "refresh") == "user-456"


def test_access_token_rejected_as_refresh() -> None:
    token = create_access_token("user-123")
    with pytest.raises(TokenError):
        decode_token(token, "refresh")


def test_garbage_token_raises() -> None:
    with pytest.raises(TokenError):
        decode_token("not-a-jwt", "access")
