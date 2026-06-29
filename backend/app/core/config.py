"""
config.py
---------
Application settings loaded from environment variables via Pydantic BaseSettings.
All values have safe defaults for local development.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # File limits
    max_upload_mb: int = 500
    max_pdf_count: int = 10_000

    # Processing
    max_workers: int = 4
    skip_encrypted: bool = True
    overwrite_output: bool = True

    # Job lifecycle
    job_ttl_minutes: int = 30  # temp files deleted after this many minutes
    cleanup_interval_seconds: int = 300  # how often the cleanup thread wakes up

    # Temp directory root (uses OS default if empty)
    tmp_root: str = ""

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
