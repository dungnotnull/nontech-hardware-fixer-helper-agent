"""Safety assessment — classify repair tier and generate warnings."""

from __future__ import annotations

from fixeragent.models import FaultType, RepairTier, SafetyAssessment


class SafetyAssessor:
    """Evaluate repair risk and assign DIY tier per CLAUDE.md §3.3."""

    TIER_MAP: dict[FaultType, RepairTier] = {
        FaultType.USER_ERROR: RepairTier.DIY_EASY,
        FaultType.CONNECTIVITY_ERROR: RepairTier.DIY_EASY,
        FaultType.FILTER_CLOG: RepairTier.DIY_EASY,
        FaultType.PAPER_JAM: RepairTier.DIY_EASY,
        FaultType.FIRMWARE_ERROR: RepairTier.DIY_MODERATE,
        FaultType.SEAL_FAILURE: RepairTier.DIY_MODERATE,
        FaultType.HARDWARE_FAILURE: RepairTier.DIY_ADVANCED,
        FaultType.MECHANICAL_WEAR: RepairTier.DIY_ADVANCED,
        FaultType.POWER_SUPPLY_ISSUE: RepairTier.PROFESSIONAL_ONLY,
        FaultType.UNKNOWN: RepairTier.PROFESSIONAL_ONLY,
    }

    TIER_LABELS: dict[RepairTier, str] = {
        RepairTier.DIY_EASY: "DIY Easy",
        RepairTier.DIY_MODERATE: "DIY Moderate",
        RepairTier.DIY_ADVANCED: "DIY Advanced",
        RepairTier.PROFESSIONAL_ONLY: "Professional Only",
    }

    # Device categories that are always professional-only if internal repair needed
    ALWAYS_TIER4_DEVICES: set[str] = {
        "microwave", "microwave_oven", "crt", "crt_monitor",
        "gas_stove", "gas_water_heater", "hvac", "furnace",
    }

    # Keywords that auto-escalate to tier 4 regardless of device
    TIER4_KEYWORDS: set[str] = {
        "mains", "high voltage", "capacitor", "refrigerant", "gas leak",
        "compressor", "magnetron", "flyback", "anode", "power supply board",
    }

    def assess(
        self,
        device_category: str,
        fault_type: FaultType,
        user_description: str = "",
        retrieved_chunks: list[dict] | None = None,
    ) -> SafetyAssessment:
        tier = self.TIER_MAP.get(fault_type, RepairTier.PROFESSIONAL_ONLY)
        warnings: list[str] = []
        electrical_hazard_v: float | None = None
        capacitor_risk = False
        gas_or_refrigerant = False
        escalation_reason: str | None = None

        # Check user description for tier-4 keywords
        desc_lower = user_description.lower()
        for kw in self.TIER4_KEYWORDS:
            if kw in desc_lower:
                tier = RepairTier.PROFESSIONAL_ONLY
                escalation_reason = f"Keyword '{kw}' detected in user description"
                warnings.append(f"Detected '{kw}' — this repair requires professional handling.")

        # Device-specific hard rules
        dev_lower = device_category.lower()
        if any(d in dev_lower for d in self.ALWAYS_TIER4_DEVICES):
            tier = RepairTier.PROFESSIONAL_ONLY
            if "microwave" in dev_lower:
                capacitor_risk = True
                electrical_hazard_v = 2000.0
                warnings.append(
                    "Microwave internal repairs are NEVER DIY-safe. "
                    "Capacitors can hold 2000V+ after unplugging."
                )
            elif "crt" in dev_lower:
                electrical_hazard_v = 25000.0
                warnings.append("CRT monitors hold lethal charge even when unplugged.")
            elif "gas" in dev_lower:
                gas_or_refrigerant = True
                warnings.append("Gas appliance repairs require certified technicians.")
            elif "hvac" in dev_lower or "furnace" in dev_lower:
                gas_or_refrigerant = True
                warnings.append("HVAC and furnace repairs involve refrigerant and combustion hazards.")
            if not escalation_reason:
                escalation_reason = f"Auto-escalated: {dev_lower} is in ALWAYS_TIER4 list"

        # Power supply always tier 4
        if fault_type == FaultType.POWER_SUPPLY_ISSUE:
            electrical_hazard_v = 120.0  # typical mains
            warnings.append("Power supply repairs involve mains voltage. Professional required.")

        # Refrigerator compressor / sealed system
        if "refrigerator" in dev_lower and fault_type in (FaultType.HARDWARE_FAILURE, FaultType.UNKNOWN):
            gas_or_refrigerant = True
            warnings.append("Refrigerator sealed system repairs involve refrigerant. Professional required.")

        if tier == RepairTier.PROFESSIONAL_ONLY and not escalation_reason:
            escalation_reason = "Auto-escalated by safety classification rules"

        return SafetyAssessment(
            tier=tier,
            tier_label=self.TIER_LABELS[tier],
            requires_unplug=tier.value < 4,
            electrical_hazard_v=electrical_hazard_v,
            capacitor_risk=capacitor_risk,
            gas_or_refrigerant=gas_or_refrigerant,
            escalation_reason=escalation_reason,
            warnings=warnings,
        )