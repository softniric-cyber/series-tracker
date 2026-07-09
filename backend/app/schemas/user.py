"""Esquemas Pydantic de usuario expuestos por la API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    country: str
    language: str
    created_at: datetime
