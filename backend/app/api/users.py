"""Endpoints de usuario: ver y editar el perfil propio."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserPublic, UserUpdate
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def read_me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.patch("/me", response_model=UserPublic)
def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> UserPublic:
    user = auth_service.update_user_profile(
        db, current_user, country=payload.country, language=payload.language
    )
    return UserPublic.model_validate(user)
