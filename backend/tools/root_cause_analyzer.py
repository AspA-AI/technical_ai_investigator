"""Tool 3: LLM root cause analysis (Phase 8)."""

from __future__ import annotations

import json
from typing import Any

from llm.client import LLMClient
from tools.base import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)


class RootCauseAnalyzer(BaseTool[dict[str, Any], list[dict[str, Any]]]):
    name = "root_cause_analysis"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._init_error: str | None = None
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = LLMClient()
            except ValueError as exc:
                self._llm_client = None
                self._init_error = str(exc)

    def run(self, payload: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]:
        anomalies = payload.get("anomalies") or []
        incidents = payload.get("incidents") or []

        if self._llm_client is None:
            reason = self._init_error or "the language model client is not configured"
            log.warning("RootCauseAnalyzer: %s; returning a heuristic (non-LLM) estimate.", reason)
            return self._fallback(anomalies, incidents, reason=reason)

        prompt = self._build_prompt(anomalies, incidents)
        try:
            response = self._llm_client.generate_text(prompt, max_tokens=400, temperature=0.0)
        except Exception as exc:
            reason = f"the language model request failed ({exc})"
            log.warning("RootCauseAnalyzer: %s; returning a heuristic (non-LLM) estimate.", reason)
            return self._fallback(anomalies, incidents, reason=reason)

        parsed = self._parse_response(response)
        if not parsed:
            reason = "the language model response could not be parsed into root-cause candidates"
            log.warning("RootCauseAnalyzer: %s; returning a heuristic (non-LLM) estimate.", reason)
            return self._fallback(anomalies, incidents, reason=reason)
        return parsed

    def _build_prompt(self, anomalies: list[Any], incidents: list[Any]) -> str:
        anomaly_texts = []
        for anomaly in anomalies:
            if isinstance(anomaly, dict):
                flags = [name.replace("_", " ") for name, value in anomaly.items() if isinstance(value, bool) and value]
                if flags:
                    anomaly_texts.append(", ".join(flags))

        incident_summaries = []
        for incident in incidents:
            if isinstance(incident, dict):
                incident_id = incident.get("incident_id")
                root_cause = incident.get("root_cause")
                similarity = incident.get("similarity")
                incident_summaries.append(
                    f"Incident {incident_id}: root_cause={root_cause}, similarity={similarity}"
                )

        return (
            "You are an engineering failure investigation assistant. "
            "Given the detected anomaly signals and historical incident matches, "
            "identify the most likely root causes and provide confidence estimates. "
            "Respond with valid JSON only, using a list of objects with keys: "
            "cause, confidence, evidence. "
            "Do not perform any numerical calculations beyond simple reasoning.\n\n"
            f"Anomalies:\n- {'\n- '.join(anomaly_texts) if anomaly_texts else 'none'}\n\n"
            f"Historical incidents:\n- {'\n- '.join(incident_summaries) if incident_summaries else 'none'}\n\n"
            "Return at most 5 candidates."
        )

    def _parse_response(self, response: str) -> list[dict[str, Any]]:
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                cleaned: list[dict[str, Any]] = []
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    cleaned.append(
                        {
                            "cause": str(item.get("cause", "")).strip(),
                            "confidence": int(item.get("confidence", 0)) if item.get("confidence") is not None else 0,
                            "evidence": [str(e) for e in item.get("evidence", []) if e],
                        }
                    )
                return cleaned
        except json.JSONDecodeError:
            pass
        return []

    def _fallback(
        self,
        anomalies: list[Any],
        incidents: list[Any],
        reason: str | None = None,
    ) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        if not anomalies and not incidents:
            ranked = [
                {
                    "cause": "insufficient evidence",
                    "confidence": 25,
                    "evidence": ["No anomaly information or incident matches were available."],
                }
            ]
            return self._annotate_degraded(ranked, reason)

        if anomalies:
            ranked.append(
                {
                    "cause": "sensor anomaly pattern",
                    "confidence": 50,
                    "evidence": ["Anomaly signals were detected in the sensor telemetry."],
                }
            )

        for incident in incidents:
            if isinstance(incident, dict):
                root_cause = str(incident.get("root_cause") or "").strip()
                if root_cause:
                    ranked.append(
                        {
                            "cause": root_cause,
                            "confidence": max(
                                10,
                                min(90, int(round(float(incident.get("similarity", 0.0)) * 100))),
                            ),
                            "evidence": [f"Matched incident {incident.get('incident_id')}"],
                        }
                    )

        if not ranked:
            ranked = [
                {
                    "cause": "insufficient evidence",
                    "confidence": 25,
                    "evidence": ["No usable anomaly or incident data was available."],
                }
            ]
        return self._annotate_degraded(ranked, reason)

    @staticmethod
    def _annotate_degraded(
        ranked: list[dict[str, Any]], reason: str | None
    ) -> list[dict[str, Any]]:
        """Mark heuristic results so callers know the LLM was not used (and why)."""
        if not reason:
            return ranked
        notice = f"Heuristic estimate — generated without the language model because {reason}."
        for item in ranked:
            item["degraded"] = True
            item["notice"] = notice
            item.setdefault("evidence", []).append(notice)
        return ranked
