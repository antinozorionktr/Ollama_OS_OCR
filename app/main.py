"""
DocVision OCR — FastAPI Backend
REST API + WebSocket for document OCR processing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import router as api_router
from app.api.websocket import ws_router
from app.utils.store import get_store
from app.utils.logger import setup_logger

logger = setup_logger("docvision.main")

settings = get_settings()

app = FastAPI(
    title="DocVision OCR API",
    description=(
        "REST API for document OCR processing using Mistral Vision via Ollama. "
        "Supports invoices, contracts, and CRAC documents with text extraction, "
        "structured data parsing, and Word document generation."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ───
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.on_event("startup")
async def startup():
    logger.info("DocVision OCR API starting up")
    store = get_store()
    store.interrupt_active_batches()
    logger.info(f"Ollama: {settings.ollama_base_url} | Model: {settings.ollama_model}")
    logger.info(f"Folders: invoice={settings.invoice_dir}, contract={settings.contract_dir}, crac={settings.crac_dir}")
    logger.info("API ready at /docs")


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "DocVision OCR API",
        "version": "3.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }