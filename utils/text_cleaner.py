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
    Convert structured extraction data into clean document sections
    suitable for Word document generation.
    """
    sections = []

    # Title based on doc type
    type_titles = {
        "invoice": "Invoice Details",
        "contract": "Contract Details",
        "crac": "CRAC Document Details",
    }
    sections.append({"type": "heading", "text": type_titles.get(doc_type, "Document Details"), "level": 1})

    if not structured_data:
        sections.append({"type": "paragraph", "text": "No structured data extracted.", "level": 0})
        return sections

    # ── Group fields into logical sections ──
    field_groups = {
        "invoice": {
            "General Information": ["invoice_number", "invoice_date", "due_date", "currency", "payment_terms"],
            "Vendor Details": ["vendor_name", "vendor_address", "vendor_gstin"],
            "Customer Details": ["customer_name", "customer_address", "customer_gstin"],
            "Financial Summary": ["subtotal", "tax_amount", "total_amount"],
        },
        "contract": {
            "Contract Information": ["contract_title", "contract_number", "effective_date", "expiration_date", "governing_law"],
            "Party 1": ["party_1_name", "party_1_role"],
            "Party 2": ["party_2_name", "party_2_role"],
            "Terms": ["contract_value", "currency", "payment_terms", "termination_clause_summary"],
        },
        "crac": {
            "Document Information": ["document_title", "document_number", "date_issued"],
            "Entity Details": ["entity_name", "entity_type", "entity_id"],
            "Risk Assessment": ["risk_rating", "credit_score", "credit_limit", "outstanding_amount"],
            "Compliance": ["compliance_status", "review_date", "reviewer_name", "approval_status"],
        },
    }

    groups = field_groups.get(doc_type, {})
    used_keys = set()

    for group_name, field_keys in groups.items():
        group_has_data = False
        group_fields = []

        for key in field_keys:
            value = structured_data.get(key)
            if value is not None and value != "" and value != "null":
                group_has_data = True
                label = key.replace("_", " ").title()
                group_fields.append({"label": label, "value": str(value)})
                used_keys.add(key)

        if group_has_data:
            sections.append({"type": "heading", "text": group_name, "level": 2})
            for field in group_fields:
                sections.append({
                    "type": "key_value",
                    "text": f"{field['label']}: {field['value']}",
                    "label": field["label"],
                    "value": field["value"],
                    "level": 0,
                })

    # ── Handle list fields (line_items, key_obligations, etc.) ──
    list_fields = {
        "line_items": "Line Items",
        "key_obligations": "Key Obligations",
        "key_findings": "Key Findings",
        "recommendations": "Recommendations",
    }
    for key, title in list_fields.items():
        value = structured_data.get(key)
        if value and isinstance(value, list) and len(value) > 0:
            used_keys.add(key)
            sections.append({"type": "heading", "text": title, "level": 2})
            if isinstance(value[0], dict):
                # Table data (e.g. line items)
                sections.append({"type": "table", "data": value, "level": 0, "text": ""})
            else:
                for item in value:
                    if item and str(item).strip():
                        sections.append({"type": "list_item", "text": str(item).strip(), "level": 0})

    # ── Remaining fields ──
    remaining = {k: v for k, v in structured_data.items()
                 if k not in used_keys and not k.startswith("_")
                 and v is not None and v != "" and v != "null"}
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