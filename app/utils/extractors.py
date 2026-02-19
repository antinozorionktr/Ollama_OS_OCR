"""
Structured Extractor
Orchestrates: PDF→images → OCR → structured extraction.
Integrates with logger and time estimator.
"""

import os
import time
import tempfile
from pathlib import Path
from typing import Optional

from utils.ollama_client import OllamaOCRClient
from utils.pdf_handler import pdf_to_images
from utils.logger import setup_logger

logger = setup_logger("docvision.extractor")

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


class StructuredExtractor:
    """
    High-level document processing pipeline.
    Handles PDFs (converts to images) and direct image inputs.
    """

    def __init__(self, client: OllamaOCRClient):
        self.client = client

    def process_document(
        self,
        file_path: str,
        doc_type: str = "invoice",
        extract_raw: bool = True,
        extract_structured: bool = True,
    ) -> dict:
        """
        Process a single document (PDF or image).
        Returns dict with: raw_text, structured_data, page_count, processing_time_seconds
        """
        file_name = os.path.basename(file_path)
        file_size_kb = round(os.path.getsize(file_path) / 1024, 1) if os.path.exists(file_path) else 0
        start_time = time.time()

        logger.info(
            f"Processing started: {file_name} ({doc_type}) | {file_size_kb} KB",
            extra={
                "file_name": file_name,
                "doc_type": doc_type,
                "file_size_kb": file_size_kb,
                "step": "process_start",
                "status": "started",
            },
        )

        file_ext = Path(file_path).suffix.lower()
        result = {
            "raw_text": "",
            "structured_data": {},
            "page_count": 0,
            "pages": [],
        }

        # ─── Convert to image(s) ───
        if file_ext == ".pdf":
            logger.debug(f"Converting PDF to images: {file_name}", extra={"step": "pdf_convert"})
            pdf_start = time.time()
            image_paths = pdf_to_images(file_path)
            pdf_duration = round(time.time() - pdf_start, 2)
            result["page_count"] = len(image_paths)
            cleanup_images = True
            logger.info(
                f"PDF converted: {len(image_paths)} pages in {pdf_duration}s",
                extra={
                    "file_name": file_name,
                    "pages": len(image_paths),
                    "duration_s": pdf_duration,
                    "step": "pdf_convert",
                },
            )
        elif file_ext in SUPPORTED_IMAGE_EXTENSIONS:
            image_paths = [file_path]
            result["page_count"] = 1
            cleanup_images = False
        else:
            logger.error(f"Unsupported file type: {file_ext}", extra={"file_name": file_name, "step": "validation"})
            raise ValueError(f"Unsupported file type: {file_ext}")

        try:
            all_raw_text = []
            all_structured = {}

            for page_idx, img_path in enumerate(image_paths):
                page_num = page_idx + 1
                page_result = {"page": page_num}

                logger.info(
                    f"Processing page {page_num}/{len(image_paths)} of {file_name}",
                    extra={
                        "file_name": file_name,
                        "page": page_num,
                        "pages": len(image_paths),
                        "step": "page_process",
                    },
                )

                # Raw text extraction
                if extract_raw:
                    logger.debug(f"Extracting raw text: page {page_num}", extra={"step": "raw_extraction"})
                    raw_start = time.time()
                    raw_text = self.client.extract_raw_text(img_path)
                    raw_dur = round(time.time() - raw_start, 2)
                    page_result["raw_text"] = raw_text
                    all_raw_text.append(f"--- Page {page_num} ---\n{raw_text}")
                    logger.info(
                        f"Raw text extracted: page {page_num} | {raw_dur}s | {len(raw_text)} chars",
                        extra={
                            "file_name": file_name,
                            "page": page_num,
                            "duration_s": raw_dur,
                            "step": "raw_extraction",
                            "status": "done",
                        },
                    )

                # Structured data extraction
                if extract_structured:
                    logger.debug(f"Extracting structured data: page {page_num}", extra={"step": "struct_extraction"})
                    struct_start = time.time()
                    structured = self.client.extract_structured_data(img_path, doc_type)
                    struct_dur = round(time.time() - struct_start, 2)
                    page_result["structured_data"] = structured

                    for key, value in structured.items():
                        if key.startswith("_"):
                            continue
                        if key not in all_structured:
                            all_structured[key] = value
                        elif isinstance(value, list) and isinstance(all_structured[key], list):
                            all_structured[key].extend(value)

                    logger.info(
                        f"Structured data extracted: page {page_num} | {struct_dur}s | {len(structured)} fields",
                        extra={
                            "file_name": file_name,
                            "page": page_num,
                            "duration_s": struct_dur,
                            "step": "struct_extraction",
                            "status": "done",
                        },
                    )

                result["pages"].append(page_result)

            result["raw_text"] = "\n\n".join(all_raw_text)
            result["structured_data"] = all_structured

        finally:
            if cleanup_images:
                for img_path in image_paths:
                    try:
                        os.unlink(img_path)
                    except OSError:
                        pass

        total_duration = round(time.time() - start_time, 2)
        result["processing_time_seconds"] = total_duration

        logger.info(
            f"Processing complete: {file_name} | {total_duration}s | {result['page_count']} pages",
            extra={
                "file_name": file_name,
                "doc_type": doc_type,
                "duration_s": total_duration,
                "pages": result["page_count"],
                "step": "process_complete",
                "status": "done",
            },
        )

        return result