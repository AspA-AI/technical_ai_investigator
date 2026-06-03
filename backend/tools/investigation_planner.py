"""Tool 4: Investigation plan from root causes (Phase 5)."""

from __future__ import annotations

from typing import Any

from tools.base import BaseTool


class InvestigationPlanner(BaseTool[list[dict[str, Any]], list[str]]):
    name = "investigation_planner"

    def run(self, payload: list[dict[str, Any]], **kwargs: Any) -> list[str]:
        steps: list[str] = []
        seen: set[str] = set()

        def add(step: str) -> None:
            normalized = step.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                steps.append(normalized)

        for item in payload:
            if not isinstance(item, dict):
                continue
            cause = str(item.get("cause") or "").lower()
            if "cooling" in cause:
                add("Inspect cooling system pressure and flow")
                add("Check heat exchanger performance")
            if "bearing" in cause:
                add("Inspect bearing assembly for wear and lubrication loss")
            if "lubrication" in cause:
                add("Verify lubrication volume, viscosity, and delivery path")
            if "drive train" in cause or "rotor" in cause:
                add("Inspect drive train alignment and rotating components")
            if "compressor" in cause or "hpc" in cause:
                add("Inspect high-pressure compressor blades and seals")
            if "insufficient evidence" in cause:
                add("Collect additional telemetry and review maintenance history")

        add("Correlate findings with similar historical incidents")
        add("Validate the final hypothesis with maintenance and inspection records")
        return steps
