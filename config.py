"""
Application configuration — all settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Ollama ──
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral-small3.1:24b-2503-fp16"
    ollama_timeout: int = 300

    # ── Data folders ──
    invoice_dir: str = "/data/Invoice"
    contract_dir: str = "/data/Contract"
    crac_dir: str = "/data/Crac"

    # ── Storage ──
    db_path: str = "/app/data/docvision.db"
    docx_output_dir: str = "/app/data/docx_outputs"
    log_dir: str = "/app/logs"

    # ── Server ──
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    class Config:
        env_prefix = ""
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()