"""
Surya OCR Client — v0.17.x API
Wraps Surya's OCR engine to produce the same token dict format the pipeline expects:
  {text: str, bbox: [x1, y1, x2, y2], page: int}

Surya gives real pixel-accurate bounding boxes — not LLM-guessed positions.
Models are lazy-loaded and cached on first call.

Surya v0.17 API:
  FoundationPredictor  → shared backbone
  DetectionPredictor   → finds text regions
  RecognitionPredictor(foundation) → reads text + returns OCRResult with text_lines

Offline usage:
  Set SURYA_OFFLINE=true in .env after the first download to prevent any
  HuggingFace network calls (equivalent to HF_HUB_OFFLINE=1).
"""

import os
import functools
from pathlib import Path
from typing import Optional

from app.utils.logger import setup_logger

logger = setup_logger("docvision.surya")


# ──────────────────────────────────────────────────────────
# Lazy model loader — cached globally, loaded only once
# ──────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _load_surya_predictors(device: str = "auto"):
    """
    Load Surya v0.17 predictors (Foundation → Detection → Recognition).
    Result is LRU-cached — models are downloaded and loaded only on first call.
    """
    import torch
    from surya.foundation import FoundationPredictor
    from surya.detection import DetectionPredictor
    from surya.recognition import RecognitionPredictor

    # Resolve device
    if device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    logger.info(f"Loading Surya OCR predictors on device: {device}")

    foundation = FoundationPredictor(device=device)
    det_predictor = DetectionPredictor()
    rec_predictor = RecognitionPredictor(foundation_predictor=foundation)

    logger.info("Surya OCR predictors loaded and cached.")
    return det_predictor, rec_predictor, device


# ──────────────────────────────────────────────────────────
# Public client class
# ──────────────────────────────────────────────────────────

class SuryaOCRClient:
    """
    Wraps Surya OCR v0.17 to extract real word-level bounding boxes from images.
    Outputs the same token format as OllamaOCRClient.extract_tokens_with_bbox():
      list[{text: str, bbox: [x1, y1, x2, y2], page: int}]
    """

    def __init__(self, device: str = "auto", offline: bool = False):
        self.device = device
        self.offline = offline
        self._available: Optional[bool] = None  # None = not yet checked

        if offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
            logger.info("Surya running in offline mode (HF_HUB_OFFLINE=1)")

    def is_available(self) -> bool:
        """Check whether surya-ocr is importable (installed in venv)."""
        if self._available is not None:
            return self._available
        try:
            from surya.foundation import FoundationPredictor  # noqa: F401
            from surya.detection import DetectionPredictor    # noqa: F401
            from surya.recognition import RecognitionPredictor  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            logger.warning(
                "surya-ocr not installed or incomplete. "
                "Install with: pip install surya-ocr. "
                "Falling back to Ollama bbox estimation."
            )
        return self._available

    def extract_tokens(self, image_path: str, page: int = 1) -> list[dict]:
        """
        Run Surya OCR on a single image and return token dicts with real bboxes.

        Returns:
            list of {text, bbox: [x1, y1, x2, y2], page} — same as pipeline expects.
            Returns [] on any failure so the pipeline can fall back gracefully.
        """
        if not self.is_available():
            return []

        try:
            from PIL import Image

            img = Image.open(image_path).convert("RGB")

            # Load (or retrieve cached) predictors
            det_predictor, rec_predictor, device = _load_surya_predictors(self.device)

            # Run full OCR (detection + recognition in one call)
            ocr_results = rec_predictor(
                [img],
                det_predictor=det_predictor,
                return_words=False,   # line-level results
                sort_lines=True,
            )

            tokens = []
            if not ocr_results:
                logger.warning(f"Surya returned no results for page {page}")
                return []

            page_result = ocr_results[0]  # one image → one result

            for line in page_result.text_lines:
                text = line.text.strip()
                if not text:
                    continue

                # Surya v0.17 bbox is a flat list [x1, y1, x2, y2]
                bbox = _normalise_bbox(line.bbox)
                if bbox is None:
                    continue

                tokens.append({
                    "text": text,
                    "bbox": bbox,
                    "page": page,
                })

            logger.info(
                f"Surya extracted {len(tokens)} tokens from page {page}",
                extra={"step": "surya_extraction", "page": page},
            )
            return tokens

        except Exception as e:
            logger.warning(
                f"Surya extraction failed for page {page}: {e}. "
                "Returning [] — pipeline will fall back to Ollama.",
                extra={"step": "surya_extraction", "error": str(e)},
            )
            return []


# ──────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────

def _normalise_bbox(raw_bbox) -> Optional[list[float]]:
    """
    Normalise Surya bbox to flat [x1, y1, x2, y2].
    Handles:
      - Flat list/tuple of 4 numbers: [x1, y1, x2, y2]
      - Polygon list of 4 points:     [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
      - Object with .bbox attribute
    """
    try:
        if isinstance(raw_bbox, (list, tuple)):
            if len(raw_bbox) == 4:
                first = raw_bbox[0]
                if isinstance(first, (int, float)):
                    return [float(v) for v in raw_bbox]
                elif isinstance(first, (list, tuple)) and len(first) == 2:
                    xs = [pt[0] for pt in raw_bbox]
                    ys = [pt[1] for pt in raw_bbox]
                    return [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
        # Pydantic/dataclass model with x1,y1,x2,y2 attributes
        if hasattr(raw_bbox, "x1"):
            return [float(raw_bbox.x1), float(raw_bbox.y1),
                    float(raw_bbox.x2), float(raw_bbox.y2)]
    except Exception:
        pass
    return None
