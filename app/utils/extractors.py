"""
Structured Extractor — simplified wrapper for the OCR pipeline.
Orchestrates: file upload → pipeline → results.
"""

import os
import time
from pathlib import Path
from typing import Optional

from app.utils.ollama_client import OllamaOCRClient
from app.services.ocr_pipeline import OCRPipeline
from app.utils.logger import setup_logger

logger = setup_logger("docvision.extractor")

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


class StructuredExtractor:
    """
    High-level document processing interface.
    Delegates to OCRPipeline for actual processing.
    """

    def __init__(self, client: OllamaOCRClient):
        self.client = client
        self.pipeline = OCRPipeline(client)

    def process_document(
        self,
        file_path: str,
        on_progress: Optional[callable] = None,
    ) -> dict:
        """
        Process a single document (PDF or image).
        Returns dict with: document_id, filename, total_pages, processing_time_seconds.
        """
        file_ext = Path(file_path).suffix.lower()
        valid_exts = {".pdf"} | SUPPORTED_IMAGE_EXTENSIONS
        if file_ext not in valid_exts:
            raise ValueError(f"Unsupported file type: {file_ext}")

        return self.pipeline.process_document(
            file_path=file_path,
            on_progress=on_progress,
        )