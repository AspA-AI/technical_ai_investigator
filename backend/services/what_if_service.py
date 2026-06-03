"""What-if counterfactual analysis (Phase 12).

Loads a persisted investigation, derives its baseline failure risk, applies the
proposed parameter changes through the deterministic ``CounterfactualAnalysis``
tool, and returns the before/after risk (both as numeric scores and as the
categorical risk level used elsewhere in the app).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from models.investigation import InvestigationRun
from services.errors import InvestigationNotFoundError
from tools.counterfactual_analysis import CounterfactualAnalysis
from utils.logger import get_logger

log = get_logger(__name__)

# Categorical anomaly risk (AnomalyDetector output) <-> numeric baseline score
# used by the counterfactual tool. Midpoints chosen so each maps back onto its
# own category via ``_risk_category``.
RISK_SCORES = {"low": 30, "medium": 60, "high": 85}


class WhatIfService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._tool = CounterfactualAnalysis()

    def analyze(self, investigation_id: int, parameters: dict[str, Any]) -> dict[str, Any]:
        state = self._load_state(investigation_id)

        params = dict(parameters or {})
        baseline_score, before_risk = self._resolve_baseline(state, params.get("baseline_risk"))
        params["baseline_risk"] = baseline_score

        result = self._tool.run(params)
        after_score = int(result.get("after_risk", baseline_score))
        after_risk = self._risk_category(after_score)

        log.service(
            "What-if investigation_id=%s before=%s(%s) after=%s(%s) reduction=%s",
            investigation_id,
            before_risk,
            baseline_score,
            after_risk,
            after_score,
            result.get("risk_reduction"),
        )
        return {
            "before_risk": before_risk,
            "after_risk": after_risk,
            "result": result,
        }

    def _load_state(self, investigation_id: int) -> dict[str, Any]:
        investigation = (
            self._db.query(InvestigationRun)
            .filter(InvestigationRun.id == investigation_id)
            .one_or_none()
        )
        if investigation is None:
            raise InvestigationNotFoundError(f"Investigation run {investigation_id} was not found")
        if not investigation.state_json:
            return {}
        try:
            parsed = json.loads(investigation.state_json)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _resolve_baseline(self, state: dict[str, Any], fallback: int | None) -> tuple[int, str]:
        """Prefer the investigation's detected risk; otherwise use the request baseline."""
        risk = self._investigation_risk(state)
        if risk in RISK_SCORES:
            return RISK_SCORES[risk], risk
        score = max(0, min(100, int(fallback if fallback is not None else 70)))
        return score, self._risk_category(score)

    @staticmethod
    def _investigation_risk(state: dict[str, Any]) -> str | None:
        for anomaly in state.get("anomalies") or []:
            if isinstance(anomaly, dict) and anomaly.get("risk"):
                return str(anomaly["risk"]).lower()
        return None

    @staticmethod
    def _risk_category(score: int) -> str:
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"
