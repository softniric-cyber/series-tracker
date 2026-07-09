"""Endpoints de autenticación: registro, login y refresco de tokens."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.services import auth as auth_service
from app.services.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair_for(user_id: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenPair:
    try:
        user = auth_service.register_user(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except auth_service.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    return _token_pair_for(str(user.id))


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    try:
        user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    except auth_service.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from None
    return _token_pair_for(str(user.id))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        subject = decode_token(payload.refresh_token, "refresh")
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None
    user = auth_service.get_user_by_id(db, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    return _token_pair_for(str(user.id))
