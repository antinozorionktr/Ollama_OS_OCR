"""
Application configuration — all settings from environment variables.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Ollama ──
    ollama_base_url: str = "http://localhost:11434"
    vision_model: str = "llama3.2-vision:11b"
    cleanup_model: str = "mistral:7b"

    # ── vLLM (Optional) ──
    vllm_base_url: Optional[str] = None
    use_vllm: bool = False

    ocr_dpi: int = 300

    ollama_timeout: int = 300

    # ── Data folders ──
    document_dir: str = "/data/Documents"

    # ── Storage ──
    db_path: str = "/app/data/docvision.db"
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