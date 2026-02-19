"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# ─── Enums ───

class DocType(str, Enum):
    invoice = "invoice"
    contract = "contract"
    crac = "crac"


class BatchStatus(str, Enum):
    running = "running"
    completed = "completed"
    interrupted = "interrupted"
    discarded = "discarded"


# ─── Health ───

class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    model_available: bool
    available_models: list[str] = []
    db_ok: bool = True


# ─── Folder / Stats ───

class FolderStatsResponse(BaseModel):
    invoice: int = 0
    contract: int = 0
    crac: int = 0
    total_files: int = 0
    processed_count: dict[str, int] = {}


class FolderFilesResponse(BaseModel):
    doc_type: str
    folder_path: str
    files: list[str]
    count: int


# ─── Results ───

class OCRResultResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    doc_type: str
    raw_text: Optional[str] = None
    clean_text: Optional[str] = None
    structured_data: dict = {}
    page_count: int = 0
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None
    processed_at: str
    batch_id: Optional[str] = None


class ResultsListResponse(BaseModel):
    results: list[OCRResultResponse]
    total: int


class DeleteResponse(BaseModel):
    deleted: bool
    message: str


# ─── Processing ───

class ProcessFileRequest(BaseModel):
    doc_type: DocType = DocType.invoice
    extract_raw: bool = True
    extract_structured: bool = True


class ProcessResponse(BaseModel):
    result_id: int
    file_name: str
    doc_type: str
    processing_time_seconds: float
    page_count: int
    error: Optional[str] = None


# ─── Batch ───

class BatchStartRequest(BaseModel):
    doc_types: list[DocType] = [DocType.invoice, DocType.contract, DocType.crac]
    extract_raw: bool = True
    extract_structured: bool = True


class BatchResponse(BaseModel):
    batch_id: str
    status: str
    total_files: int
    message: str


class BatchStatsResponse(BaseModel):
    batch_id: str
    status: str
    total_files: int
    done: int
    errors: int
    pending: int
    progress_pct: float
    avg_duration_s: float
    eta_seconds: float
    started_at: str
    finished_at: Optional[str] = None
    queue: list[dict] = []


class BatchListResponse(BaseModel):
    batches: list[dict]


# ─── DOCX ───

class DocxGenerateRequest(BaseModel):
    result_id: int


class DocxResponse(BaseModel):
    success: bool
    file_name: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


# ─── WebSocket messages ───

class WSBatchUpdate(BaseModel):
    type: str = "batch_update"
    batch_id: str
    status: str
    current_file: Optional[str] = None
    current_doc_type: Optional[str] = None
    completed: int = 0
    failed: int = 0
    total: int = 0
    progress_pct: float = 0
    eta_seconds: float = 0
    avg_per_file_s: float = 0
    elapsed_s: float = 0
    file_timings: list[dict] = []
    error: Optional[str] = None


# ─── Config ───

class ConfigResponse(BaseModel):
    ollama_base_url: str
    ollama_model: str
    invoice_dir: str
    contract_dir: str
    crac_dir: str