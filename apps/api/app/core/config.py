from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Big Cycle Atlas API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/bigcycleatlas"
    cors_origins: list[str] = ["http://localhost:3000"]
    # Directory of the built Astro frontend. When set and existing, the API
    # serves it at "/" (native production mode — no separate web server).
    web_dist: str | None = "../web-astro/dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()