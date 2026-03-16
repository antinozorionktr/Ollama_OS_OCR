"""
Semantic OCR Pipeline — page-wise processing with two-model architecture.

Pipeline:
  Document Upload → PDF to page images → Per page:
    1. llama3.2-vision:11b → raw text + structural hints
    2. mistral:7b → cleaned text
    3. mistral:7b → recreated layout
  → Store per-page results in DB
"""
import os
import time
from pathlib import Path

from app.utils.ollama_client import OllamaOCRClient
from app.utils.pdf_handler import pdf_to_images
from app.utils.store import get_store
from app.utils.logger import setup_logger
from app.utils.image_processing import preprocess_for_ocr, preprocess_block_cv

logger = setup_logger("docvision.pipeline")


class OCRPipeline:
    """
    Runs the semantic OCR pipeline for a document.
    Processes each page independently through:
      1. Vision extraction (raw text)
      2. Text cleanup (cleaned text)
      3. Layout reconstruction (recreated layout)
    """

    def __init__(self, client: OllamaOCRClient):
        self.client = client
        self.store = get_store()

    def process_document(
        self,
        file_path: str,
        on_progress: callable = None,
        dpi: int = None,
        document_id: int = None,
    ) -> dict:
        """
        Full pipeline entry point.
        Creates a document record, processes each page, saves results.
        Returns dict with document_id, total_pages, processing_time_seconds.
        """
        if dpi is None:
            from app.core.config import get_settings
            dpi = get_settings().ocr_dpi

        start = time.time()
        file_path = str(file_path)
        ext = Path(file_path).suffix.lower()
        filename = Path(file_path).name

        logger.info(f"Pipeline started: {file_path}")

        if on_progress:
            on_progress({"step": "start", "progress_pct": 5, "message": "Processing started..."})

        # ── Convert to page images ──
        if ext == ".pdf":
            image_paths = pdf_to_images(file_path, dpi=dpi)
            cleanup = True
        else:
            image_paths = [file_path]
            cleanup = False

        total_pages = len(image_paths)
        logger.info(f"Document has {total_pages} pages")

        if on_progress:
            on_progress({"step": "pages_detected", "progress_pct": 10, "message": f"Document has {total_pages} pages"})

        # ── Create or Get document record ──
        if document_id is None:
            document_id = self.store.save_document(
                filename=filename,
                file_path=file_path,
                total_pages=total_pages,
            )
        else:
            # Update existing document metadata if needed
            self.store.update_document(
                document_id=document_id,
                total_pages=total_pages,
                error=None,
            )

        # ── Process each page ──
        page_results = []
        for page_idx, img_path in enumerate(image_paths):
            page_num = page_idx + 1
            logger.info(f"Processing page {page_num}/{total_pages}")

            if on_progress:
                base_pct = 10 + (page_idx * 80 // total_pages)
                on_progress({
                    "step": "page_start",
                    "progress_pct": base_pct,
                    "message": f"Processing page {page_num}/{total_pages}...",
                    "current_page": page_num,
                    "total_pages": total_pages,
                })

            try:
                # ── Step 0: Pre-processing & Layout Detection ──
                logger.info(f"  Step 0: Pre-processing & Detecting layout (page {page_num})")
                
                # Pre-process the original image
                preprocessed_img_path = preprocess_for_ocr(img_path)
                
                regions = self.client.detect_layout(preprocessed_img_path)
                logger.info(f"  Detected {len(regions)} logical regions")

                if on_progress:
                    on_progress({"step": "layout_detected", "message": f"Page {page_num}: {len(regions)} regions detected"})

                # ── Step 1: Fragmented Vision Extraction ──
                # If we have regions, extract each separately. Otherwise process the whole page.
                if regions:
                    logger.info(f"  Step 1: Segmented vision extraction ({len(regions)} blocks)")
                    block_texts = []
                    for ridx, region in enumerate(regions):
                        try:
                            # Crop and process region
                            crop_path = self._crop_region(preprocessed_img_path, region["bbox"], page_num, ridx)
                            block_text = self.client.extract_page_text(crop_path)
                            block_texts.append(block_text)
                            # Cleanup crop
                            if os.path.exists(crop_path):
                                os.unlink(crop_path)
                        except Exception as e:
                            logger.warning(f"  Failed to process region {ridx}: {e}")
                    
                    raw_text = "\n\n".join(block_texts)
                else:
                    logger.info(f"  Step 1: Vision extraction (full page)")
                    raw_text = self.client.extract_page_text(preprocessed_img_path)

                if on_progress:
                    step_pct = 10 + (page_idx * 80 // total_pages) + (25 // total_pages)
                    on_progress({"step": "vision_done", "progress_pct": step_pct, "message": f"Page {page_num}: Text extracted"})

                # Step 2: Text cleanup → cleaned text
                logger.info(f"  Step 2: Text cleanup (page {page_num})")
                cleaned_text = self.client.clean_text(raw_text)

                if on_progress:
                    step_pct = 10 + (page_idx * 80 // total_pages) + (50 // total_pages)
                    on_progress({"step": "cleanup_done", "progress_pct": step_pct, "message": f"Page {page_num}: Text cleaned"})

                # Final deduplication guard (redundant but safe)
                raw_text = self.client.remove_duplicate_blocks(raw_text)
                cleaned_text = self.client.remove_duplicate_blocks(cleaned_text)

                # Step 3: Layout reconstruction → recreated layout
                logger.info(f"  Step 3: Layout reconstruction (page {page_num})")
                recreated_layout = self.client.reconstruct_layout(raw_text, regions=regions)

                if on_progress:
                    step_pct = 10 + (page_idx * 80 // total_pages) + (60 // total_pages)
                    on_progress({"step": "layout_done", "progress_pct": step_pct, "message": f"Page {page_num}: Layout reconstructed"})

                # Step 4: Structured Data Extraction (key-value pairs)
                logger.info(f"  Step 4: Structured data extraction (page {page_num})")
                structured_data = self.client.extract_structured_data(raw_text, regions=regions)

                if on_progress:
                    step_pct = 10 + ((page_idx + 1) * 80 // total_pages)
                    on_progress({"step": "extraction_done", "progress_pct": step_pct, "message": f"Page {page_num}: Entities extracted"})

                # Save page result to DB
                self.store.save_page_result(
                    document_id=document_id,
                    page_number=page_num,
                    raw_text=raw_text,
                    cleaned_text=cleaned_text,
                    recreated_layout=recreated_layout,
                    structured_data=structured_data,
                )

                page_results.append({
                    "page_number": page_num,
                    "raw_text": raw_text,
                    "cleaned_text": cleaned_text,
                    "recreated_layout": recreated_layout,
                    "structured_data": structured_data,
                })

                logger.info(f"  Page {page_num} complete")

            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                # Save partial result
                self.store.save_page_result(
                    document_id=document_id,
                    page_number=page_num,
                    raw_text=f"[Error: {str(e)}]",
                )
                page_results.append({
                    "page_number": page_num,
                    "error": str(e),
                })

        # ── Cleanup temp images ──
        if cleanup:
            for p in image_paths:
                try:
                    os.unlink(p)
                    # Also cleanup preprocessed page
                    if os.path.exists(p.replace(".png", "_preprocessed.png")):
                        os.unlink(p.replace(".png", "_preprocessed.png"))
                except OSError:
                    pass

        # ── Update document with processing time ──
        elapsed = round(time.time() - start, 2)
        self.store.update_document(
            document_id=document_id,
            processing_time_seconds=elapsed,
        )

        if on_progress:
            on_progress({"step": "complete", "progress_pct": 100, "message": "Processing complete"})

        logger.info(f"Pipeline complete: {elapsed}s | {total_pages} pages")

        return {
            "document_id": document_id,
            "filename": filename,
            "total_pages": total_pages,
            "processing_time_seconds": elapsed,
            "pages": page_results,
        }

    def _preprocess_block(self, img):
        """Enhance image for better OCR: grayscale, contrast, sharpness."""
        from PIL import ImageOps, ImageEnhance
        
        # 1. Grayscale
        img = ImageOps.grayscale(img)
        
        # 2. Contrast enhancement
        enhencer = ImageEnhance.Contrast(img)
        img = enhencer.enhance(1.8)
        
        # 3. Brightness normalization
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)

        # 4. Sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.5)
        
        return img

    def _crop_region(self, image_path: str, bbox: list[float], page_num: int, region_idx: int) -> str:
        """Helper to crop a region and save it to a temp file."""
        from PIL import Image
        import tempfile
        
        with Image.open(image_path) as img:
            w, h = img.size
            # Normalize coordinates [0-1000] -> actual pixels
            x1 = int(bbox[0] * w / 1000)
            y1 = int(bbox[1] * h / 1000)
            x2 = int(bbox[2] * w / 1000)
            y2 = int(bbox[3] * h / 1000)
            
            # Ensure valid box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            crop = img.crop((x1, y1, x2, y2))
            
            # Preprocessing: Enhance for OCR
            crop = preprocess_block_cv(crop)
            
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=f"_p{page_num}_r{region_idx}.png"
            )
            crop.save(tmp.name, "PNG")
            tmp.close()
            return tmp.name
