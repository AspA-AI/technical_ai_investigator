"""Application settings loaded from environment variables."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for Engineering Failure Investigation Copilot."""

    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/investigation_copilot",
        description="PostgreSQL connection URL (PGVector enabled)",
    )

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    UPLOAD_DIR: str = "datasets/uploads"
    RAW_DATA_DIR: str = "datasets/raw"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
