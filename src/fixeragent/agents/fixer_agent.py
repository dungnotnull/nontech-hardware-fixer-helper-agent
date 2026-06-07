"""Orchestration layer — FixerAgent main loop."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from loguru import logger

from fixeragent.config import get_settings
from fixeragent.models import (
    DiagnosticPayload,
    DiagnosisResponse,
    FaultType,
    LLMConfig,
    RepairGuide,
)
from fixeragent.tools.llm_router import LLMRouter
from fixeragent.tools.rag_engine import RAGEngine
from fixeragent.tools.repair_generator import RepairGuideGenerator
from fixeragent.tools.safety_assessor import SafetyAssessor
from fixeragent.tools.vision_analyzer import VisionAnalyzer


class AgentState(str, Enum):
    IDLE = "idle"
    VISION_ANALYSIS = "vision_analysis"
    DEVICE_CONFIRMATION = "device_confirmation"
    SAFETY_CHECK = "safety_check"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    GUIDE_GENERATION = "guide_generation"
    ESCALATED = "escalated"
    COMPLETE = "complete"


class FixerAgent:
    """End-to-end agent: image / text → diagnosis → retrieval → repair guide."""

    def __init__(
        self,
        vision: VisionAnalyzer | None = None,
        rag: RAGEngine | None = None,
        safety: SafetyAssessor | None = None,
        generator: RepairGuideGenerator | None = None,
        llm_router: LLMRouter | None = None,
    ) -> None:
        self.vision = vision or VisionAnalyzer()
        self.rag = rag or RAGEngine()
        self.safety = safety or SafetyAssessor()
        self.generator = generator or RepairGuideGenerator(llm_router=llm_router or LLMRouter())
        self.llm_router = llm_router or LLMRouter()
        self.settings = get_settings()
        self.state: AgentState = AgentState.IDLE
        logger.info("FixerAgent orchestration layer ready")

    def diagnose(
        self,
        image_path: str | None = None,
        description: str = "",
        device_hint: str = "",
        llm_config: LLMConfig | None = None,
    ) -> DiagnosisResponse:
        """Run full diagnosis → repair guide pipeline."""
        self.state = AgentState.VISION_ANALYSIS
        logger.info("Starting diagnosis pipeline")

        if llm_config:
            self.llm_router = LLMRouter(config=llm_config)
            self.generator = RepairGuideGenerator(llm_router=self.llm_router)
            self.vision = VisionAnalyzer(llm_router=self.llm_router)

        # Step 1: Vision analysis (or text-only diagnosis)
        if image_path:
            diagnosis = self.vision.analyze_image(image_path, description)
        else:
            diagnosis = self._text_only_diagnosis(description, device_hint)

        # Confidence gate
        if diagnosis.needs_better_input:
            return DiagnosisResponse(
                session_id="",
                status="needs_input",
                message="Could not confidently identify the device. Please provide a clearer photo or enter the model number.",
                diagnosis=diagnosis,
            )

        if diagnosis.needs_clarification:
            return DiagnosisResponse(
                session_id="",
                status="needs_clarification",
                message=f"Is this a {diagnosis.device_info.model_candidates[0]}? Please confirm or provide the exact model number.",
                diagnosis=diagnosis,
            )

        # Step 2: Safety assessment
        self.state = AgentState.SAFETY_CHECK
        safety = self.safety.assess(
            device_category=diagnosis.device_info.device_category,
            fault_type=diagnosis.fault_type,
            user_description=description,
        )

        if safety.tier.value == 4:
            self.state = AgentState.ESCALATED
            guide = self.generator._generate_escalation_guide(
                session_id="",
                device_name=self._device_name(diagnosis),
                fault_desc=description or diagnosis.fault_type.value,
                safety=safety,
            )
            return DiagnosisResponse(
                session_id=guide.session_id,
                status="escalated",
                message="This repair requires a certified professional due to safety hazards.",
                guide=guide,
                safety=safety,
                diagnosis=diagnosis,
            )

        # Step 3: Knowledge retrieval
        self.state = AgentState.KNOWLEDGE_RETRIEVAL
        query = self._build_rag_query(diagnosis)
        chunks = self.rag.retrieve(query, top_k=5, min_score=self.settings.diagnostic_confidence_threshold)

        # Step 4: Guide generation
        self.state = AgentState.GUIDE_GENERATION
        guide = self.generator.generate(diagnosis, safety, chunks)
        self.state = AgentState.COMPLETE

        logger.info(f"Generated guide {guide.session_id} for {guide.device_name} (tier={guide.safety.tier_label})")
        return DiagnosisResponse(
            session_id=guide.session_id,
            status="success",
            guide=guide,
            safety=safety,
            diagnosis=diagnosis,
        )

    def _text_only_diagnosis(self, description: str, device_hint: str) -> DiagnosticPayload:
        """When no image is provided, use LLM to classify from text description."""
        prompt = f"""A user described their broken appliance as:
"{description}"
Device hint (if any): {device_hint or 'none'}

Classify this into the following JSON format exactly:
{{
  "device_category": "...",
  "brand": "...",
  "model_candidates": ["..."],
  "model_confidence": 0.0,
  "error_indicators": {{
    "led_pattern": "...",
    "display_code": "...",
    "physical_damage": [],
    "audible_symptoms": [],
    "user_description": "..."
  }},
  "visible_components": [],
  "fault_type": "...",
  "fault_confidence": 0.0
}}
"""
        try:
            raw = self.llm_router.chat(
                [
                    {"role": "system", "content": "You classify appliance faults from user text descriptions. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                json_mode=True,
            )
            data = json.loads(raw)
            return DiagnosticPayload(
                device_info={
                    "device_category": data.get("device_category", "unknown"),
                    "brand": data.get("brand"),
                    "model_candidates": data.get("model_candidates", []),
                    "model_confidence": data.get("model_confidence", 0.0),
                    "model_number_ocr": None,
                },
                error_indicators={
                    "led_pattern": data.get("error_indicators", {}).get("led_pattern"),
                    "display_code": data.get("error_indicators", {}).get("display_code"),
                    "physical_damage": data.get("error_indicators", {}).get("physical_damage", []),
                    "audible_symptoms": data.get("error_indicators", {}).get("audible_symptoms", []),
                    "user_description": description,
                },
                visible_components=data.get("visible_components", []),
                fault_type=data.get("fault_type", "unknown"),
                fault_confidence=data.get("fault_confidence", 0.0),
            )
        except Exception as e:
            logger.warning(f"Text-only diagnosis LLM failed: {e}")
            return DiagnosticPayload(
                device_info={"device_category": device_hint or "unknown", "brand": None, "model_candidates": [], "model_confidence": 0.0, "model_number_ocr": None},
                error_indicators={"led_pattern": None, "display_code": None, "physical_damage": [], "audible_symptoms": [], "user_description": description},
                visible_components=[],
                fault_type=FaultType.UNKNOWN,
                fault_confidence=0.0,
            )

    def _build_rag_query(self, diagnosis: DiagnosticPayload) -> str:
        parts = [
            diagnosis.device_info.device_category,
            diagnosis.device_info.brand or "",
            diagnosis.fault_type.value,
            diagnosis.error_indicators.display_code or "",
            diagnosis.error_indicators.led_pattern or "",
            diagnosis.error_indicators.user_description or "",
        ]
        return " ".join(p for p in parts if p)

    @staticmethod
    def _device_name(diagnosis: DiagnosticPayload) -> str:
        brand = diagnosis.device_info.brand or ""
        model = diagnosis.device_info.model_candidates[0] if diagnosis.device_info.model_candidates else ""
        category = diagnosis.device_info.device_category or "Device"
        if brand and model:
            return f"{brand} {model}"
        if brand:
            return f"{brand} {category}"
        return category

    def feedback(self, session_id: str, outcome: str, notes: str | None = None) -> dict[str, Any]:
        """Log user feedback to outcomes file."""
        from datetime import datetime
        entry = {
            "session_id": session_id,
            "outcome": outcome,
            "notes": notes,
            "timestamp": datetime.utcnow().isoformat(),
        }
        log_path = self.settings.feedback_log_path
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            logger.info(f"Feedback logged for session {session_id}: {outcome}")
            return {"acknowledged": True}
        except Exception as e:
            logger.error(f"Feedback logging failed: {e}")
            return {"acknowledged": False, "error": str(e)}