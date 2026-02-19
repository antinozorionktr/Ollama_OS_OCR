"""
Word Document Generator
Orchestrates: clean OCR text → structure into sections → generate .docx via docx-js
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.utils.text_cleaner import clean_ocr_text, extract_sections, structured_data_to_sections
from app.utils.logger import setup_logger

logger = setup_logger("docvision.docx_gen")

GENERATOR_JS = os.path.join(os.path.dirname(__file__), "generate_docx.js")
DOCX_OUTPUT_DIR = os.environ.get("DOCX_OUTPUT_DIR", "/app/data/docx_outputs")


def generate_docx_for_result(result: dict) -> Optional[str]:
    """
    Generate a clean, formatted Word document from an OCR result.

    Args:
        result: dict with keys like raw_text, structured_data, file_name, doc_type, processed_at

    Returns:
        Path to generated .docx file, or None on failure.
    """
    os.makedirs(DOCX_OUTPUT_DIR, exist_ok=True)

    file_name = result.get("file_name", "document")
    doc_type = result.get("doc_type", "invoice")
    processed_at = result.get("processed_at", "")
    raw_text = result.get("raw_text", "")
    structured_data = result.get("structured_data", {})

    # ── Clean the raw text ──
    cleaned_text = clean_ocr_text(raw_text)

    # ── Parse into sections ──
    raw_sections = extract_sections(cleaned_text) if cleaned_text else []

    # ── Build structured sections ──
    structured_sections = structured_data_to_sections(structured_data, doc_type) if structured_data else []

    # ── Output path ──
    base_name = Path(file_name).stem
    output_filename = f"{base_name}_ocr_report.docx"
    output_path = os.path.join(DOCX_OUTPUT_DIR, output_filename)

    # Avoid collisions
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{base_name}_ocr_report_{counter}.docx"
        output_path = os.path.join(DOCX_OUTPUT_DIR, output_filename)
        counter += 1

    # ── Prepare JSON payload for the JS generator ──
    payload = {
        "file_name": file_name,
        "doc_type": doc_type,
        "processed_at": processed_at,
        "raw_sections": raw_sections,
        "structured_sections": structured_sections,
        "output_path": output_path,
    }

    logger.info(f"Generating Word document: {output_filename}",
                extra={"file_name": file_name, "step": "docx_generate"})

    try:
        proc = subprocess.run(
            ["node", GENERATOR_JS],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if proc.returncode != 0:
            logger.error(f"docx-js generation failed: {proc.stderr}",
                         extra={"file_name": file_name, "step": "docx_generate", "error": proc.stderr})
            return None

        # Validate the file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Word document generated: {output_filename} ({os.path.getsize(output_path)} bytes)",
                        extra={"file_name": file_name, "step": "docx_generate", "status": "done"})
            return output_path
        else:
            logger.error("Generated file is empty or missing",
                         extra={"file_name": file_name, "step": "docx_generate"})
            return None

    except subprocess.TimeoutExpired:
        logger.error("docx generation timed out", extra={"file_name": file_name, "step": "docx_generate"})
        return None
    except Exception as e:
        logger.error(f"docx generation error: {e}", extra={"file_name": file_name, "step": "docx_generate", "error": str(e)})
        return None


def get_docx_path_for_result(result: dict) -> Optional[str]:
    """Check if a docx already exists for this result, return its path."""
    file_name = result.get("file_name", "document")
    base_name = Path(file_name).stem
    output_filename = f"{base_name}_ocr_report.docx"
    output_path = os.path.join(DOCX_OUTPUT_DIR, output_filename)
    if os.path.exists(output_path):
        return output_path
    return None