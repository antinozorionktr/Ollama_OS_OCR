"""
OCR Text Cleaner
Cleans raw OCR output by removing artifacts, fixing spacing,
merging broken lines, and producing structured clean text.
"""

import re
from typing import Optional


def clean_ocr_text(raw_text: str) -> str:
    """
    Clean raw OCR text by removing common artifacts and normalizing formatting.
    Returns clean, human-readable text.
    """
    if not raw_text:
        return ""

    text = raw_text

    # ── Remove page separators we added ──
    text = re.sub(r"---\s*Page\s+\d+\s*---\n?", "", text)

    # ── Remove excessive dashes / underscores / equals used as dividers ──
    text = re.sub(r"[-_=]{3,}", "", text)

    # ── Remove stray special characters that OCR commonly produces ──
    # Pipes, tildes, carets used as noise (not within words)
    text = re.sub(r"(?<!\w)[|~^`\\](?!\w)", "", text)

    # ── Remove garbled character sequences (non-ASCII noise) ──
    # Keep common accented chars, currency symbols, and unicode punctuation
    text = re.sub(r"[^\x20-\x7E\n\t\u00A0-\u024F\u2000-\u206F\u20A0-\u20CF\u2100-\u214F₹€£¥°±×÷©®™•–—''""…]", "", text)

    # ── Fix bullet artifacts: replace weird bullet-like chars with clean bullets ──
    text = re.sub(r"^\s*[►▸▪▫◦◆◇●○■□➤➢>»]\s*", "• ", text, flags=re.MULTILINE)

    # ── Normalize whitespace ──
    # Replace tabs with spaces
    text = text.replace("\t", "  ")
    # Collapse multiple spaces into one (preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)
    # Remove spaces at start/end of lines
    text = re.sub(r"^ +| +$", "", text, flags=re.MULTILINE)

    # ── Merge broken lines (OCR often breaks mid-sentence) ──
    # If a line ends with a lowercase letter and next starts with lowercase, merge
    text = re.sub(r"([a-z,;])\n([a-z])", r"\1 \2", text)

    # ── Fix hyphenated line breaks (word- \n break → wordbreak) ──
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # ── Remove excessive blank lines (keep max 2) ──
    text = re.sub(r"\n{3,}", "\n\n", text)

    # ── Clean up common OCR misreads ──
    # Fix doubled periods
    text = re.sub(r"\.{2,}", ".", text)
    # Fix space before punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    # Fix missing space after punctuation (if followed by uppercase)
    text = re.sub(r"([.,;:!?])([A-Z])", r"\1 \2", text)

    # ── Remove leading/trailing noise ──
    text = text.strip()

    return text


def extract_sections(clean_text: str) -> list[dict]:
    """
    Parse cleaned text into sections based on detected headings and structure.
    Returns a list of dicts: [{"type": "heading"|"paragraph"|"list_item"|"table_row", "text": "...", "level": int}]
    """
    if not clean_text:
        return []

    lines = clean_text.split("\n")
    sections = []
    current_para_lines = []

    def flush_paragraph():
        if current_para_lines:
            text = " ".join(current_para_lines).strip()
            if text:
                sections.append({"type": "paragraph", "text": text, "level": 0})
            current_para_lines.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            continue

        # ── Detect headings: ALL CAPS lines, short lines ending without punctuation ──
        is_heading = False
        if stripped.isupper() and len(stripped) > 3 and len(stripped) < 100:
            is_heading = True
            level = 1
        elif (
            len(stripped) < 80
            and not stripped.endswith((",", ".", ";", ":"))
            and stripped[0].isupper()
            and not stripped.startswith("•")
            and re.match(r"^(\d+[\.\)]\s+|[A-Z][\.\)]\s+|Section\s+|Article\s+|Part\s+|Chapter\s+)", stripped)
        ):
            is_heading = True
            level = 2

        if is_heading:
            flush_paragraph()
            sections.append({"type": "heading", "text": stripped, "level": level})
            continue

        # ── Detect list items ──
        if re.match(r"^[•\-\*]\s+", stripped):
            flush_paragraph()
            item_text = re.sub(r"^[•\-\*]\s+", "", stripped)
            sections.append({"type": "list_item", "text": item_text, "level": 0})
            continue

        # ── Detect numbered list ──
        if re.match(r"^\d+[\.\)]\s+", stripped) and len(stripped) < 200:
            flush_paragraph()
            sections.append({"type": "numbered_item", "text": stripped, "level": 0})
            continue

        # ── Regular paragraph line ──
        current_para_lines.append(stripped)

    flush_paragraph()
    return sections


def structured_data_to_sections(structured_data: dict, doc_type: str) -> list[dict]:
    """
    Convert structured extraction data (generic or doc-specific) into
    Word document sections.
    Supports the new universal schema: document_metadata, fields,
    tables, checkboxes, signatures, stamps, notes.
    """
    sections = []

    # ── Document Title ──
    sections.append({"type": "heading", "text": "Document Details", "level": 1})

    if not structured_data:
        sections.append({"type": "paragraph", "text": "No structured data extracted.", "level": 0})
        return sections

    # ── Document Metadata ──
    metadata = structured_data.get("document_metadata", {})
    if not metadata:
        # Fallback: check for top-level metadata keys
        for k in ("document_type", "title", "date", "document_id", "issuing_organization", "involved_entities"):
            if structured_data.get(k):
                metadata[k] = structured_data[k]

    if metadata:
        sections.append({"type": "heading", "text": "Document Information", "level": 2})
        for key, value in metadata.items():
            if value is not None and value not in ("", "null"):
                label = key.replace("_", " ").title()
                sections.append({"type": "key_value", "label": label, "value": str(value),
                                  "text": f"{label}: {value}", "level": 0})

    # ── Form Fields ──
    fields = structured_data.get("fields", {})
    if fields and isinstance(fields, dict):
        sections.append({"type": "heading", "text": "Fields", "level": 2})
        for key, value in fields.items():
            if value is not None and value not in ("", "null"):
                label = key.replace("_", " ").title()
                sections.append({"type": "key_value", "label": label, "value": str(value),
                                  "text": f"{label}: {value}", "level": 0})

    # ── Tables ──
    tables = structured_data.get("tables", [])
    if tables and isinstance(tables, list):
        for tbl in tables:
            table_name = tbl.get("table_name", "Table") if isinstance(tbl, dict) else "Table"
            rows = tbl.get("rows", tbl) if isinstance(tbl, dict) else tbl
            if rows and isinstance(rows, list):
                sections.append({"type": "heading", "text": table_name, "level": 2})
                sections.append({"type": "table", "data": rows, "level": 0, "text": ""})

    # ── Checkboxes ──
    checkboxes = structured_data.get("checkboxes", {})
    if checkboxes and isinstance(checkboxes, dict):
        sections.append({"type": "heading", "text": "Checkboxes / Options", "level": 2})
        for key, value in checkboxes.items():
            label = key.replace("_", " ").title()
            checked = "[✓]" if value else "[ ]"
            sections.append({"type": "key_value", "label": label, "value": str(value),
                              "text": f"{checked} {label}", "level": 0})

    # ── Signatures ──
    signatures = structured_data.get("signatures", [])
    if signatures:
        sections.append({"type": "heading", "text": "Signatures", "level": 2})
        for sig in signatures:
            if isinstance(sig, dict):
                sig_label = sig.get("label", "Signature")
                present = sig.get("present", True)
                sections.append({"type": "paragraph",
                                  "text": f"{sig_label}: {'__________________' if present else 'N/A'}",
                                  "level": 0})
            else:
                sections.append({"type": "paragraph", "text": f"Signature: {sig}", "level": 0})

    # ── Stamps ──
    stamps = structured_data.get("stamps", [])
    if stamps:
        sections.append({"type": "heading", "text": "Stamps & Seals", "level": 2})
        for stamp in stamps:
            sections.append({"type": "paragraph", "text": f"[STAMP: {stamp}]", "level": 0})

    # ── Notes ──
    notes = structured_data.get("notes", [])
    if notes:
        sections.append({"type": "heading", "text": "Notes", "level": 2})
        for note in notes:
            sections.append({"type": "list_item", "text": str(note), "level": 0})

    # ── Remaining unhandled top-level fields ──
    known_keys = {"document_metadata", "fields", "tables", "checkboxes",
                  "signatures", "stamps", "notes",
                  "document_type", "title", "date", "document_id",
                  "issuing_organization", "involved_entities"}
    remaining = {k: v for k, v in structured_data.items()
                 if k not in known_keys and not k.startswith("_")
                 and v is not None and v not in ("", "null")}
    if remaining:
        sections.append({"type": "heading", "text": "Additional Information", "level": 2})
        for key, value in remaining.items():
            label = key.replace("_", " ").title()
            if isinstance(value, (list, dict)):
                sections.append({"type": "key_value", "label": label,
                                  "value": str(value), "text": f"{label}: {value}", "level": 0})
            else:
                sections.append({"type": "key_value", "label": label,
                                  "value": str(value), "text": f"{label}: {value}", "level": 0})

    return sections

