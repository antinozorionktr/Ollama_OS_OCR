"""
Structured Logger for DocVision OCR
Provides file + console logging with structured JSON log entries,
and an in-memory log buffer for the Streamlit UI live log viewer.
"""

import logging
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Optional


# ─── In-memory ring buffer for UI log viewer ───
_LOG_BUFFER: deque = deque(maxlen=500)


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log files."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach extra fields if present
        for key in ("file_name", "doc_type", "duration_s", "page", "pages",
                     "step", "status", "error", "model", "ollama_url",
                     "file_size_kb", "eta_s", "progress"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class BufferHandler(logging.Handler):
    """Pushes formatted log lines into the in-memory deque for the UI."""

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "msg": record.getMessage(),
            }
            for key in ("file_name", "doc_type", "duration_s", "step", "status",
                         "error", "eta_s", "progress", "page", "pages"):
                val = getattr(record, key, None)
                if val is not None:
                    entry[key] = val
            _LOG_BUFFER.append(entry)
        except Exception:
            pass


def setup_logger(
    name: str = "docvision",
    log_dir: str = "/app/logs",
    level: int = logging.DEBUG,
) -> logging.Logger:
    """
    Configure and return the application logger.
    - Console: colored human-readable
    - File:    structured JSON (rotated daily via name)
    - Buffer:  in-memory for Streamlit live viewer
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)
    logger.propagate = False

    # ── Console handler (human-readable) ──
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "\033[90m%(asctime)s\033[0m │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # ── JSON file handler ──
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"docvision_{today}.log"),
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # ── In-memory buffer handler ──
    buf_handler = BufferHandler()
    buf_handler.setLevel(logging.DEBUG)
    logger.addHandler(buf_handler)

    return logger


def get_log_buffer() -> list[dict]:
    """Return a snapshot of the in-memory log buffer (newest last)."""
    return list(_LOG_BUFFER)


def clear_log_buffer():
    """Clear the in-memory log buffer."""
    _LOG_BUFFER.clear()