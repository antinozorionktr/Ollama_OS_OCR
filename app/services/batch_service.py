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
from app.utils.extractors import StructuredExtractor
from app.utils.store import get_store
from app.utils.time_estimator import TimeEstimator
from app.utils.logger import setup_logger

logger = setup_logger("docvision.batch_service")

# ─── WebSocket connection manager ───
_ws_connections: set = set()
_ws_lock = threading.Lock()

# ─── Running batches tracker ───
_running_batches: dict[str, dict] = {}

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


def _broadcast_sync(message: dict):
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


def get_running_batch_info(batch_id: str) -> Optional[dict]:
    return _running_batches.get(batch_id)


def start_batch(
    doc_types: list[str],
    extract_raw: bool = True,
    extract_structured: bool = True,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> dict:
    """
    Create and start a batch processing job in a background thread.
    Returns batch metadata immediately.
    """
    settings = get_settings()
    store = get_store()

    folder_map = {
        "invoice": settings.invoice_dir,
        "contract": settings.contract_dir,
        "crac": settings.crac_dir,
    }

    files_to_process = []
    for doc_type in doc_types:
        folder = folder_map.get(doc_type, "")
        for fp in list_files(folder):
            files_to_process.append((fp, doc_type))

    if not files_to_process:
        return {"error": "No supported files found in selected folders", "batch_id": None}

    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    store.create_batch(batch_id, files_to_process, config={
        "model": settings.ollama_model,
        "ollama_url": settings.ollama_base_url,
        "extract_raw": extract_raw,
        "extract_structured": extract_structured,
    })

    logger.info(f"Batch {batch_id} created: {len(files_to_process)} files")

    # Start processing in background thread
    thread = threading.Thread(
        target=_run_batch_thread,
        args=(batch_id, files_to_process, extract_raw, extract_structured, loop),
        daemon=True,
    )
    thread.start()

    return {
        "batch_id": batch_id,
        "status": "running",
        "total_files": len(files_to_process),
        "message": f"Batch started with {len(files_to_process)} files",
    }


def resume_batch(batch_id: str, extract_raw: bool = True, extract_structured: bool = True,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> dict:
    """Resume an interrupted batch."""
    store = get_store()
    batch = store.get_batch(batch_id)
    if not batch:
        return {"error": "Batch not found", "batch_id": batch_id}

    pending = store.get_pending_files(batch_id)
    if not pending:
        store.finish_batch(batch_id, "completed")
        return {"batch_id": batch_id, "status": "completed", "total_files": 0,
                "message": "All files already processed"}

    # Convert pending dicts to tuples
    files_to_process = [(p["file_path"], p["doc_type"]) for p in pending]

    # Mark as running again
    store._get_conn().execute("UPDATE batches SET status = 'running' WHERE id = ?", (batch_id,))
    store._get_conn().commit()

    thread = threading.Thread(
        target=_run_batch_thread,
        args=(batch_id, files_to_process, extract_raw, extract_structured, loop),
        daemon=True,
    )
    thread.start()

    return {
        "batch_id": batch_id,
        "status": "running",
        "total_files": len(files_to_process),
        "message": f"Batch resumed with {len(files_to_process)} remaining files",
    }


def _run_batch_thread(
    batch_id: str,
    files: list[tuple[str, str]],
    extract_raw: bool,
    extract_structured: bool,
    loop: Optional[asyncio.AbstractEventLoop],
):
    """Background thread that processes each file and broadcasts progress."""
    settings = get_settings()
    store = get_store()
    client = OllamaOCRClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )
    extractor = StructuredExtractor(client)
    estimator = TimeEstimator()
    estimator.start_batch(len(files))

    batch_info = {
        "batch_id": batch_id,
        "status": "running",
        "total": len(files),
        "completed": 0,
        "failed": 0,
        "file_timings": [],
    }
    _running_batches[batch_id] = batch_info

    for idx, (file_path, doc_type) in enumerate(files):
        file_name = os.path.basename(file_path)
        timing_record = estimator.start_file(file_name, doc_type)

        # Broadcast current progress
        bs = estimator.get_batch_stats()
        msg = {
            "type": "batch_update",
            "batch_id": batch_id,
            "status": "processing",
            "current_file": file_name,
            "current_doc_type": doc_type,
            "completed": batch_info["completed"],
            "failed": batch_info["failed"],
            "total": len(files),
            "progress_pct": round((idx) / len(files) * 100, 1),
            "eta_seconds": bs["eta_seconds"],
            "avg_per_file_s": bs["avg_per_file_seconds"],
            "elapsed_s": bs["elapsed_seconds"],
            "file_timings": batch_info["file_timings"],
        }

        if loop:
            asyncio.run_coroutine_threadsafe(broadcast_async_from_loop(msg, loop), loop)
        else:
            _broadcast_sync(msg)

        try:
            result = extractor.process_document(
                file_path=file_path,
                doc_type=doc_type,
                extract_raw=extract_raw,
                extract_structured=extract_structured,
            )
            result["file_name"] = file_name
            result["file_path"] = file_path
            result["doc_type"] = doc_type
            result["processed_at"] = datetime.now().isoformat()

            result_id = store.save_result(result, batch_id=batch_id)
            estimator.finish_file(timing_record, status="done")
            store.mark_file_done(batch_id, file_path, result_id, timing_record.duration_s)
            batch_info["completed"] += 1

            batch_info["file_timings"].append({
                "file": file_name, "type": doc_type,
                "pages": result.get("page_count", 1),
                "time_s": timing_record.duration_s, "status": "done",
            })

        except Exception as e:
            estimator.finish_file(timing_record, status="error")
            store.mark_file_error(batch_id, file_path, str(e), timing_record.duration_s or 0)
            err_result = {
                "file_name": file_name, "file_path": file_path, "doc_type": doc_type,
                "error": str(e), "processed_at": datetime.now().isoformat(),
            }
            store.save_result(err_result, batch_id=batch_id)
            batch_info["failed"] += 1

            batch_info["file_timings"].append({
                "file": file_name, "type": doc_type,
                "pages": 0, "time_s": timing_record.duration_s or 0, "status": "error",
                "error": str(e),
            })
            logger.error(f"Batch {batch_id}: error on {file_name}: {e}")

    # ── Batch done ──
    store.finish_batch(batch_id, "completed")
    batch_info["status"] = "completed"

    final_bs = estimator.get_batch_stats()
    done_msg = {
        "type": "batch_complete",
        "batch_id": batch_id,
        "status": "completed",
        "completed": batch_info["completed"],
        "failed": batch_info["failed"],
        "total": len(files),
        "progress_pct": 100.0,
        "elapsed_s": final_bs["elapsed_seconds"],
        "file_timings": batch_info["file_timings"],
    }

    if loop:
        asyncio.run_coroutine_threadsafe(broadcast_async_from_loop(done_msg, loop), loop)
    else:
        _broadcast_sync(done_msg)

    logger.info(f"Batch {batch_id} complete: {batch_info['completed']} done, {batch_info['failed']} errors")
    _running_batches.pop(batch_id, None)


async def broadcast_async_from_loop(msg: dict, loop: asyncio.AbstractEventLoop):
    """Helper to broadcast from the event loop."""
    await broadcast_async(msg)