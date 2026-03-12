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
    fields_to_skip = ["title"]
    field_entries = []
    for key, info in structured_data.items():
        if key in fields_to_skip:
            continue
        
        val = info
        if isinstance(info, dict):
            val = info.get("value")
        
        if val:
            label = key.replace("_", " ").title()
            field_entries.append(f"**{label}:** {val}")

    if field_entries:
        md.append("## Document Details")
        md.extend(field_entries)
        md.append("")

    # 3. Tables / Line Items
    # Note: In our current schema, line_items is usually a separate list
    # But for a universal preparer, we check if structured_data has a 'line_items' key
    # or if it's passed separately. For now, assume it's in a 'line_items' key if present.
    
    # If structured_data is just the fields, we might need the original pipeline output
    # But let's handle what we have.
    
    # 4. Raw Text fallback
    if raw_text and not field_entries:
        md.append("## Extracted Text")
        md.append(raw_text)

    return "\n".join(md)
