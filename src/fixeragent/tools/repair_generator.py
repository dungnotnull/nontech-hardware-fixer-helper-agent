"""Repair Guide Generator — synthesize retrieved knowledge into user-facing steps."""

from __future__ import annotations

import json
import uuid
from typing import Any

from loguru import logger

from fixeragent.models import (
    DiagnosticPayload,
    FaultType,
    RepairGuide,
    RepairStep,
    SafetyAssessment,
    RetrievalChunk,
)
from fixeragent.tools.llm_router import LLMRouter


class RepairGuideGenerator:
    """Build step-by-step repair guides from diagnosis + retrieved knowledge."""

    SYSTEM_PROMPT = """You are FixerAgent, an expert home appliance repair assistant.
Your job is to convert technical repair documentation into clear, safe, numbered step-by-step instructions that a non-technical homeowner can follow.

Rules:
1. Always start with a safety warning about unplugging the device.
2. One action per step. Be specific about what to touch, turn, or remove.
3. List required tools and parts at the top.
4. Include an estimated time for each step if possible.
5. End with a test procedure and a "Still broken?" fallback suggestion.
6. Cite the source manual/document used.
7. Never provide instructions for mains voltage, gas lines, or refrigerant.
8. Output MUST be valid JSON matching the schema.

JSON schema:
{
  "tools_needed": ["string"],
  "parts_needed": ["string"],
  "parts_links": [{"name": "string", "url": "string"}],
  "estimated_total_time": "string",
  "steps": [
    {
      "step_number": int,
      "title": "string",
      "instruction": "string",
      "tools_needed": ["string"],
      "parts_needed": ["string"],
      "estimated_time_min": int,
      "caution_notes": ["string"]
    }
  ],
  "test_procedure": "string",
  "troubleshooting_fallback": "string",
  "source_attribution": "string"
}"""

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self.router = llm_router or LLMRouter()
        logger.info("RepairGuideGenerator initialized")

    def generate(
        self,
        diagnosis: DiagnosticPayload,
        safety: SafetyAssessment,
        retrieved_chunks: list[RetrievalChunk],
    ) -> RepairGuide:
        """Assemble a RepairGuide from diagnosis and RAG results via LLM."""
        session_id = str(uuid.uuid4())[:12]
        device_name = self._format_device_name(diagnosis)
        fault_desc = diagnosis.error_indicators.user_description or diagnosis.fault_type.value.replace("_", " ")

        if safety.tier.value == 4:
            return self._generate_escalation_guide(session_id, device_name, fault_desc, safety)

        context = self._build_context(retrieved_chunks)
        user_prompt = self._build_prompt(diagnosis, safety, context)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            raw = self.router.chat(messages, json_mode=True)
            data = json.loads(raw)
            guide = self._parse_llm_output(session_id, device_name, fault_desc, safety, data)
            guide.enhanced_by_llm = f"Enhanced by {self.router.config.provider.value}"
            return guide
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}. Raw: {raw[:1000]}")
            return self._fallback_guide(session_id, device_name, fault_desc, safety, retrieved_chunks)
        except Exception as e:
            logger.error(f"Guide generation failed: {e}")
            return self._fallback_guide(session_id, device_name, fault_desc, safety, retrieved_chunks)

    def _format_device_name(self, diagnosis: DiagnosticPayload) -> str:
        brand = diagnosis.device_info.brand or ""
        model = diagnosis.device_info.model_candidates[0] if diagnosis.device_info.model_candidates else ""
        category = diagnosis.device_info.device_category or "Device"
        if brand and model:
            return f"{brand} {model}"
        if brand:
            return f"{brand} {category}"
        return category

    def _build_context(self, chunks: list[RetrievalChunk]) -> str:
        parts: list[str] = []
        for i, chunk in enumerate(chunks[:5], 1):
            src = chunk.metadata.get("source_file", chunk.metadata.get("atom_id", "unknown"))
            parts.append(f"[Source {i} | {src}]\n{chunk.content}")
        return "\n\n---\n\n".join(parts)

    def _build_prompt(
        self,
        diagnosis: DiagnosticPayload,
        safety: SafetyAssessment,
        context: str,
    ) -> str:
        return f"""Device: {self._format_device_name(diagnosis)}
Category: {diagnosis.device_info.device_category}
Fault: {diagnosis.fault_type.value}
User description: {diagnosis.error_indicators.user_description or 'N/A'}
Error code: {diagnosis.error_indicators.display_code or 'N/A'}
LED pattern: {diagnosis.error_indicators.led_pattern or 'N/A'}
Safety tier: {safety.tier_label}

Retrieved technical documentation:
{context}

Generate the repair guide JSON now.
"""

    def _parse_llm_output(
        self,
        session_id: str,
        device_name: str,
        fault_desc: str,
        safety: SafetyAssessment,
        data: dict[str, Any],
    ) -> RepairGuide:
        steps_data = data.get("steps", [])
        steps: list[RepairStep] = []
        for sd in steps_data:
            steps.append(RepairStep(
                step_number=sd.get("step_number", len(steps) + 1),
                title=sd.get("title", "Step"),
                instruction=sd.get("instruction", ""),
                tools_needed=sd.get("tools_needed", []),
                parts_needed=sd.get("parts_needed", []),
                estimated_time_min=sd.get("estimated_time_min"),
                caution_notes=sd.get("caution_notes", []),
            ))
        return RepairGuide(
            session_id=session_id,
            device_name=device_name,
            fault_description=fault_desc,
            safety=safety,
            estimated_total_time=data.get("estimated_total_time", "10-20 minutes"),
            tools_needed=data.get("tools_needed", []),
            parts_needed=data.get("parts_needed", []),
            parts_links=data.get("parts_links", []),
            steps=steps,
            test_procedure=data.get("test_procedure", "Power on and test normal operation."),
            troubleshooting_fallback=data.get(
                "troubleshooting_fallback",
                "Contact manufacturer support or a certified technician."
            ),
            source_attribution=data.get("source_attribution", "FixerAgent knowledge base"),
            knowledge_confidence=0.85,
        )

    def _fallback_guide(
        self,
        session_id: str,
        device_name: str,
        fault_desc: str,
        safety: SafetyAssessment,
        chunks: list[RetrievalChunk],
    ) -> RepairGuide:
        """Generate a minimal but real fallback guide from top chunk text."""
        steps: list[RepairStep] = []
        if chunks:
            # Try to extract numbered steps from the top chunk
            import re
            top = chunks[0].content
            raw_steps = re.split(r"\n\s*(?:\d+[\.\)]\s+|Step\s+\d+[\.:]\s+)", top)
            for i, rs in enumerate(raw_steps[1:3], start=1):
                lines = [l.strip() for l in rs.splitlines() if l.strip()]
                steps.append(RepairStep(
                    step_number=i,
                    title=lines[0][:60] if lines else f"Step {i}",
                    instruction=" ".join(lines[:3]),
                ))
        if not steps:
            steps.append(RepairStep(
                step_number=1,
                title="Power cycle the device",
                instruction="Unplug the device, wait 30 seconds, then plug it back in and observe.",
                estimated_time_min=2,
            ))

        return RepairGuide(
            session_id=session_id,
            device_name=device_name,
            fault_description=fault_desc,
            safety=safety,
            estimated_total_time="5-15 minutes",
            tools_needed=[],
            parts_needed=[],
            steps=steps,
            test_procedure="Power on and test basic function.",
            troubleshooting_fallback="Consult manufacturer support or a certified repair service.",
            source_attribution=chunks[0].metadata.get("source", "FixerAgent fallback") if chunks else "FixerAgent fallback",
            knowledge_confidence=0.5,
            enhanced_by_llm="Fallback guide (LLM generation failed)",
        )

    def _generate_escalation_guide(
        self,
        session_id: str,
        device_name: str,
        fault_desc: str,
        safety: SafetyAssessment,
    ) -> RepairGuide:
        return RepairGuide(
            session_id=session_id,
            device_name=device_name,
            fault_description=fault_desc,
            safety=safety,
            estimated_total_time="N/A — professional required",
            tools_needed=[],
            parts_needed=[],
            steps=[],
            test_procedure="N/A",
            troubleshooting_fallback="Contact a certified technician immediately.",
            source_attribution="FixerAgent safety rules",
            knowledge_confidence=0.99,
        )