"""
Application configuration — all settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Ollama ──
    ollama_base_url: str = "http://localhost:11434"
    ocr_model: str = "llama3.2-vision:11b"

    ollama_timeout: int = 300

    # ── Surya OCR ──
    surya_device: str = "auto"       # auto | cuda | cpu | mps
    surya_offline: bool = False      # True = HF_HUB_OFFLINE=1 (after first download)

    # ── Data folders ──
    document_dir: str = "/data/Documents"

    # ── Storage ──
    db_path: str = "/app/data/docvision.db"
    docx_output_dir: str = "/app/data/docx_outputs"
    log_dir: str = "/app/logs"

    # ── Server ──
    host: str = "0.0.0.0"
    port: int = 8004
    cors_origins: str = "*"

    model_config = {
        "env_file": ".env",
        "env_prefix": "",
        "case_sensitive": False,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()