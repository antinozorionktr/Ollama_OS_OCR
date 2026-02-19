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
        model: str = "mistral-small3.1:24b-2503-fp16",
        timeout: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        logger.info(
            "OllamaOCRClient initialized",
            extra={"model": model, "ollama_url": base_url},
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
            "model": self.model,
            "prompt": prompt,
            "images": images_b64,
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
            "You are an OCR system. Extract ALL text visible in this document image. "
            "Maintain the original formatting and structure as much as possible. "
            "Include headers, body text, tables, footnotes, and any other text elements. "
            "Do not add any commentary or explanation — output ONLY the extracted text."
        )
        return self._call_ollama(prompt, [image_path], step="raw_text_extraction")

    def extract_structured_data(self, image_path: str, doc_type: str) -> dict:
        """Extract structured key-value data from a document image."""
        schema_prompts = {
            "invoice": (
                "You are a document data extraction system. Analyze this invoice image and "
                "extract the following fields into a JSON object. If a field is not found, "
                'use null. Output ONLY valid JSON, no markdown fences or explanation.\n\n'
                "Fields to extract:\n"
                '{\n'
                '  "invoice_number": "string",\n'
                '  "invoice_date": "string (YYYY-MM-DD if possible)",\n'
                '  "due_date": "string or null",\n'
                '  "vendor_name": "string",\n'
                '  "vendor_address": "string or null",\n'
                '  "vendor_gstin": "string or null",\n'
                '  "customer_name": "string",\n'
                '  "customer_address": "string or null",\n'
                '  "customer_gstin": "string or null",\n'
                '  "subtotal": "number or null",\n'
                '  "tax_amount": "number or null",\n'
                '  "total_amount": "number",\n'
                '  "currency": "string (e.g. INR, USD)",\n'
                '  "payment_terms": "string or null",\n'
                '  "line_items": [\n'
                '    {\n'
                '      "description": "string",\n'
                '      "quantity": "number",\n'
                '      "unit_price": "number",\n'
                '      "amount": "number"\n'
                '    }\n'
                '  ]\n'
                '}'
            ),
            "contract": (
                "You are a document data extraction system. Analyze this contract/agreement "
                "image and extract the following fields into a JSON object. If a field is not "
                'found, use null. Output ONLY valid JSON, no markdown fences or explanation.\n\n'
                "Fields to extract:\n"
                '{\n'
                '  "contract_title": "string",\n'
                '  "contract_number": "string or null",\n'
                '  "effective_date": "string (YYYY-MM-DD if possible)",\n'
                '  "expiration_date": "string or null",\n'
                '  "party_1_name": "string",\n'
                '  "party_1_role": "string (e.g. Client, Employer)",\n'
                '  "party_2_name": "string",\n'
                '  "party_2_role": "string (e.g. Vendor, Contractor)",\n'
                '  "contract_value": "number or null",\n'
                '  "currency": "string or null",\n'
                '  "payment_terms": "string or null",\n'
                '  "governing_law": "string or null",\n'
                '  "termination_clause_summary": "string or null",\n'
                '  "key_obligations": ["string"],\n'
                '  "signatures_present": "boolean"\n'
                '}'
            ),
            "crac": (
                "You are a document data extraction system. Analyze this CRAC (Credit Risk "
                "Assessment/Compliance) document image and extract the following fields into "
                'a JSON object. If a field is not found, use null. Output ONLY valid JSON, '
                'no markdown fences or explanation.\n\n'
                "Fields to extract:\n"
                '{\n'
                '  "document_title": "string",\n'
                '  "document_number": "string or null",\n'
                '  "date_issued": "string (YYYY-MM-DD if possible)",\n'
                '  "entity_name": "string",\n'
                '  "entity_type": "string (e.g. Individual, Company)",\n'
                '  "entity_id": "string or null",\n'
                '  "risk_rating": "string or null",\n'
                '  "credit_score": "string or null",\n'
                '  "credit_limit": "number or null",\n'
                '  "outstanding_amount": "number or null",\n'
                '  "compliance_status": "string or null",\n'
                '  "review_date": "string or null",\n'
                '  "reviewer_name": "string or null",\n'
                '  "key_findings": ["string"],\n'
                '  "recommendations": ["string"],\n'
                '  "approval_status": "string or null"\n'
                '}'
            ),
        }

        prompt = schema_prompts.get(doc_type, schema_prompts["invoice"])
        raw_response = self._call_ollama(prompt, [image_path], step="structured_extraction")
        return self._parse_json_response(raw_response)

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
        """Check if Ollama is running and the model is available. Returns status dict."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            model_found = any(self.model in name or name in self.model for name in model_names)
            return {
                "ollama_reachable": True,
                "model_available": model_found,
                "available_models": model_names,
            }
        except requests.exceptions.ConnectionError:
            return {"ollama_reachable": False, "model_available": False, "available_models": []}
        except Exception as e:
            return {"ollama_reachable": False, "model_available": False, "error": str(e)}