"""Tool 5: What-if counterfactual analysis (Phase 5 / 12)."""

from __future__ import annotations

from typing import Any

from tools.base import BaseTool


class CounterfactualAnalysis(BaseTool[dict[str, Any], dict[str, Any]]):
    name = "counterfactual_analysis"

    def run(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        temperature_change = float(payload.get("temperature_change") or 0.0)
        pressure_change = float(payload.get("pressure_change") or 0.0)
        vibration_change = float(payload.get("vibration_change") or 0.0)
        rpm_change = float(payload.get("rpm_change") or 0.0)

        baseline_risk = int(payload.get("baseline_risk") or 70)
        improvement = (
            max(0.0, -temperature_change) * 1.8
            + max(0.0, -pressure_change) * 1.2
            + max(0.0, -vibration_change) * 2.2
            + max(0.0, rpm_change) * 0.35
        )
        reduction = max(0, min(100, int(round(improvement))))
        after_risk = max(0, baseline_risk - reduction)

        return {
            "risk_reduction": reduction,
            "before_risk": baseline_risk,
            "after_risk": after_risk,
            "assumptions": {
                "temperature_change": temperature_change,
                "pressure_change": pressure_change,
                "vibration_change": vibration_change,
                "rpm_change": rpm_change,
            },
        }
