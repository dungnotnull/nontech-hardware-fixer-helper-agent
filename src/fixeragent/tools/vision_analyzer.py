"""Vision module — extract structured diagnostic info from images."""

from __future__ import annotations

import base64
import json
import re
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from fixeragent.config import get_settings
from fixeragent.models import DiagnosticPayload, DeviceInfo, ErrorIndicators, FaultType
from fixeragent.tools.llm_router import LLMRouter

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
    logger.warning("PIL not available; image preprocessing disabled")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available; OCR disabled")


class VisionAnalyzer:
    """Analyze device images/video frames and return structured diagnostics."""

    VISION_PROMPT = """Analyze the provided image of a broken or malfunctioning home appliance / electronic device.

Return a JSON object with exactly these keys:
- device_category: string (one of: printer, microwave, router, washing_machine, refrigerator, air_conditioner, faucet, vacuum, tv, laptop, or "unknown")
- brand: string or null
- model_candidates: array of strings (up to 3 best guesses)
- model_confidence: float 0.0-1.0
- error_indicators:
    - led_pattern: string or null (describe blink pattern, e.g. "blinking_red_4x")
    - display_code: string or null (any alphanumeric error code visible)
    - physical_damage: array of strings (e.g. ["crack", "burn_mark", "leak"])
    - audible_symptoms: array of strings
- visible_components: array of strings (parts visible in the image)
- fault_type: string (one of: paper_jam, connectivity_error, hardware_failure, firmware_error, power_supply_issue, filter_clog, seal_failure, mechanical_wear, user_error, unknown)
- fault_confidence: float 0.0-1.0

Be concise. If you cannot identify the device, set model_confidence below 0.5.
"""

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self.settings = get_settings()
        self.router = llm_router or LLMRouter()
        logger.info("VisionAnalyzer initialized")

    def analyze_image(self, image_path: str | Path, user_description: str = "") -> DiagnosticPayload:
        """Run full vision pipeline: preprocess → VLM → OCR → assemble DiagnosticPayload."""
        image_path = Path(image_path)
        logger.info(f"Analyzing image: {image_path}")

        # Preprocess
        processed_path = self._preprocess(image_path)

        # VLM analysis via LLM Router
        vision_prompt = self.VISION_PROMPT
        if user_description:
            vision_prompt += f"\n\nUser also described the problem as: {user_description}"

        raw = self.router.vision(processed_path, vision_prompt, json_mode=True)
        vision_data = self._safe_parse_json(raw)

        # OCR model number / error code
        ocr_text = self._run_ocr(processed_path)
        model_number = self._extract_model_number(ocr_text)
        display_code = self._extract_display_code(ocr_text)

        # Override if OCR found something VLM missed
        if display_code and not vision_data.get("error_indicators", {}).get("display_code"):
            vision_data.setdefault("error_indicators", {})["display_code"] = display_code
        if model_number and not vision_data.get("model_candidates"):
            vision_data["model_candidates"] = [model_number]
            vision_data["model_confidence"] = max(vision_data.get("model_confidence", 0.0), 0.75)

        device_info = DeviceInfo(
            device_category=vision_data.get("device_category", "unknown"),
            brand=vision_data.get("brand"),
            model_candidates=vision_data.get("model_candidates", []),
            model_confidence=vision_data.get("model_confidence", 0.0),
            model_number_ocr=model_number,
        )
        error_indicators = ErrorIndicators(
            led_pattern=vision_data.get("error_indicators", {}).get("led_pattern"),
            display_code=vision_data.get("error_indicators", {}).get("display_code"),
            physical_damage=vision_data.get("error_indicators", {}).get("physical_damage", []),
            audible_symptoms=vision_data.get("error_indicators", {}).get("audible_symptoms", []),
            user_description=user_description,
        )

        # Map string fault_type to enum
        raw_fault = vision_data.get("fault_type", "unknown")
        try:
            fault_type = FaultType(raw_fault)
        except ValueError:
            fault_type = FaultType.UNKNOWN

        return DiagnosticPayload(
            device_info=device_info,
            error_indicators=error_indicators,
            visible_components=vision_data.get("visible_components", []),
            fault_type=fault_type,
            fault_confidence=vision_data.get("fault_confidence", 0.0),
            raw_vision_output=vision_data,
        )

    def _preprocess(self, image_path: Path) -> Path:
        """Resize and normalize image for VLM input."""
        if not PIL_AVAILABLE:
            return image_path
        try:
            img = Image.open(image_path)
            # Convert to RGB if necessary
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            # Resize if too large (max 2048 on longest side for most VLMs)
            max_size = 2048
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            # Auto-contrast for better visibility
            img = ImageOps.autocontrast(img, cutoff=1)
            out_path = image_path.parent / f"{image_path.stem}_processed.jpg"
            img.save(out_path, "JPEG", quality=92)
            logger.debug(f"Preprocessed image saved to {out_path}")
            return out_path
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}; using original")
            return image_path

    def _run_ocr(self, image_path: Path) -> str:
        """Run TrOCR / pytesseract on the image to extract printed text."""
        if not TESSERACT_AVAILABLE:
            return ""
        try:
            text = pytesseract.image_to_string(str(image_path))
            logger.debug(f"OCR extracted {len(text)} characters")
            return text
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    @staticmethod
    def _safe_parse_json(raw: str) -> dict:
        """Extract JSON from markdown-fenced or plain text LLM output."""
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fenced:
            raw = fenced.group(1)
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse vision JSON. Raw: {raw[:500]}")
            return {}

    @staticmethod
    def _extract_model_number(ocr_text: str) -> str | None:
        """Heuristic extraction of model numbers from OCR text."""
        if not ocr_text:
            return None
        # Common model number patterns: ABC-1234, XYZ1234A, etc.
        patterns = [
            r"[A-Z]{2,6}[-\s]?\d{3,5}[A-Z]?",
            r"Model[:\s#]*([A-Za-z0-9\-]+)",
            r"M(?:odel|DL)[:\s#\.]*([A-Za-z0-9\-]{4,20})",
            r"P/N[:\s#]*([A-Za-z0-9\-]{4,20})",
        ]
        for pat in patterns:
            m = re.search(pat, ocr_text, re.IGNORECASE)
            if m:
                return m.group(1) if m.lastindex else m.group(0)
        return None

    @staticmethod
    def _extract_display_code(ocr_text: str) -> str | None:
        """Extract error codes from OCR text."""
        if not ocr_text:
            return None
        # Look for codes like E03, SE, F-3, H97, etc.
        m = re.search(r"\b([A-Z][0-9]{1,3}|[0-9]{3,4}|F-\d+|H\d{2}|E\d{1,3})\b", ocr_text)
        return m.group(1) if m else None