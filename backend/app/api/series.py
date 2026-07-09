"""Endpoints de series. Búsqueda vía TMDB (S1-4)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, TmdbClient
from app.core.config import get_settings
from app.schemas.series import SeriesSearchResponse
from app.services.series import search_series

router = APIRouter(prefix="/series", tags=["series"])


@router.get("/search", response_model=SeriesSearchResponse)
async def search(
    current_user: CurrentUser,
    client: TmdbClient,
    q: Annotated[str, Query(min_length=1, max_length=100, description="Texto a buscar")],
    page: Annotated[int, Query(ge=1, le=500)] = 1,
) -> SeriesSearchResponse:
    return await search_series(
        client,
        query=q,
        page=page,
        language=current_user.language,
        image_base=get_settings().tmdb_image_base_url,
    )
