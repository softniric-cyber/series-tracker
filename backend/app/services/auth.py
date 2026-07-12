"""Lógica de negocio de autenticación: alta y verificación de usuarios."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.security import hash_password, verify_password


class EmailAlreadyRegisteredError(Exception):
    """Ya existe un usuario con ese email."""


class InvalidCredentialsError(Exception):
    """El email no existe o la contraseña no coincide."""


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, *, email: str, password: str, display_name: str | None) -> User:
    normalized = _normalize_email(email)
    if db.scalar(select(User).where(User.email == normalized)) is not None:
        raise EmailAlreadyRegisteredError(normalized)
    user = User(
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    normalized = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))
    # Los usuarios solo-Google no tienen contraseña (password_hash None).
    if (
        user is None
        or user.password_hash is None
        or not verify_password(password, user.password_hash)
    ):
        raise InvalidCredentialsError(normalized)
    return user


def get_or_create_google_user(
    db: Session, *, google_sub: str, email: str, display_name: str | None
) -> User:
    """Busca el usuario por `google_sub`, si no por email (vincula), y si no lo crea.

    Los emails de Google vienen verificados, así que vincular por email es seguro:
    quien ya tenía cuenta con contraseña puede entrar además con Google.
    """
    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is not None:
        return user

    normalized = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))
    if user is not None:
        if user.google_sub is None:
            user.google_sub = google_sub
            db.commit()
            db.refresh(user)
        return user

    user = User(
        email=normalized,
        password_hash=None,
        google_sub=google_sub,
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: str) -> User | None:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    return db.get(User, uid)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def set_password(db: Session, user: User, new_password: str) -> User:
    """Cambia la contraseña (usado por el reset). Invalida enlaces de reset previos."""
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session, user: User, *, country: str | None, language: str | None
) -> User:
    if country is not None:
        user.country = country
    if language is not None:
        user.language = language
    db.commit()
    db.refresh(user)
    return user
