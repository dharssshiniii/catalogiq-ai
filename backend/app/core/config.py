from functools import lru_cache
from pathlib import Path
import os
import tempfile

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CatalogIQ AI"
    app_mode: str = "DEMO"
    database_url: str = (
        f"sqlite:///{Path(tempfile.gettempdir()).as_posix()}/catalogiq.db"
        if os.getenv("VERCEL") else "sqlite:///./catalogiq.db"
    )
    max_upload_bytes: int = 5 * 1024 * 1024
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    catalogiq_mode: str | None = None
    live_batch_cap: int = 5
    review_confidence_threshold: float = 0.70
    retrieval_timeout_seconds: float = 10
    max_source_bytes: int = 5 * 1024 * 1024
    max_pdf_pages: int = 100
    required_columns: tuple[str, ...] = (
        "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"
    )
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[3] / ".env", extra="ignore")

    @property
    def mode(self) -> str:
        return (self.catalogiq_mode or self.app_mode).upper()


@lru_cache
def get_settings() -> Settings:
    return Settings()
