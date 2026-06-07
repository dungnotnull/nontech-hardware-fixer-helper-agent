"""Unit tests for Pydantic schemas."""

import pytest
from fixeragent.models import (
    DiagnosticPayload,
    DeviceInfo,
    ErrorIndicators,
    RepairGuide,
    RepairStep,
    SafetyAssessment,
    RepairTier,
    FaultType,
    FeedbackOutcome,
    OutcomeStatus,
)


class TestDiagnosticPayload:
    def test_proceed_with_high_confidence(self) -> None:
        d = DiagnosticPayload(
            device_info=DeviceInfo(device_category="printer", brand="HP", model_confidence=0.90),
            error_indicators=ErrorIndicators(),
        )
        assert d.proceed_with_diagnosis is True
        assert d.needs_clarification is False
        assert d.needs_better_input is False

    def test_needs_clarification_mid_confidence(self) -> None:
        d = DiagnosticPayload(
            device_info=DeviceInfo(device_category="printer", brand="HP", model_confidence=0.70),
            error_indicators=ErrorIndicators(),
        )
        assert d.proceed_with_diagnosis is False
        assert d.needs_clarification is True
        assert d.needs_better_input is False

    def test_needs_better_input_low_confidence(self) -> None:
        d = DiagnosticPayload(
            device_info=DeviceInfo(device_category="printer", brand="HP", model_confidence=0.40),
            error_indicators=ErrorIndicators(),
        )
        assert d.proceed_with_diagnosis is False
        assert d.needs_clarification is False
        assert d.needs_better_input is True


class TestSafetyAssessment:
    def test_tier_1_user_error(self) -> None:
        s = SafetyAssessment(tier=RepairTier.DIY_EASY, tier_label="?? DIY Easy", requires_unplug=True)
        assert s.tier == RepairTier.DIY_EASY

    def test_tier_4_escalation(self) -> None:
        s = SafetyAssessment(
            tier=RepairTier.PROFESSIONAL_ONLY,
            tier_label="?? Professional Only",
            requires_unplug=False,
            escalation_reason="Auto-escalated",
        )
        assert s.tier == RepairTier.PROFESSIONAL_ONLY


class TestRepairGuide:
    def test_markdown_output(self) -> None:
        guide = RepairGuide(
            session_id="abc123",
            device_name="HP Printer",
            fault_description="Paper jam",
            safety=SafetyAssessment(tier=RepairTier.DIY_EASY, tier_label="?? DIY Easy", requires_unplug=True),
            estimated_total_time="5 minutes",
            tools_needed=[],
            parts_needed=[],
            steps=[
                RepairStep(step_number=1, title="Open panel", instruction="Open the front panel."),
            ],
            test_procedure="Print test page.",
            troubleshooting_fallback="Contact support.",
            source_attribution="Test",
            knowledge_confidence=0.92,
        )
        md = guide.to_markdown()
        assert "?? Repair Guide" in md
        assert "Step 1" in md
        assert "Paper jam" in md


class TestFeedbackOutcome:
    def test_outcome_enum(self) -> None:
        f = FeedbackOutcome(session_id="abc", outcome=OutcomeStatus.FIXED)
        assert f.outcome == OutcomeStatus.FIXED
