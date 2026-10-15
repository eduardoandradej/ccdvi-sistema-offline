"""Configuração via variáveis de ambiente (prefixo DVI_). Nenhum segredo é versionado."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DVI_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://dvi:dvi_dev@localhost:5432/dvi"
    storage_dir: Path = Path("./var/storage")
    max_upload_mb: int = 25
    session_hours: int = 12
    cookie_secure: bool = False  # True quando servido via HTTPS interno
    cookie_name: str = "dvi_session"
    # Origem permitida para o frontend em modo desenvolvimento (Vite). Em produção o
    # Nginx serve frontend e API na mesma origem e CORS fica desabilitado.
    dev_cors_origin: str | None = None
    app_env: str = "development"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
