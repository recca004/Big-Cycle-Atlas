from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Big Cycle Atlas API"
    app_version: str = "1.1.0-dev"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/bigcycleatlas"
    cors_origins: list[str] = ["http://localhost:3000"]
    # Host-header allowlist — guards the unauthenticated local API against
    # DNS-rebinding (a remote page resolving a hostname to 127.0.0.1).
    # For private-network deploys add the proxy hostname (e.g. "bca.local").
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]"]
    # Directory of the built Astro frontend. When set and existing, the API
    # serves it at "/" (native production mode — no separate web server).
    web_dist: str | None = "../web-astro/dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()