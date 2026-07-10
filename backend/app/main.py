from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, me, series, users
from app.core.config import get_settings
from app.services.tmdb_client import TMDBClient

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Un único cliente TMDB reutiliza conexiones durante toda la vida de la app.
    app.state.tmdb_client = TMDBClient()
    try:
        yield
    finally:
        await app.state.tmdb_client.aclose()


app = FastAPI(title="SeriesTracker API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(series.router)
app.include_router(me.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
