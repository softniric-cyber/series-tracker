"""Endpoints de usuario: ver/editar el perfil, exportar datos y darse de baja."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserDataExport, UserPublic, UserUpdate
from app.services import account as account_service
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


@router.get("/me/export", response_model=UserDataExport)
def export_me(current_user: CurrentUser, db: DbSession) -> UserDataExport:
    """Exporta todos los datos del usuario (RGPD, portabilidad — S3-3)."""
    return account_service.export_user_data(db, current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(current_user: CurrentUser, db: DbSession) -> None:
    """Baja de cuenta: borra el usuario y, en cascada, todos sus datos (RGPD — S3-3)."""
    account_service.delete_user(db, current_user)
