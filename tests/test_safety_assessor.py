"""Tests for SafetyAssessor."""

import pytest
from fixeragent.tools.safety_assessor import SafetyAssessor
from fixeragent.models import FaultType, RepairTier


class TestSafetyAssessor:
    def setup_method(self) -> None:
        self.assessor = SafetyAssessor()

    def test_user_error_tier_1(self) -> None:
        result = self.assessor.assess("printer", FaultType.USER_ERROR)
        assert result.tier == RepairTier.DIY_EASY

    def test_power_supply_tier_4(self) -> None:
        result = self.assessor.assess("router", FaultType.POWER_SUPPLY_ISSUE)
        assert result.tier == RepairTier.PROFESSIONAL_ONLY

    def test_microwave_always_tier_4(self) -> None:
        result = self.assessor.assess("microwave", FaultType.PAPER_JAM)
        assert result.tier == RepairTier.PROFESSIONAL_ONLY
        assert any("2000V" in w for w in result.warnings)

    def test_crt_always_tier_4(self) -> None:
        result = self.assessor.assess("CRT monitor", FaultType.HARDWARE_FAILURE)
        assert result.tier == RepairTier.PROFESSIONAL_ONLY
