import os
from typing import Literal
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env fica em backend/ — dois níveis acima de app/core/
_ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "HMPCF"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # CORS — em produção LAN pode ficar ["*"] pois frontend e backend são mesma origem
    CORS_ORIGINS: list[str] = ["*"]

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "hmpcf"

    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_PRE_PING: bool = True

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """URL síncrona usada exclusivamente pelo Alembic."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
