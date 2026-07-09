"""Esquemas Pydantic de usuario expuestos por la API."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

_COUNTRY_RE = re.compile(r"[A-Za-z]{2}")
_LANGUAGE_RE = re.compile(r"[A-Za-z]{2}-[A-Za-z]{2}")


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    country: str
    language: str
    created_at: datetime


class UserUpdate(BaseModel):
    """Campos editables del perfil. Todos opcionales (PATCH parcial)."""

    country: str | None = None
    language: str | None = None

    @field_validator("country")
    @classmethod
    def _normalize_country(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not _COUNTRY_RE.fullmatch(v):
            raise ValueError("country must be a 2-letter ISO 3166-1 code, e.g. 'ES'")
        return v.upper()

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not _LANGUAGE_RE.fullmatch(v):
            raise ValueError("language must look like 'es-ES' (ll-CC)")
        lang, region = v.split("-")
        return f"{lang.lower()}-{region.upper()}"
