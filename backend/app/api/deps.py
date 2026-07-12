"""Dependencias reutilizables de la API (autenticación, sesión de BD)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.user import User
from app.services.auth import get_user_by_id
from app.services.google_auth import GoogleIdentity, verify_google_token
from app.services.security import TokenError, decode_token
from app.services.tmdb_client import TMDBClient

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        subject = decode_token(credentials.credentials, "access")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = get_user_by_id(db, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_tmdb_client(request: Request) -> TMDBClient:
    """Devuelve el cliente TMDB compartido creado en el lifespan de la app."""
    client: TMDBClient = request.app.state.tmdb_client
    return client


TmdbClient = Annotated[TMDBClient, Depends(get_tmdb_client)]

# Verificador del ID token de Google, inyectado como dependencia para poder
# sobreescribirlo en los tests (evita llamadas reales a Google).
GoogleVerifier = Callable[[str], GoogleIdentity]


def get_google_verifier() -> GoogleVerifier:
    client_id = get_settings().google_client_id
    return lambda credential: verify_google_token(credential, client_id)


GoogleTokenVerifier = Annotated[GoogleVerifier, Depends(get_google_verifier)]
