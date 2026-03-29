from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_features.geojson"


class Settings(BaseSettings):
    app_name: str = "Environmental Monitoring API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    repository_backend: Literal["file", "postgis"] = "file"
    data_path: Path = DEFAULT_DATA_PATH
    database_url: str = "postgresql+psycopg://spatial:spatial@localhost:5432/spatial"

    model_config = SettingsConfigDict(
        env_prefix="SPATIAL_DATA_API_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()