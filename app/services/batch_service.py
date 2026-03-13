"""
Batch Processing Service
Runs batch OCR jobs in background threads and broadcasts
progress via WebSocket connections.
"""

import os
import time
import uuid
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.utils.ollama_client import OllamaOCRClient
from app.services.ocr_pipeline import OCRPipeline
from app.utils.store import get_store
from app.utils.logger import setup_logger

logger = setup_logger("docvision.batch_service")

# ─── WebSocket connection manager ───
_ws_connections: set = set()
_ws_lock = threading.Lock()

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def list_files(directory: str) -> list[str]:
    if not directory or not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    )


def register_ws(ws):
    with _ws_lock:
        _ws_connections.add(ws)


def unregister_ws(ws):
    with _ws_lock:
        _ws_connections.discard(ws)


def broadcast_sync(message: dict):
    """Broadcast a message to all connected WebSocket clients (from sync thread)."""
    with _ws_lock:
        dead = set()
        for ws in _ws_connections:
            try:
                loop = ws._loop if hasattr(ws, '_loop') else asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(ws.send_json(message), loop)
            except Exception:
                dead.add(ws)
        _ws_connections.difference_update(dead)


async def broadcast_async(message: dict):
    """Broadcast a message to all connected WebSocket clients (from async context)."""
    with _ws_lock:
        dead = set()
        for ws in _ws_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        _ws_connections.difference_update(dead)