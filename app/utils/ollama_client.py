"""
Ollama Vision + Cleanup Client
- Vision extraction: llama3.2-vision:11b (image → raw text with structural hints)
- Text cleanup: mistral:7b (raw text → cleaned text)
- Layout reconstruction: mistral:7b (raw text → recreated layout)
"""

import base64
import time
import os
import json
import requests
from pathlib import Path

from app.utils.logger import setup_logger

logger = setup_logger("docvision.ollama")


class OllamaOCRClient:
    """Client for the two-model OCR pipeline via Ollama."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        vision_model: str = "llama3.2-vision:11b",
        cleanup_model: str = "mistral:7b",
        timeout: int = 300,
        vllm_base_url: str = None,
        use_vllm: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.vllm_base_url = vllm_base_url.rstrip("/") if vllm_base_url else None
        self.use_vllm = use_vllm
        self.vision_model = vision_model
        self.cleanup_model = cleanup_model
        self.timeout = timeout
        logger.info(
            "OllamaOCRClient initialized",
            extra={
                "vision_model": vision_model,
                "cleanup_model": cleanup_model,
                "ollama_url": base_url,
                "vllm_url": vllm_base_url,
                "use_vllm": use_vllm
            },
        )

    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_ollama(
        self,
        model: str,
        prompt: str,
        image_paths: list[str] | None = None,
        step: str = "ocr",
    ) -> str:
        """
        Call Ollama's /api/generate endpoint.
        Supports both vision calls (with images) and text-only calls (without images).
        """
        images_b64 = []
        if image_paths:
            for p in image_paths:
                images_b64.append(self._encode_image(p))

        logger.debug(
            f"Ollama API call starting | model={model} | step={step} | images={len(images_b64)}",
            extra={"step": step},
        )

        # ── Options ──
        # Important: set num_ctx to handle large documents (raw text + prompt)
        payload = {
            "model": model,
            "prompt": prompt,
            "images": images_b64,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.85,
                "top_k": 20,
                "repeat_penalty": 1.35,
                "num_predict": 2048,
                "num_ctx": 16384,
                "num_keep": 0,
                "stop": [
                    "END_TRANSCRIPTION",
                    "<END>",
                    "### END"
                ]
            },
        }
        if images_b64:
            payload["images"] = images_b64

        url = f"{self.base_url}/api/generate"
        start = time.time()

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            duration = round(time.time() - start, 2)

            resp_text = result.get("response", "").strip()
            
            # Post-process: Remove meta-commentary like "Here is the cleaned text:"
            lines = resp_text.split("\n")
            if lines and ("here is" in lines[0].lower() or "certainly" in lines[0].lower()):
                resp_text = "\n".join(lines[1:]).strip()

            logger.info(
                f"Ollama API call complete | model={model} | step={step} | {duration}s | response_len={len(resp_text)}",
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

    def _call_vllm(
        self,
        model: str,
        prompt: str,
        image_paths: list[str] | None = None,
        step: str = "ocr",
    ) -> str:
        """Call vLLM's OpenAI-compatible /v1/chat/completions endpoint."""
        if not self.vllm_base_url:
            raise ValueError("vLLM base URL not configured")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
            }
        ]

        if image_paths:
            for p in image_paths:
                b64 = self._encode_image(p)
                ext = Path(p).suffix.lower().lstrip(".")
                if ext == "jpg": ext = "jpeg"
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{ext};base64,{b64}"}
                })

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 2048,
        }

        url = f"{self.vllm_base_url}/v1/chat/completions"
        start = time.time()

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            duration = round(time.time() - start, 2)
            
            resp_text = result["choices"][0]["message"]["content"].strip()
            
            logger.info(
                f"vLLM API call complete | model={model} | step={step} | {duration}s",
                extra={"step": step, "duration_s": duration},
            )
            return resp_text
        except Exception as e:
            logger.error(f"vLLM API error ({step}): {e}")
            raise

    # ───────────────────────────────────────────
    # Stage 0: Layout Detection (llama3.2-vision)
    # ───────────────────────────────────────────

    def detect_layout(self, image_path: str) -> list[dict]:
        """
        Detect logical regions on a page (Header, Table, Paragraph, etc.)
        using the vision model. Returns a list of region dicts with bboxes.
        """
        prompt = (
            "SYSTEM: You are a layout analysis engine.\n"
            "Identify and provide bounding boxes for all logical regions in the document.\n\n"
            "### CATEGORIES\n"
            "- header\n"
            "- paragraph\n"
            "- table\n"
            "- form\n"
            "- section_title\n"
            "- footer\n\n"
            "### OUTPUT FORMAT\n"
            "Return JSON only: [{\"type\": \"category\", \"bbox\": [x1, y1, x2, y2], \"label\": \"description\"}]\n"
            "Coordinates [0-1000] relative to image size.\n"
            "Respond ONLY with valid JSON.\n\n"
            "LAYOUT:"
        )
        if self.use_vllm:
            resp = self._call_vllm(self.vision_model, prompt, [image_path], step="layout_detection")
        else:
            resp = self._call_ollama(self.vision_model, prompt, [image_path], step="layout_detection")
        
        # Basic JSON extraction (robust against model chatter)
        import json
        try:
            # Find start/end of JSON array
            start_idx = resp.find("[")
            end_idx = resp.rfind("]") + 1
            if start_idx != -1 and end_idx != -1:
                return json.loads(resp[start_idx:end_idx])
            return []
        except Exception as e:
            logger.warning(f"Failed to parse layout detection JSON: {e}")
            return []

    # ───────────────────────────────────────────
    # Stage 1: Vision Extraction (llama3.2-vision)
    # ───────────────────────────────────────────

    def remove_duplicate_blocks(self, text: str) -> str:
        """Removes duplicated lines/blocks often repeated by LLM OCR."""
        seen = set()
        result = []
        for line in text.splitlines():
            line_clean = line.strip()
            if not line_clean:
                result.append(line)
                continue
            if line_clean not in seen:
                seen.add(line_clean)
                result.append(line)
        return "\n".join(result)

    def extract_page_text(self, image_path: str) -> str:
        """
        Extract raw text with structural hints from a page image
        using the vision model (llama3.2-vision:11b).
        """
        prompt = (
            "SYSTEM: You are a high-precision OCR transcription engine.\n"
            "Your job is to TRANSCRIBE text exactly from the image.\n"
            "You are NOT allowed to summarize, interpret, or explain anything.\n\n"

            "### GLOBAL RULES\n"
            "1. Transcribe ALL visible text.\n"
            "2. Preserve the original reading order (top → bottom, left → right).\n"
            "3. Preserve line breaks exactly as seen.\n"
            "4. If text is unclear, write the closest readable text.\n"
            "5. DO NOT hallucinate missing text.\n"
            "6. DO NOT explain the document.\n"
            "7. DO NOT repeat sections unless they actually appear twice.\n\n"

            "### STRUCTURE RULES\n"
            "Use the following structure markers:\n\n"

            "Tables:\n"
            "Use | to separate columns\n"
            "Example:\n"
            "Item | Qty | Price\n"
            "Pen | 2 | 10\n\n"

            "Checkboxes:\n"
            "[x] checked\n"
            "[ ] unchecked\n\n"

            "Forms:\n"
            "Field: Value\n\n"

            "Sections:\n"
            "Write section titles on their own line\n\n"

            "### IMPORTANT\n"
            "1. Maintain spacing where possible\n"
            "2. Keep numbers exactly as written\n"
            "3. Keep punctuation exactly as written\n"
            "4. If a word is unclear write: [?]\n\n"

            "### OUTPUT FORMAT\n"
            "Return ONLY the transcription text.\n"
            "NO explanations.\n"
            "NO commentary.\n\n"

            "START TRANSCRIPTION:"
        )
        raw_text = self._call_ollama(self.vision_model, prompt, [image_path], step="vision_extraction")
        return self.remove_duplicate_blocks(raw_text)

    # ───────────────────────────────────────────
    # Stage 2: Text Cleanup (mistral:7b)
    # ───────────────────────────────────────────

    def clean_text(self, raw_text: str) -> str:
        """
        Clean and normalize raw extracted text using mistral:7b.
        Fixes spacing, punctuation, line grouping, and paragraph structure.
        """
        if not raw_text or len(raw_text) < 10:
            return raw_text or ""

        prompt = (
            "SYSTEM: You are a document text normalization engine.\n"
            "Your job is to CLEAN OCR text while preserving its structure.\n\n"

            "### CLEANING RULES\n"
            "1. Fix spacing and punctuation.\n"
            "2. Merge broken words caused by OCR errors.\n"
            "3. Remove duplicated blocks caused by OCR loops.\n"
            "4. Preserve all tables, checkboxes, and field labels.\n"
            "5. DO NOT change the meaning of the text.\n"
            "6. DO NOT invent missing data.\n"
            "7. DO NOT summarize.\n\n"

            "### STRUCTURE PRESERVATION\n"
            "You MUST preserve:\n"
            "- tables using |\n"
            "- checkboxes [x] [ ]\n"
            "- field-value pairs\n"
            "- section headers\n\n"

            "### INPUT TEXT\n"
            f"{raw_text}\n\n"

            "### OUTPUT\n"
            "Return the cleaned text only.\n"
        )

        return self._call_ollama(self.cleanup_model, prompt, step="text_cleanup")

    # ───────────────────────────────────────────
    # Stage 3: Structured Data Extraction (mistral:7b)
    # ───────────────────────────────────────────

    def extract_structured_data(self, raw_text: str) -> str:
        """
        Extract key-value pairs (semantic entities) and tables from raw text using mistral:7b.
        Produces a JSON string.
        """
        if not raw_text:
            return "{}"

        prompt = (
            "SYSTEM: You are a structural information extraction engine.\n\n"

            "TASK: Extract entities and tables from the text into a valid JSON object.\n\n"

            "### EXTRACTION RULES\n"
            "1. Identify common fields (names, dates, totals, IDs).\n"
            "2. Identify any tables or lists of items (lines).\n"
            "3. Format exactly as a JSON object.\n"
            "4. For regular fields, use: \"field_name\": \"value\"\n"
            "5. For tables, use an array of objects under a descriptive key (e.g., \"line_items\").\n"
            "6. Preserve original values exactly.\n"
            "7. Respond ONLY with valid JSON.\n\n"

            "### TEXT\n"
            f"{raw_text}\n\n"

            "### OUTPUT FORMAT\n"
            "{\n"
            "  \"invoice_number\": \"...\",\n"
            "  \"line_items\": [\n"
            "    { \"description\": \"...\", \"amount\": \"...\" }\n"
            "  ]\n"
            "}\n"
        )
        resp = self._call_ollama(self.cleanup_model, prompt, step="structured_extraction")

        # Robust JSON extraction
        try:
            start_idx = resp.find("{")
            end_idx = resp.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                # Validate it's actual JSON
                json_str = resp[start_idx:end_idx]
                json.loads(json_str) # test parse
                return json_str
            return "{}"
        except Exception:
            return "{}"

    # ───────────────────────────────────────────
    # Stage 4: Layout Reconstruction (mistral:7b)
    # ───────────────────────────────────────────

    def reconstruct_layout(self, raw_text: str) -> str:
        """
        Reconstruct document layout from raw text using mistral:7b.
        Produces a visually formatted version with sections, tables, forms.
        """
        if not raw_text:
            return ""

        prompt = (
            "SYSTEM: You are a document layout reconstruction engine.\n\n"

            "TASK: Recreate a clean readable version of the document.\n"
            "Preserve the structure including sections, forms, and tables.\n\n"

            "### LAYOUT RULES\n"
            "1. Section titles should be centered with separator lines.\n"
            "2. Tables must have aligned columns.\n"
            "3. Field-value pairs must stay on one line.\n"
            "4. Preserve checkboxes using [x] and [ ].\n"
            "5. Group related fields together.\n"
            "6. Remove duplicated text blocks if they appear.\n"
            "7. Do NOT add commentary.\n"
            "8. Do NOT invent new information.\n\n"

            "### TABLE FORMAT\n"
            "Align columns using spacing.\n\n"

            "Example:\n"
            "Item        Qty     Price\n"
            "Pen         2       10\n\n"

            "### INPUT TEXT\n"
            f"{raw_text}\n\n"

            "### OUTPUT\n"
            "Return the reconstructed document only.\n"
        )
        return self._call_ollama(self.cleanup_model, prompt, step="layout_reconstruction")


    # ───────────────────────────────────────────
    # Health Check
    # ───────────────────────────────────────────

    def health_check(self) -> dict:
        """Check if Ollama is running and the required models are available."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            vision_ok = any(self.vision_model in n or n in self.vision_model for n in model_names)
            cleanup_ok = any(self.cleanup_model in n or n in self.cleanup_model for n in model_names)

            return {
                "ollama_reachable": True,
                "vision_model_available": vision_ok,
                "cleanup_model_available": cleanup_ok,
                "model_available": vision_ok and cleanup_ok,
                "available_models": model_names,
            }
        except requests.exceptions.ConnectionError:
            return {"ollama_reachable": False, "model_available": False, "available_models": []}
        except Exception as e:
            return {"ollama_reachable": False, "model_available": False, "error": str(e)}