"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from typing import Optional


# ─── Health ───

class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    vision_model_available: bool = False
    cleanup_model_available: bool = False
    model_available: bool
    available_models: list[str] = []
    db_ok: bool = True


# ─── Config ───

class ConfigResponse(BaseModel):
    ollama_base_url: str
    vision_model: str
    cleanup_model: str
    document_dir: str


# ─── Document ───

class DocumentResponse(BaseModel):
    id: int
    filename: str
    uploaded_at: str
    total_pages: int = 0
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ─── Page ───

class PageResponse(BaseModel):
    id: int
    document_id: int
    page_number: int
    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    recreated_layout: Optional[str] = None
    structured_data: Optional[str] = None
    created_at: Optional[str] = None


class StructuredDataUpdate(BaseModel):
    structured_data: str


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    pages: list[PageResponse]


# ─── Processing ───

class ProcessResponse(BaseModel):
    document_id: int
    filename: str
    total_pages: int
    processing_time_seconds: float
    error: Optional[str] = None


# ─── Delete ───

class DeleteResponse(BaseModel):
    deleted: bool
    message: str


# ─── Stats ───

class StatsResponse(BaseModel):
    total_documents: int = 0
    total_files: int = 0