"""
Markdown Preparer — Formats structured OCR extraction results into a clean Markdown document.
"""

from typing import Any, Optional

def prepare_markdown(structured_data: dict, raw_text: Optional[str] = None) -> str:
    """
    Convert structured extraction data (fields and line items) into a formatted Markdown string.
    Falls back to raw_text if structured_data is empty.
    """
    if not structured_data and not raw_text:
        return "No extraction data available."

    md = []
    
    # 1. Document Title
    if "title" in structured_data:
        title = structured_data["title"]
        if isinstance(title, dict):
            title = title.get("value", "Document")
        md.append(f"# {title}")
        md.append("")

    # 2. General Fields
    metadata = structured_data.get("document_metadata", {}) or structured_data.get("fields", {})
    if not metadata:
        # Fallback: find any non-nested fields
        metadata = {k: v for k, v in structured_data.items() if not isinstance(v, (list, dict))}

    field_entries = []
    for key, val in metadata.items():
        if key.lower() == "title" or not val:
            continue
        label = key.replace("_", " ").title()
        field_entries.append(f"**{label}:** {val}")

    if field_entries:
        md.append("## Document Information")
        md.extend(field_entries)
        md.append("")

    # 3. Tables / Line Items
    tables = structured_data.get("tables", [])
    if not tables and "line_items" in structured_data:
        tables = [{"table_name": "Line Items", "rows": structured_data["line_items"]}]
    
    if tables:
        for tbl in tables:
            name = tbl.get("table_name", "Table")
            rows = tbl.get("rows", [])
            if rows:
                md.append(f"## {name}")
                # Render table
                headers = rows[0].keys()
                header_line = "| " + " | ".join(headers) + " |"
                sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                md.append(header_line)
                md.append(sep_line)
                for row in rows:
                    md.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
                md.append("")

    # 4. Extracted Notes / Others
    for key in ["notes", "stamps", "signatures"]:
        items = structured_data.get(key, [])
        if items:
            md.append(f"## {key.title()}")
            for item in items:
                md.append(f"- {item}")
            md.append("")

    # 5. Raw Text fallback (only if very little structured data)
    if raw_text and len(md) < 5:
        md.append("## Extracted Text")
        md.append(raw_text)

    return "\n".join(md)
