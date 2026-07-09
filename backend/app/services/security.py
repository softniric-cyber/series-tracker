"""Primitivas de seguridad sin dependencias de BD: hashing de contraseñas y JWT.

Se mantienen puras (sin acceso a base de datos) para poder testearlas de forma
unitaria y para que cuenten en la cobertura de `app/services`.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()
_ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """El token es inválido, ha expirado o no es del tipo esperado."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=_ALGORITHM)


def create_access_token(subject: str) -> str:
    minutes = get_settings().jwt_access_minutes
    return _create_token(subject, "access", timedelta(minutes=minutes))


def create_refresh_token(subject: str) -> str:
    days = get_settings().jwt_refresh_days
    return _create_token(subject, "refresh", timedelta(days=days))


def decode_token(token: str, expected_type: TokenType) -> str:
    """Devuelve el `sub` del token si es válido y del tipo esperado; si no, lanza TokenError."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError("invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("unexpected token type")
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise TokenError("missing subject")
    return subject
