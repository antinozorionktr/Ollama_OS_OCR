"""
PDF Handler
Converts PDF pages to images for vision-model OCR processing.
Uses pdf2image (poppler) as primary, PyMuPDF as fallback.
"""

import os
import tempfile
from pathlib import Path
from app.utils.logger import setup_logger

logger = setup_logger("docvision.pdf")


def pdf_to_images(pdf_path: str, dpi: int = 300) -> list[str]:
    """
    Convert each page of a PDF into a PNG image.
    Returns a list of temporary image file paths.
    """
    logger.debug(f"Converting PDF: {os.path.basename(pdf_path)} at {dpi} DPI")

    # ─── Method 1: pdf2image (poppler-based) ───
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(pdf_path, dpi=dpi, fmt="png")
        image_paths = []
        for idx, img in enumerate(images):
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=f"_page{idx + 1}.png", prefix="ocr_"
            )
            img.save(tmp.name, "PNG")
            image_paths.append(tmp.name)
            tmp.close()
        logger.debug(f"pdf2image produced {len(image_paths)} pages")
        return image_paths

    except ImportError:
        logger.debug("pdf2image not available, trying PyMuPDF")

    # ─── Method 2: PyMuPDF (fitz) ───
    try:
        import fitz

        doc = fitz.open(pdf_path)
        image_paths = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=f"_page{page_idx + 1}.png", prefix="ocr_"
            )
            pix.save(tmp.name)
            image_paths.append(tmp.name)
            tmp.close()

        doc.close()
        logger.debug(f"PyMuPDF produced {len(image_paths)} pages")
        return image_paths

    except ImportError:
        pass

    raise ImportError(
        "No PDF-to-image library found. Install one of:\n"
        "  pip install pdf2image   (requires poppler system package)\n"
        "  pip install PyMuPDF     (pure Python, no system deps)"
    )