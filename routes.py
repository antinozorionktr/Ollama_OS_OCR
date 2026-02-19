"""
FastAPI REST API routes for DocVision OCR.
"""

import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.api.schemas import (
    HealthResponse, FolderStatsResponse, FolderFilesResponse,
    OCRResultResponse, ResultsListResponse, DeleteResponse,
    ProcessFileRequest, ProcessResponse,
    BatchStartRequest, BatchResponse, BatchStatsResponse, BatchListResponse,
    DocxGenerateRequest, DocxResponse, ConfigResponse, DocType,
)
from app.utils.store import get_store
from app.utils.ollama_client import OllamaOCRClient
from app.utils.extractors import StructuredExtractor
from app.utils.text_cleaner import clean_ocr_text
from app.utils.docx_generator import generate_docx_for_result
from app.utils.logger import setup_logger, get_log_buffer, clear_log_buffer
from app.services.batch_service import (
    start_batch, resume_batch, list_files, SUPPORTED_EXTENSIONS,
)

logger = setup_logger("docvision.api")
router = APIRouter()


# ═══════════════════════════════════════════════
# HEALTH & CONFIG
# ═══════════════════════════════════════════════

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API, Ollama, and database health."""
    settings = get_settings()
    client = OllamaOCRClient(base_url=settings.ollama_base_url, model=settings.ollama_model)
    health = client.health_check()
    store = get_store()
    db_ok = True
    try:
        store.get_results_count()
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok" if health["ollama_reachable"] and db_ok else "degraded",
        ollama_reachable=health["ollama_reachable"],
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
        ollama_model=s.ollama_model,
        invoice_dir=s.invoice_dir,
        contract_dir=s.contract_dir,
        crac_dir=s.crac_dir,
    )


# ═══════════════════════════════════════════════
# FOLDERS & STATS
# ═══════════════════════════════════════════════

@router.get("/stats", response_model=FolderStatsResponse, tags=["Stats"])
async def get_stats():
    """Get file counts per folder and processed counts."""
    settings = get_settings()
    store = get_store()
    inv = list_files(settings.invoice_dir)
    con = list_files(settings.contract_dir)
    crac = list_files(settings.crac_dir)
    processed = store.get_results_count()

    return FolderStatsResponse(
        invoice=len(inv),
        contract=len(con),
        crac=len(crac),
        total_files=len(inv) + len(con) + len(crac),
        processed_count=processed,
    )


@router.get("/folders/{doc_type}", response_model=FolderFilesResponse, tags=["Stats"])
async def get_folder_files(doc_type: DocType):
    """List all supported files in a folder."""
    settings = get_settings()
    folder_map = {
        "invoice": settings.invoice_dir,
        "contract": settings.contract_dir,
        "crac": settings.crac_dir,
    }
    folder = folder_map[doc_type.value]
    files = list_files(folder)
    return FolderFilesResponse(
        doc_type=doc_type.value,
        folder_path=folder,
        files=[os.path.basename(f) for f in files],
        count=len(files),
    )


# ═══════════════════════════════════════════════
# RESULTS CRUD
# ═══════════════════════════════════════════════

@router.get("/results", response_model=ResultsListResponse, tags=["Results"])
async def get_results(
    doc_type: Optional[str] = Query(None, description="Filter by doc type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get all OCR results with optional filtering and pagination."""
    store = get_store()
    all_results = store.get_all_results(doc_type=doc_type)
    total = len(all_results)
    page = all_results[offset: offset + limit]

    results = []
    for r in page:
        clean = clean_ocr_text(r.get("raw_text", "")) if r.get("raw_text") else None
        results.append(OCRResultResponse(
            id=r["id"],
            file_name=r.get("file_name", ""),
            file_path=r.get("file_path", ""),
            doc_type=r.get("doc_type", ""),
            raw_text=r.get("raw_text"),
            clean_text=clean,
            structured_data=r.get("structured_data", {}),
            page_count=r.get("page_count", 0),
            processing_time_seconds=r.get("processing_time_seconds"),
            error=r.get("error"),
            processed_at=r.get("processed_at", ""),
            batch_id=r.get("batch_id"),
        ))

    return ResultsListResponse(results=results, total=total)


@router.get("/results/{result_id}", response_model=OCRResultResponse, tags=["Results"])
async def get_result(result_id: int):
    """Get a single OCR result by ID."""
    store = get_store()
    all_results = store.get_all_results()
    for r in all_results:
        if r["id"] == result_id:
            clean = clean_ocr_text(r.get("raw_text", "")) if r.get("raw_text") else None
            return OCRResultResponse(
                id=r["id"],
                file_name=r.get("file_name", ""),
                file_path=r.get("file_path", ""),
                doc_type=r.get("doc_type", ""),
                raw_text=r.get("raw_text"),
                clean_text=clean,
                structured_data=r.get("structured_data", {}),
                page_count=r.get("page_count", 0),
                processing_time_seconds=r.get("processing_time_seconds"),
                error=r.get("error"),
                processed_at=r.get("processed_at", ""),
                batch_id=r.get("batch_id"),
            )
    raise HTTPException(status_code=404, detail="Result not found")


@router.delete("/results", response_model=DeleteResponse, tags=["Results"])
async def delete_all_results():
    """Delete all OCR results and batch data."""
    store = get_store()
    store.delete_all_results()
    return DeleteResponse(deleted=True, message="All results and batches cleared")


@router.delete("/results/{result_id}", response_model=DeleteResponse, tags=["Results"])
async def delete_result(result_id: int):
    """Delete a single result by ID."""
    store = get_store()
    with store._cursor() as cur:
        cur.execute("DELETE FROM results WHERE id = ?", (result_id,))
    return DeleteResponse(deleted=True, message=f"Result {result_id} deleted")


# ═══════════════════════════════════════════════
# SINGLE FILE PROCESSING
# ═══════════════════════════════════════════════

@router.post("/process/upload", response_model=ProcessResponse, tags=["Processing"])
async def process_uploaded_file(
    file: UploadFile = File(...),
    doc_type: DocType = Query(DocType.invoice),
    extract_raw: bool = Query(True),
    extract_structured: bool = Query(True),
):
    """Upload and process a single document file."""
    settings = get_settings()

    ext = Path(file.filename or "file.pdf").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    # Save to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        client = OllamaOCRClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
        )
        extractor = StructuredExtractor(client)

        result = extractor.process_document(
            file_path=tmp_path,
            doc_type=doc_type.value,
            extract_raw=extract_raw,
            extract_structured=extract_structured,
        )
        result["file_name"] = file.filename
        result["file_path"] = "uploaded"
        result["doc_type"] = doc_type.value
        result["processed_at"] = datetime.now().isoformat()

        store = get_store()
        result_id = store.save_result(result)

        return ProcessResponse(
            result_id=result_id,
            file_name=file.filename or "",
            doc_type=doc_type.value,
            processing_time_seconds=result.get("processing_time_seconds", 0),
            page_count=result.get("page_count", 0),
        )
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        raise HTTPException(500, f"Processing failed: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.post("/process/path", response_model=ProcessResponse, tags=["Processing"])
async def process_file_by_path(
    file_path: str = Query(..., description="Absolute path to file on server"),
    doc_type: DocType = Query(DocType.invoice),
    extract_raw: bool = Query(True),
    extract_structured: bool = Query(True),
):
    """Process a file by its server-side path."""
    if not os.path.exists(file_path):
        raise HTTPException(404, f"File not found: {file_path}")

    settings = get_settings()
    client = OllamaOCRClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )
    extractor = StructuredExtractor(client)

    try:
        result = extractor.process_document(
            file_path=file_path,
            doc_type=doc_type.value,
            extract_raw=extract_raw,
            extract_structured=extract_structured,
        )
        result["file_name"] = os.path.basename(file_path)
        result["file_path"] = file_path
        result["doc_type"] = doc_type.value
        result["processed_at"] = datetime.now().isoformat()

        store = get_store()
        result_id = store.save_result(result)

        return ProcessResponse(
            result_id=result_id,
            file_name=os.path.basename(file_path),
            doc_type=doc_type.value,
            processing_time_seconds=result.get("processing_time_seconds", 0),
            page_count=result.get("page_count", 0),
        )
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")


# ═══════════════════════════════════════════════
# BATCH PROCESSING
# ═══════════════════════════════════════════════

@router.post("/batches/start", response_model=BatchResponse, tags=["Batches"])
async def start_batch_processing(req: BatchStartRequest):
    """Start a new batch processing job (runs in background)."""
    loop = asyncio.get_event_loop()
    result = start_batch(
        doc_types=[d.value for d in req.doc_types],
        extract_raw=req.extract_raw,
        extract_structured=req.extract_structured,
        loop=loop,
    )
    if result.get("error"):
        raise HTTPException(400, result["error"])

    return BatchResponse(**result)


@router.post("/batches/{batch_id}/resume", response_model=BatchResponse, tags=["Batches"])
async def resume_batch_processing(
    batch_id: str,
    extract_raw: bool = Query(True),
    extract_structured: bool = Query(True),
):
    """Resume an interrupted batch."""
    loop = asyncio.get_event_loop()
    result = resume_batch(batch_id, extract_raw, extract_structured, loop=loop)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return BatchResponse(**result)


@router.post("/batches/{batch_id}/discard", response_model=BatchResponse, tags=["Batches"])
async def discard_batch(batch_id: str):
    """Discard an interrupted batch."""
    store = get_store()
    batch = store.get_batch(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    store.finish_batch(batch_id, "discarded")
    return BatchResponse(
        batch_id=batch_id, status="discarded",
        total_files=batch["total_files"], message="Batch discarded",
    )


@router.get("/batches", response_model=BatchListResponse, tags=["Batches"])
async def list_batches(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
):
    """List all batches."""
    store = get_store()
    with store._cursor() as cur:
        if status:
            cur.execute(
                "SELECT * FROM batches WHERE status = ? ORDER BY started_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cur.execute("SELECT * FROM batches ORDER BY started_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
    return BatchListResponse(batches=[dict(r) for r in rows])


@router.get("/batches/active", tags=["Batches"])
async def get_active_batch():
    """Get the most recent active/interrupted batch."""
    store = get_store()
    batch = store.get_active_batch()
    if not batch:
        return {"batch": None, "message": "No active batch"}
    stats = store.get_batch_stats(batch["id"])
    return {"batch": batch, "stats": stats}


@router.get("/batches/{batch_id}", response_model=BatchStatsResponse, tags=["Batches"])
async def get_batch_status(batch_id: str, include_queue: bool = Query(False)):
    """Get detailed batch status and progress."""
    store = get_store()
    stats = store.get_batch_stats(batch_id)
    if not stats:
        raise HTTPException(404, "Batch not found")

    queue = []
    if include_queue:
        queue = store.get_batch_queue(batch_id)

    return BatchStatsResponse(**stats, queue=queue)


# ═══════════════════════════════════════════════
# DOCX GENERATION
# ═══════════════════════════════════════════════

@router.post("/results/{result_id}/docx", response_model=DocxResponse, tags=["Documents"])
async def generate_docx(result_id: int):
    """Generate a Word document for a specific result."""
    store = get_store()
    all_results = store.get_all_results()
    result = None
    for r in all_results:
        if r["id"] == result_id:
            result = r
            break
    if not result:
        raise HTTPException(404, "Result not found")
    if result.get("error"):
        raise HTTPException(400, "Cannot generate DOCX for failed result")

    docx_path = generate_docx_for_result(result)
    if not docx_path:
        return DocxResponse(success=False, error="DOCX generation failed")

    file_name = os.path.basename(docx_path)
    return DocxResponse(
        success=True,
        file_name=file_name,
        download_url=f"/api/results/{result_id}/docx/download",
    )


@router.get("/results/{result_id}/docx/download", tags=["Documents"])
async def download_docx(result_id: int):
    """Download the generated Word document."""
    store = get_store()
    all_results = store.get_all_results()
    result = None
    for r in all_results:
        if r["id"] == result_id:
            result = r
            break
    if not result:
        raise HTTPException(404, "Result not found")

    docx_path = generate_docx_for_result(result)
    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(404, "DOCX file not found — generate it first")

    return FileResponse(
        docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(docx_path),
    )


@router.post("/results/docx/bulk", tags=["Documents"])
async def generate_bulk_docx(doc_type: Optional[str] = Query(None)):
    """Generate Word documents for all results (optionally filtered)."""
    store = get_store()
    all_results = store.get_all_results(doc_type=doc_type)
    success = 0
    failed = 0
    for r in all_results:
        if not r.get("error"):
            path = generate_docx_for_result(r)
            if path:
                success += 1
            else:
                failed += 1
    return {"generated": success, "failed": failed, "total": len(all_results)}


# ═══════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════

@router.get("/logs", tags=["System"])
async def get_logs(limit: int = Query(100, ge=1, le=500)):
    """Get recent log entries from the in-memory buffer."""
    logs = get_log_buffer()
    return {"logs": logs[-limit:], "total": len(logs)}


@router.delete("/logs", tags=["System"])
async def clear_logs():
    """Clear the in-memory log buffer."""
    clear_log_buffer()
    return {"cleared": True}