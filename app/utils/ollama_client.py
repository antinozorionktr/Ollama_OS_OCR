"""
Ollama Vision OCR Client
Sends images to Mistral (or other vision models) via Ollama's API
for text extraction. Includes structured logging for every API call.
"""

import base64
import json
import time
import os
import requests
from pathlib import Path
from typing import Optional

from app.utils.logger import setup_logger

logger = setup_logger("docvision.ollama")


class OllamaOCRClient:
    """Client for interacting with Ollama vision models for OCR tasks."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        ocr_model: str = "ministral-3:14b",
        timeout: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.ocr_model = ocr_model
        self.timeout = timeout
        logger.info(
            "OllamaOCRClient initialized",
            extra={"ocr_model": ocr_model, "ollama_url": base_url},
        )

    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_ollama(self, prompt: str, image_paths: list[str], step: str = "ocr") -> str:
        """
        Call Ollama's /api/generate endpoint with images.
        """
        file_sizes = []
        for p in image_paths:
            try:
                file_sizes.append(round(os.path.getsize(p) / 1024, 1))
            except OSError:
                file_sizes.append(0)

        logger.debug(
            f"Ollama API call starting | step={step} | images={len(image_paths)} | sizes_kb={file_sizes}",
            extra={"step": step},
        )

        images_b64 = [self._encode_image(p) for p in image_paths]

        payload = {
            "model": self.ocr_model,
            "prompt": prompt,
            "images": images_b64 if images_b64 else [],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
            },
        }

        url = f"{self.base_url}/api/generate"
        start = time.time()

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            duration = round(time.time() - start, 2)

            resp_text = result.get("response", "")
            logger.info(
                f"Ollama API call complete | step={step} | {duration}s | response_len={len(resp_text)}",
                extra={"step": step, "duration_s": duration},
            )
            return resp_text

        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to Ollama at {self.base_url}",
                extra={"step": step, "status": "connection_error"},
            )
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running (`ollama serve`)."
            )
        except requests.exceptions.Timeout:
            logger.error(
                f"Ollama request timed out after {self.timeout}s",
                extra={"step": step, "status": "timeout"},
            )
            raise TimeoutError(
                f"Request timed out after {self.timeout}s. "
                "The document may be too large or the model too slow."
            )
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Ollama HTTP error: {e.response.status_code}",
                extra={"step": step, "status": "http_error", "error": str(e)},
            )
            raise RuntimeError(f"Ollama API error: {e.response.status_code} — {e.response.text}")

    def extract_raw_text(self, image_path: str) -> str:
        """Extract all visible text from an image using OCR."""
        prompt = (
            "You are a high-accuracy OCR and document transcription system.\n\n"
            "Your task is to transcribe ALL visible text from the provided document image.\n\n"

            "### Document Types You May Encounter\n"
            "- Printed documents\n"
            "- Handwritten notes or forms\n"
            "- Forms with fields and labels\n"
            "- Tables and structured layouts\n"
            "- Signatures and initials\n"
            "- Checkboxes or radio buttons\n"
            "- Stamps or seals\n\n"

            "### Transcription Rules\n"
            "1. Extract ALL readable text exactly as it appears.\n"
            "2. Preserve the layout and structure where possible.\n"
            "3. Maintain line breaks and spacing.\n"
            "4. Represent tables using rows and columns aligned in plain text.\n"
            "5. For checkboxes:\n"
            "   - [x] if checked\n"
            "   - [ ] if unchecked\n"
            "6. If a signature is present, write: [Signature]\n"
            "7. If handwritten text appears, transcribe it as written.\n"
            "8. If text is unclear, mark it as [illegible].\n\n"

            "Output ONLY the transcription. Do not explain anything."
        )
        return self._call_ollama(prompt, [image_path], step="raw_text_extraction")

    def extract_tokens_with_bbox(
        self, image_path: str, page: int = 1, image_width: int = 1000, image_height: int = 1414
    ) -> list[dict]:
        """
        Extract text tokens with bounding boxes from an image.
        Returns list of {text, bbox:[x1,y1,x2,y2], page} dicts.
        The model is asked to return spatial token information.
        Falls back to line-level estimation if model doesn't support native bbox.
        """
        prompt = (
            "You are a precise OCR token extraction system.\n\n"
            "Analyze the document image and return ALL visible text as a JSON array.\n\n"
            "For each piece of text, estimate its bounding box position on the image.\n"
            f"The image is {image_width}x{image_height} pixels.\n\n"
            "### Rules:\n"
            "1. Break text into meaningful tokens: words, numbers, labels, values.\n"
            "2. For each token estimate [x1, y1, x2, y2] pixel coordinates.\n"
            "   - x1,y1 = top-left corner of the token\n"
            "   - x2,y2 = bottom-right corner of the token\n"
            "3. Sort tokens roughly by reading order (top-to-bottom, left-to-right).\n"
            "4. Include ALL text — headers, body, tables, footers.\n\n"
            "Return ONLY a valid JSON array. No explanations. No markdown.\n\n"
            "Example output:\n"
            '[\n'
            '  {"text": "INVOICE", "bbox": [300, 50, 500, 80], "page": 1},\n'
            '  {"text": "INV-2023-001", "bbox": [400, 95, 550, 120], "page": 1}\n'
            ']'
        )
        raw = self._call_ollama(prompt, [image_path], step="token_extraction")

        # Parse JSON response
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            tokens = json.loads(text)
            return self._validate_tokens(tokens, page)
        except json.JSONDecodeError:
            # Tier 2: Recover partial array by truncating at last complete `}`
            recovered = self._recover_partial_token_array(text)
            if recovered is not None:
                logger.info(
                    f"Recovered {len(recovered)} tokens from partial JSON response.",
                    extra={"step": "token_extraction"},
                )
                return self._validate_tokens(recovered, page)
            # Tier 3: Raw text fallback
            logger.warning(
                "Token bbox parse failed; falling back to raw text synthesis.",
                extra={"step": "token_extraction"},
            )
            raw_text = self.extract_raw_text(image_path)
            return self._synthesize_tokens_from_text(raw_text, page, image_width, image_height)
        except Exception as e:
            logger.warning(f"Token extraction unexpected error: {e}. Falling back.",
                           extra={"step": "token_extraction"})
            raw_text = self.extract_raw_text(image_path)
            return self._synthesize_tokens_from_text(raw_text, page, image_width, image_height)

    def _validate_tokens(self, tokens, page: int) -> list[dict]:
        """Validate and normalise a parsed token list."""
        result = []
        for t in tokens:
            if isinstance(t, dict) and "text" in t and "bbox" in t:
                try:
                    result.append({
                        "text": str(t["text"]).strip(),
                        "bbox": [float(v) for v in t["bbox"][:4]],
                        "page": int(t.get("page", page))
                    })
                except (TypeError, ValueError):
                    pass
        return result

    def _recover_partial_token_array(self, text: str):
        """
        Salvage valid tokens from a truncated JSON array.
        Finds the last complete JSON object, closes the array, and re-parses.
        """
        last_brace = text.rfind('},')
        if last_brace == -1:
            last_brace = text.rfind('}')
        if last_brace == -1:
            return None

        candidate = text[:last_brace + 1].strip()
        if candidate.endswith(','):
            candidate = candidate[:-1]
        start = candidate.find('[')
        if start == -1:
            return None
        candidate = candidate[start:] + ']'

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None


    def _synthesize_tokens_from_text(self, text: str, page: int, w: int, h: int) -> list[dict]:
        """Fallback: create approximate bbox tokens by distributing lines vertically."""
        import re
        tokens = []
        lines = [l for l in text.split("\n") if l.strip()]
        line_h = max(h // max(len(lines), 1), 16)
        for idx, line in enumerate(lines):
            words = re.split(r'\s+', line.strip())
            line_y1 = idx * line_h
            line_y2 = line_y1 + line_h
            col_w = max(w // max(len(words), 1), 30)
            for widx, word in enumerate(words):
                if word:
                    tokens.append({
                        "text": word,
                        "bbox": [widx * col_w, line_y1, (widx + 1) * col_w, line_y2],
                        "page": page
                    })
        return tokens

    def extract_structured_data(self, image_path: str, doc_type: str) -> dict:
        """Extract structured key-value data from a document image."""

        schema_prompts = {
            "document": (
                "You are an expert document intelligence and information extraction system.\n"
                "Analyze the provided document image and extract all information into structured JSON.\n\n"

                "The document may include:\n"
                "- Printed or handwritten text\n"
                "- Forms with labeled fields\n"
                "- Tables\n"
                "- Checkboxes or radio buttons\n"
                "- Signatures\n"
                "- Stamps or seals\n\n"

                "### Extraction Rules\n"

                "1. GENERAL METADATA\n"
                "Extract high-level document information:\n"
                "- document_type\n"
                "- title\n"
                "- date\n"
                "- document_id\n"
                "- issuing_organization\n"
                "- involved_entities\n\n"

                "2. FORM FIELDS\n"
                "Extract all label-value pairs from the document.\n"
                "Example:\n"
                "Name: John Smith\n"
                "Address: 21 Baker Street\n\n"

                "Return them as:\n"
                '"fields": {\n'
                '  "name": "John Smith",\n'
                '  "address": "21 Baker Street"\n'
                "}\n\n"

                "3. TABLES\n"
                "Detect tables and return them as arrays of objects.\n"
                "Use column headers when available.\n"
                "Example:\n"
                '"tables": [\n'
                "  {\n"
                '    "table_name": "items",\n'
                '    "rows": [\n'
                '      {"item": "Pen", "qty": 10, "price": 2.5}\n'
                "    ]\n"
                "  }\n"
                "]\n\n"

                "4. CHECKBOXES AND RADIO BUTTONS\n"
                "Return checkbox states as boolean values.\n"
                "Example:\n"
                '"checkboxes": {\n'
                '  "terms_accepted": true,\n'
                '  "subscribe_newsletter": false\n'
                "}\n\n"

                "5. HANDWRITTEN TEXT\n"
                "Transcribe handwritten text exactly as seen.\n"
                "If uncertain, include best guess and mark with '(uncertain)'.\n\n"

                "6. SIGNATURES\n"
                "If a signature is present, return:\n"
                '"signatures": [\n'
                '  {\n'
                '    "label": "Applicant Signature",\n'
                '    "present": true\n'
                "  }\n"
                "]\n\n"

                "7. STAMPS / SEALS\n"
                "If an official stamp or seal is visible:\n"
                '"stamps": ["Company Seal", "Approved Stamp"]\n\n'

                "8. MISSING DATA\n"
                "If a value cannot be determined, return null.\n\n"

                "### JSON STRUCTURE\n"
                "Return a clean JSON object structured like this:\n\n"

                "{\n"
                '  "document_metadata": {},\n'
                '  "fields": {},\n'
                '  "tables": [],\n'
                '  "checkboxes": {},\n'
                '  "signatures": [],\n'
                '  "stamps": [],\n'
                '  "notes": []\n'
                "}\n\n"

                "### OUTPUT RULES\n"
                "- Output ONLY valid JSON\n"
                "- No markdown\n"
                "- No explanations\n"
                "- No code fences\n"
            )
        }

        prompt = schema_prompts.get(doc_type, schema_prompts["document"])
        raw_response = self._call_ollama(prompt, [image_path], step="structured_extraction")
        return self._parse_json_response(raw_response)

    def detect_layout(self, image_path: str) -> dict:
        """
        Stage: Layout Detection.
        Analyzes the document image to determine its structural layout
        before detailed extraction — helps guide the extraction pipeline.
        Returns a dict with layout metadata.
        """
        prompt = (
            "You are a document layout analysis system.\n"
            "Analyze the provided document image and identify its structural layout.\n\n"
            "### Detect and return the following:\n"
            "1. document_type: What kind of document is this? (e.g. invoice, form, contract, ID, receipt, medical report, table, etc.)\n"
            "2. layout_type: Describe the layout (e.g. single-column, multi-column, table-heavy, form-based, handwritten, mixed)\n"
            "3. has_tables: true/false — does the document contain data tables?\n"
            "4. has_handwriting: true/false — is any handwriting present?\n"
            "5. has_checkboxes: true/false — are there any checkboxes or radio buttons?\n"
            "6. has_signatures: true/false — are signatures present?\n"
            "7. has_stamps: true/false — are official stamps or seals visible?\n"
            "8. page_orientation: portrait or landscape\n"
            "9. language: detected language(s)\n"
            "10. notes: any other notable layout features\n\n"
            "Return ONLY valid JSON. No markdown. No explanations.\n\n"
            "Example:\n"
            "{\n"
            '  "document_type": "invoice",\n'
            '  "layout_type": "form-based",\n'
            '  "has_tables": true,\n'
            '  "has_handwriting": false,\n'
            '  "has_checkboxes": false,\n'
            '  "has_signatures": true,\n'
            '  "has_stamps": false,\n'
            '  "page_orientation": "portrait",\n'
            '  "language": "English",\n'
            '  "notes": "Two-column layout with line items table"\n'
            "}"
        )
        raw = self._call_ollama(prompt, [image_path], step="layout_detection")
        return self._parse_json_response(raw)

    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from model response, handling common formatting issues."""
        text = response.strip()

        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse JSON from model response", extra={"step": "json_parse"})
        return {"_raw_response": text, "_parse_error": "Could not extract valid JSON from response"}

    def health_check(self) -> dict:
        """Check if Ollama is running and the OCR model is available."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            ocr_ok = any(self.ocr_model in n or n in self.ocr_model for n in model_names)
            return {
                "ollama_reachable": True,
                "ocr_model_available": ocr_ok,
                "model_available": ocr_ok,
                "available_models": model_names,
            }
        except requests.exceptions.ConnectionError:
            return {"ollama_reachable": False, "model_available": False, "available_models": []}
        except Exception as e:
            return {"ollama_reachable": False, "model_available": False, "error": str(e)}