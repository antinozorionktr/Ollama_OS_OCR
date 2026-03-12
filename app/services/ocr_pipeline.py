"""
7-Step Structured OCR Extraction Pipeline

Step 1: Token Normalization
Step 2: Line Reconstruction
Step 3: Block/Paragraph Detection
Step 4: Table Detection
Step 5: Semantic Field Extraction
Step 6: Bounding Box Linking
Step 7: Final Structured Output
"""

import re
import time
from pathlib import Path
from typing import Optional

from app.utils.ollama_client import OllamaOCRClient
from app.utils.pdf_handler import pdf_to_images
from app.utils.logger import setup_logger

logger = setup_logger("docvision.pipeline")

# Lazy import — only available when surya-ocr is installed
try:
    from app.utils.surya_client import SuryaOCRClient
    _SURYA_IMPORTABLE = True
except ImportError:
    _SURYA_IMPORTABLE = False
    SuryaOCRClient = None



# ───────────────────────────────────────────────
# Pipeline core class
# ───────────────────────────────────────────────

class OCRPipeline:
    """
    Runs the 7-step structured extraction pipeline for a document.
    Token/bbox extraction uses Surya OCR when available (real pixel coords),
    falling back to Ollama vision model estimation.
    """

    def __init__(self, client: OllamaOCRClient, surya_client=None):
        self.client = client
        # Accept a SuryaOCRClient instance or None
        self.surya_client = surya_client

    def run(
        self,
        file_path: str,
    ) -> dict:
        """
        Full pipeline entry point.
        Returns structured extraction dict compatible with ExtractedDocument schema.
        """
        start = time.time()
        file_path = str(file_path)
        ext = Path(file_path).suffix.lower()

        logger.info(f"Pipeline started: {file_path}")

        # Get image paths for each page
        if ext == ".pdf":
            image_paths = pdf_to_images(file_path)
            cleanup = True
        else:
            image_paths = [file_path]
            cleanup = False

        # Collect all tokens across pages
        all_tokens: list[dict] = []
        for page_idx, img_path in enumerate(image_paths):
            page_num = page_idx + 1
            logger.info(f"Extracting tokens: page {page_num}/{len(image_paths)}")
            try:
                # ── Prefer Surya (real bboxes) over Ollama (estimated bboxes) ──
                if self.surya_client is not None:
                    tokens = self.surya_client.extract_tokens(img_path, page=page_num)
                    if tokens:
                        logger.info(
                            f"Surya extracted {len(tokens)} tokens for page {page_num}",
                            extra={"step": "token_extraction", "source": "surya"},
                        )
                    else:
                        # Surya returned nothing — fall back to Ollama
                        logger.warning(
                            f"Surya returned 0 tokens for page {page_num}; "
                            "falling back to Ollama.",
                            extra={"step": "token_extraction", "source": "ollama_fallback"},
                        )
                        tokens = self.client.extract_tokens_with_bbox(img_path, page=page_num)
                else:
                    tokens = self.client.extract_tokens_with_bbox(img_path, page=page_num)

                all_tokens.extend(tokens)
            except Exception as e:
                logger.error(f"Token extraction failed for page {page_num}: {e}")

        logger.info(f"Total tokens extracted: {len(all_tokens)}")

        # ─── Step 1: Normalize ───
        tokens = _step1_normalize(all_tokens)

        # ─── Step 2: Reconstruct Lines ───
        lines = _step2_reconstruct_lines(tokens)

        # ─── Step 3: Detect Blocks ───
        blocks = _step3_detect_blocks(lines)

        # ─── Step 4: Detect Tables ───
        tables = _step4_detect_tables(lines)

        # ─── Step 5: Semantic Field Extraction (Universal) ───
        semantic = _step5_extract_semantics(blocks)

        # ─── Step 6: BBox Linking ───
        fields = _step6_link_bboxes(semantic, tokens)

        # ─── Step 7: Build Final Output ───
        result = _step7_build_output(fields, tables, tokens, len(image_paths))

        if cleanup:
            import os
            for p in image_paths:
                try:
                    os.unlink(p)
                except OSError:
                    pass

        elapsed = round(time.time() - start, 2)
        result["_processing_time"] = elapsed
        logger.info(f"Pipeline complete: {elapsed}s")
        return result


# ───────────────────────────────────────────────
# Step Implementations
# ───────────────────────────────────────────────

def _step1_normalize(tokens: list[dict]) -> list[dict]:
    """Step 1: Trim, filter empty, sort by page→y→x."""
    normalized = []
    for t in tokens:
        text = str(t.get("text", "")).strip()
        if not text:
            continue
        bbox = t.get("bbox", [0, 0, 0, 0])
        if len(bbox) < 4:
            continue
        normalized.append({
            "text": text,
            "bbox": [float(b) for b in bbox],
            "page": int(t.get("page", 1)),
        })
    # Sort by page, then y1, then x1
    normalized.sort(key=lambda t: (t["page"], t["bbox"][1], t["bbox"][0]))
    return normalized


def _step2_reconstruct_lines(tokens: list[dict]) -> list[dict]:
    """
    Step 2: Group tokens into text lines by proximity of center_y.
    Returns list of line dicts with merged text and bbox.
    """
    if not tokens:
        return []

    # Compute average token height for threshold
    heights = [t["bbox"][3] - t["bbox"][1] for t in tokens if t["bbox"][3] > t["bbox"][1]]
    avg_h = max((sum(heights) / len(heights)) if heights else 20, 10)
    threshold = avg_h * 0.6

    # Group by page first, then y proximity
    from itertools import groupby
    lines = []

    def center_y(t):
        return (t["bbox"][1] + t["bbox"][3]) / 2.0

    for page_num, page_tokens in groupby(tokens, key=lambda t: t["page"]):
        page_list = list(page_tokens)
        if not page_list:
            continue

        current_line: list[dict] = [page_list[0]]
        anchor_y = center_y(page_list[0])

        for tok in page_list[1:]:
            cy = center_y(tok)
            if abs(cy - anchor_y) <= threshold:
                current_line.append(tok)
            else:
                lines.append(_merge_line(current_line, page_num))
                current_line = [tok]
                anchor_y = cy

        if current_line:
            lines.append(_merge_line(current_line, page_num))

    return lines


def _merge_line(tokens: list[dict], page: int) -> dict:
    """Merge token list into single line dict."""
    tokens = sorted(tokens, key=lambda t: t["bbox"][0])
    text = " ".join(t["text"] for t in tokens)
    x1 = min(t["bbox"][0] for t in tokens)
    y1 = min(t["bbox"][1] for t in tokens)
    x2 = max(t["bbox"][2] for t in tokens)
    y2 = max(t["bbox"][3] for t in tokens)
    return {"text": text, "tokens": tokens, "bbox": [x1, y1, x2, y2], "page": page}


def _step3_detect_blocks(lines: list[dict]) -> list[dict]:
    """
    Step 3: Group lines into semantic blocks. Classify block type.
    """
    blocks = []
    if not lines:
        return blocks

    # Compute avg line height for gap threshold
    heights = [l["bbox"][3] - l["bbox"][1] for l in lines]
    avg_h = max((sum(heights) / len(heights)) if heights else 20, 12)
    gap_threshold = avg_h * 1.5

    current_block = [lines[0]]
    for line in lines[1:]:
        prev = current_block[-1]
        gap = line["bbox"][1] - prev["bbox"][3]
        same_page = line["page"] == prev["page"]
        if same_page and gap < gap_threshold:
            current_block.append(line)
        else:
            blocks.append(_classify_block(current_block))
            current_block = [line]

    if current_block:
        blocks.append(_classify_block(current_block))

    return blocks


def _classify_block(lines: list[dict]) -> dict:
    """Classify a block of lines as header, table, footer, paragraph, etc."""
    text = " ".join(l["text"] for l in lines)
    upper_ratio = sum(1 for c in text if c.isupper()) / max(len(text.replace(" ", "")), 1)

    block_type = "paragraph"
    if len(lines) == 1 and upper_ratio > 0.6:
        block_type = "header"
    elif any(kw in text.lower() for kw in ["description", "qty", "quantity", "amount", "unit price"]):
        block_type = "table_header"
    elif any(kw in text.lower() for kw in ["thank you", "page", "footer"]):
        block_type = "footer"
    elif re.search(r'\[\s*[xX]?\s*\]', text):
        block_type = "checkbox"
    elif "signature" in text.lower():
        block_type = "signature"

    page = lines[0]["page"]
    x1 = min(l["bbox"][0] for l in lines)
    y1 = min(l["bbox"][1] for l in lines)
    x2 = max(l["bbox"][2] for l in lines)
    y2 = max(l["bbox"][3] for l in lines)

    return {
        "type": block_type,
        "text": text,
        "lines": lines,
        "bbox": [x1, y1, x2, y2],
        "page": page,
    }


def _step4_detect_tables(lines: list[dict]) -> list[dict]:
    """
    Step 4: Detect tables by finding lines with repeating column X positions.
    Returns list of table dicts with rows of cells.
    """
    tables = []
    if len(lines) < 3:
        return tables

    # Cluster token x-midpoints to find column positions
    all_x_mids = []
    for line in lines:
        for tok in line.get("tokens", []):
            mid_x = (tok["bbox"][0] + tok["bbox"][2]) / 2
            all_x_mids.append((mid_x, tok))

    if not all_x_mids:
        return tables

    # Simple: if >3 lines share similar column spacing, treat as table
    col_threshold = 40
    lines_with_multi_tokens = [l for l in lines if len(l.get("tokens", [])) >= 3]

    if len(lines_with_multi_tokens) < 2:
        return tables

    # Guess column positions from header-like lines
    header_line = None
    for line in lines:
        text_lower = line["text"].lower()
        if any(kw in text_lower for kw in ["description", "qty", "amount", "unit price", "price"]):
            header_line = line
            break

    if not header_line:
        return tables

    # Build column x-positions from header tokens
    col_positions = sorted([
        (tok["bbox"][0] + tok["bbox"][2]) / 2
        for tok in header_line.get("tokens", [])
    ])

    header_y2 = header_line["bbox"][3]
    row_lines = [l for l in lines if l["bbox"][1] > header_y2 and l["page"] == header_line["page"]]

    rows = []
    for line in row_lines[:20]:   # cap rows
        # Skip footer-ish lines
        if any(kw in line["text"].lower() for kw in ["subtotal", "tax", "total", "thank"]):
            break
        cells = _assign_tokens_to_columns(line.get("tokens", []), col_positions)
        if any(cells):
            rows.append(cells)

    if rows:
        tables.append({
            "columns": col_positions,
            "header": [t["text"] for t in header_line.get("tokens", [])],
            "rows": rows,
            "page": header_line["page"],
            "bbox": header_line["bbox"],
        })

    return tables


def _assign_tokens_to_columns(tokens: list[dict], col_positions: list[float]) -> list[str]:
    """Assign each token to its nearest column."""
    cells = [""] * len(col_positions)
    for tok in tokens:
        mid_x = (tok["bbox"][0] + tok["bbox"][2]) / 2
        nearest_col = min(range(len(col_positions)), key=lambda i: abs(col_positions[i] - mid_x))
        cells[nearest_col] = (cells[nearest_col] + " " + tok["text"]).strip()
    return cells


def _step5_extract_semantics(blocks: list[dict]) -> dict:
    """
    Step 5: Universal field extraction — works on any document type.
    Extracts: labeled fields (Label: Value), dates, monetary amounts,
    reference/ID numbers, headers, emails, phone numbers.
    """
    all_text = "\n".join(b["text"] for b in blocks)
    fields: dict[str, dict] = {}

    # ── 1. Label:Value pairs (most universal pattern) ──
    label_val_pat = r'^([A-Za-z][A-Za-z\s\.]{1,38}[A-Za-z])\s*[:\-]\s*(.{1,120})$'
    for m in re.finditer(label_val_pat, all_text, re.MULTILINE):
        label = m.group(1).strip().lower().replace(" ", "_").replace(".", "")
        value = m.group(2).strip()
        if label and value and label not in fields:
            fields[label] = {"raw_value": value, "raw_text": m.group(0).strip()}

    # ── 2. Dates (all common formats) ──
    date_pat = r'(\d{4}[\-/]\d{2}[\-/]\d{2}|\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s*\d{4})'
    dates = re.findall(date_pat, all_text, re.IGNORECASE)
    for idx, d in enumerate(dates[:5]):
        key = "date" if idx == 0 else f"date_{idx + 1}"
        if key not in fields:
            fields[key] = {"raw_value": d, "raw_text": d}

    # ── 3. Monetary totals ──
    total_pat = r'(?:total|amount\s*due|grand\s*total|balance\s*due).*?([\$€£₹]\s*[\d,]+\.?\d*)'
    m = re.search(total_pat, all_text, re.IGNORECASE)
    if m and "total" not in fields:
        fields["total"] = {"raw_value": m.group(1).strip(), "raw_text": m.group(0).strip()}

    # ── 4. Any currency value line ──
    currency_pat = r'([\$€£₹]\s*[\d,]+\.\d{2})'
    amounts = re.findall(currency_pat, all_text)
    for idx, amt in enumerate(amounts[:8]):
        key = f"amount_{idx + 1}"
        if key not in fields:
            fields[key] = {"raw_value": amt, "raw_text": amt}

    # ── 5. Reference / ID numbers ──
    ref_pat = r'(?:No|Number|#|Ref|ID|Code)[.:\s]+([A-Z0-9][A-Z0-9\-\/]{2,30})'
    for m in re.finditer(ref_pat, all_text, re.IGNORECASE):
        val = m.group(1).strip()
        key = "reference_number"
        if key not in fields:
            fields[key] = {"raw_value": val, "raw_text": m.group(0).strip()}

    # ── 6. Email addresses ──
    email_pat = r'[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pat, all_text)
    for idx, e in enumerate(emails[:3]):
        key = "email" if idx == 0 else f"email_{idx + 1}"
        if key not in fields:
            fields[key] = {"raw_value": e, "raw_text": e}

    # ── 7. Phone numbers ──
    phone_pat = r'(?:\+?\d[\d\s\-\.]{7,16}\d)'
    phones = re.findall(phone_pat, all_text)
    for idx, ph in enumerate(phones[:3]):
        key = "phone" if idx == 0 else f"phone_{idx + 1}"
        if key not in fields:
            fields[key] = {"raw_value": ph.strip(), "raw_text": ph.strip()}

    # ── 8. First header block as title ──
    header_block = next((b for b in blocks if b["type"] == "header"), None)
    if header_block and "title" not in fields:
        fields["title"] = {"raw_value": header_block["text"], "raw_text": header_block["text"]}

    return fields


def _extract_labeled_field(text: str, fields: dict, key: str, patterns: list[str]):
    """Try each regex pattern and populate field if found."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            val = m.group(1).strip() if m.lastindex else m.group(0).strip()
            fields[key] = {"raw_value": val, "raw_text": m.group(0).strip()}
            return


def _step6_link_bboxes(fields: dict, tokens: list[dict]) -> dict:
    """
    Step 6: For each extracted field value, find matching OCR tokens
    and compute merged bounding box. Assign confidence.
    """
    linked: dict[str, dict] = {}

    for key, info in fields.items():
        raw_val = str(info.get("raw_value", "")).strip()
        if not raw_val:
            linked[key] = {"value": None, "bbox": None, "page": 1, "confidence": "LOW"}
            continue

        # Find matching tokens
        matched = _find_matching_tokens(raw_val, tokens)

        if matched:
            bbox = _merge_bboxes([t["bbox"] for t in matched])
            page = matched[0]["page"]
            conf = "HIGH" if len(matched) > 1 else "MEDIUM"
        else:
            bbox = None
            page = 1
            conf = "LOW"

        linked[key] = {
            "value": raw_val,
            "bbox": bbox,
            "page": page,
            "confidence": conf,
        }

    return linked


def _find_matching_tokens(value: str, tokens: list[dict]) -> list[dict]:
    """Find OCR tokens whose combined text matches the field value."""
    value_parts = value.split()
    matched = []
    for tok in tokens:
        if any(part.lower() in tok["text"].lower() for part in value_parts):
            matched.append(tok)
    # Limit to spatially coherent cluster
    if matched:
        first = matched[0]
        coherent = [t for t in matched if abs(t["bbox"][1] - first["bbox"][1]) < 60]
        return coherent[:len(value_parts) + 3]
    return []


def _merge_bboxes(bboxes: list[list[float]]) -> list[float]:
    """Merge a list of bboxes into a single encompassing bbox."""
    x1 = min(b[0] for b in bboxes)
    y1 = min(b[1] for b in bboxes)
    x2 = max(b[2] for b in bboxes)
    y2 = max(b[3] for b in bboxes)
    return [x1, y1, x2, y2]


def _step7_build_output(
    fields: dict,
    tables: list[dict],
    tokens: list[dict],
    pages: int,
) -> dict:
    """
    Step 7: Assemble final structured output compatible with ExtractedDocument schema.
    """
    # Convert fields to FieldValue schema format
    output_fields: dict = {}
    for key, info in fields.items():
        output_fields[key] = {
            "value": info.get("value"),
            "bbox": info.get("bbox"),
            "page": info.get("page", 1),
            "confidence": info.get("confidence", "LOW"),
        }

    # Convert table rows to line items (for invoices)
    line_items = []
    for table in tables:
        header = [h.lower().strip() for h in table.get("header", [])]
        for row in table.get("rows", []):
            if not any(row):
                continue
            item: dict = {}
            for col_idx, cell_val in enumerate(row):
                if col_idx < len(header):
                    col_name = header[col_idx]
                    # Map column names to standard fields
                    if any(kw in col_name for kw in ["desc", "item", "service"]):
                        std_key = "description"
                    elif any(kw in col_name for kw in ["qty", "quantity", "units"]):
                        std_key = "qty"
                    elif any(kw in col_name for kw in ["unit", "price", "rate"]):
                        std_key = "unit_price"
                    elif any(kw in col_name for kw in ["amount", "total", "subtotal"]):
                        std_key = "total"
                    else:
                        std_key = col_name.replace(" ", "_")[:20]
                    item[std_key] = {
                        "value": cell_val,
                        "bbox": None,
                        "page": table.get("page", 1),
                        "confidence": "MEDIUM" if cell_val else "LOW",
                    }
            if item:
                line_items.append(item)

    return {
        "document_type": "document",
        "fields": output_fields,
        "line_items": line_items,
        "raw_tokens": tokens,
        "pages": pages,
    }
