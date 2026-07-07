from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"

    database_url: str = "postgresql+psycopg://series:series@localhost:5432/series_tracker"

    jwt_secret: str = "change-me"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 30

    tmdb_bearer_token: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
