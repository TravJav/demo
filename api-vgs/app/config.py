from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "api-vgs"
    database_url: str = "postgresql+psycopg://vgs:vgs@localhost:5433/vgs"
    environment: str = "local"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="API_VGS_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
