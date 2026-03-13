"""
FastAPI REST API routes for DocVision OCR.
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from starlette.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.api.schemas import (
    HealthResponse, ConfigResponse, StatsResponse,
    DocumentResponse, DocumentListResponse, DocumentDetailResponse,
    PageResponse, ProcessResponse, DeleteResponse, StructuredDataUpdate,
)
from app.services.ocr_pipeline import OCRPipeline
from app.utils.store import get_store
from app.utils.ollama_client import OllamaOCRClient
from app.utils.logger import setup_logger

logger = setup_logger("docvision.api")
router = APIRouter()

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def _list_files(directory: str) -> list[str]:
    """List supported files in a directory."""
    if not directory or not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    )


# ═══════════════════════════════════════════════
# HEALTH & CONFIG
# ═══════════════════════════════════════════════

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API, Ollama, and database health."""
    settings = get_settings()
    client = OllamaOCRClient(
        base_url=settings.ollama_base_url,
        vision_model=settings.vision_model,
        cleanup_model=settings.cleanup_model,
        vllm_base_url=settings.vllm_base_url,
        use_vllm=settings.use_vllm,
    )
    health = client.health_check()
    store = get_store()
    db_ok = True
    try:
        store.get_documents_count()
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok" if health["ollama_reachable"] and db_ok else "degraded",
        ollama_reachable=health["ollama_reachable"],
        vision_model_available=health.get("vision_model_available", False),
        cleanup_model_available=health.get("cleanup_model_available", False),
        model_available=health.get("model_available", False),
        available_models=health.get("available_models", []),
        db_ok=db_ok,
    )


@router.get("/config", response_model=ConfigResponse, tags=["System"])
async def get_config():
    """Get current server configuration."""
    s = get_settings()
    return ConfigResponse(
        ollama_base_url=s.ollama_base_url,
        vision_model=s.vision_model,
        cleanup_model=s.cleanup_model,
        document_dir=s.document_dir,
    )


# ═══════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════

@router.get("/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    """Get document and file counts."""
    settings = get_settings()
    store = get_store()
    files = _list_files(settings.document_dir)
    doc_count = store.get_documents_count()
    return StatsResponse(
        total_documents=doc_count,
        total_files=len(files),
    )


# ═══════════════════════════════════════════════
# UPLOAD & PROCESS
# ═══════════════════════════════════════════════

@router.post("/upload", response_model=ProcessResponse, tags=["Processing"])
async def upload_and_process(
    file: UploadFile = File(...),
):
    """Upload and process a document file through the OCR pipeline."""
    settings = get_settings()

    # Validate file type
    ext = Path(file.filename or "file.pdf").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    # Save to document directory
    target_dir = settings.document_dir
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, file.filename or "uploaded_file.pdf")

    # Avoid overwriting
    if os.path.exists(file_path):
        base, extension = os.path.splitext(file_path)
        file_path = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"

    file_path = os.path.abspath(file_path)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    try:
        client = OllamaOCRClient(
            base_url=settings.ollama_base_url,
            vision_model=settings.vision_model,
            cleanup_model=settings.cleanup_model,
            timeout=settings.ollama_timeout,
            vllm_base_url=settings.vllm_base_url,
            use_vllm=settings.use_vllm,
        )
        pipeline = OCRPipeline(client)

        def progress_callback(data):
            from app.services.batch_service import broadcast_sync
            broadcast_sync({
                "type": "upload_progress",
                "file_name": file.filename,
                **data
            })

        result = await run_in_threadpool(
            pipeline.process_document,
            file_path=file_path,
            on_progress=progress_callback,
        )

        return ProcessResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            total_pages=result["total_pages"],
            processing_time_seconds=result["processing_time_seconds"],
        )
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        raise HTTPException(500, f"Processing failed: {str(e)}")


# ═══════════════════════════════════════════════
# DOCUMENTS CRUD
# ═══════════════════════════════════════════════

@router.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents():
    """List all processed documents."""
    store = get_store()
    docs = store.get_all_documents()
    return DocumentListResponse(
        documents=[DocumentResponse(**d) for d in docs],
        total=len(docs),
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse, tags=["Documents"])
async def get_document(document_id: int):
    """Get a document with all its page results."""
    store = get_store()
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    pages = store.get_document_pages(document_id)

    return DocumentDetailResponse(
        document=DocumentResponse(**doc),
        pages=[PageResponse(**p) for p in pages],
    )


    return PageResponse(**page)


@router.put("/documents/{document_id}/pages/{page_number}/structured", tags=["Documents"])
async def update_page_structured(document_id: int, page_number: int, update: StructuredDataUpdate):
    """Update the structured data for a specific page."""
    store = get_store()
    page = store.get_page(document_id, page_number)
    if not page:
        raise HTTPException(404, f"Page {page_number} not found for document {document_id}")
    
    store.update_page_structured_data(document_id, page_number, update.structured_data)
    return {"updated": True}


@router.post("/documents/{document_id}/rerun", response_model=ProcessResponse, tags=["Processing"])
async def rerun_ocr(document_id: int):
    """Re-run the OCR pipeline for an existing document."""
    store = get_store()
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    
    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(404, "Original document file not found")
    
    settings = get_settings()
    try:
        # Before re-running, clear existing pages for this document
        # Wait, should we? Re-running usually means fresh start for that doc.
        # But we want to maintain the document ID.
        # Let's delete existing pages first.
        with store._cursor() as cur:
            cur.execute("DELETE FROM document_pages WHERE document_id = ?", (document_id,))
            
        client = OllamaOCRClient(
            base_url=settings.ollama_base_url,
            vision_model=settings.vision_model,
            cleanup_model=settings.cleanup_model,
            timeout=settings.ollama_timeout,
            vllm_base_url=settings.vllm_base_url,
            use_vllm=settings.use_vllm,
        )
        pipeline = OCRPipeline(client)
        
        # We need a process_document_v2 or similar that takes doc_id?
        # Current process_document always saves a NEW document.
        # I should modify process_document to accept an existing doc_id.
        
        result = await run_in_threadpool(
            pipeline.process_document,
            file_path=file_path,
            document_id=document_id, # We'll need to update process_document to handle this
        )
        
        return ProcessResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            total_pages=result["total_pages"],
            processing_time_seconds=result["processing_time_seconds"],
        )
    except Exception as e:
        logger.error(f"Rerun processing error: {e}")
        raise HTTPException(500, f"Rerun failed: {str(e)}")


@router.get("/documents/{document_id}/preview", tags=["Documents"])
async def get_document_preview(document_id: int):
    """Stream the original document file for preview."""
    store = get_store()
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(404, "Original document file not found")

    ext = Path(file_path).suffix.lower()
    media_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_map.get(ext, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type)


@router.delete("/documents/{document_id}", response_model=DeleteResponse, tags=["Documents"])
async def delete_document(document_id: int):
    """Delete a document and its associated file."""
    store = get_store()
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete physical file
    file_path = doc.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")

    # Delete from DB
    store.delete_document(document_id)
    return DeleteResponse(deleted=True, message=f"Document {document_id} deleted")


@router.delete("/documents", response_model=DeleteResponse, tags=["Documents"])
async def delete_all_documents():
    """Delete all documents and their data."""
    store = get_store()
    store.delete_all_documents()
    return DeleteResponse(deleted=True, message="All documents deleted")


# ═══════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════

@router.get("/logs", tags=["System"])
async def get_logs(limit: int = Query(100, ge=1, le=500)):
    """Get recent log entries from the in-memory buffer."""
    from app.utils.logger import get_log_buffer
    logs = get_log_buffer()
    return {"logs": logs[-limit:], "total": len(logs)}


@router.delete("/logs", tags=["System"])
async def clear_logs():
    """Clear the in-memory log buffer."""
    from app.utils.logger import clear_log_buffer
    clear_log_buffer()
    return {"cleared": True}