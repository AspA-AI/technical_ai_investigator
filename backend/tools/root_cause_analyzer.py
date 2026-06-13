"""Tool 3: LLM root cause analysis (Phase 8)."""

from __future__ import annotations

import json
from typing import Any

from llm.client import LLMClient
from tools.base import BaseTool


class RootCauseAnalyzer(BaseTool[dict[str, Any], list[dict[str, Any]]]):
    name = "root_cause_analysis"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = LLMClient()
            except ValueError:
                self._llm_client = None

    def run(self, payload: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]:
        anomalies = payload.get("anomalies") or []
        incidents = payload.get("incidents") or []

        prompt = self._build_prompt(anomalies, incidents)
        if self._llm_client is None:
            return self._fallback(anomalies, incidents)

        try:
            response = self._llm_client.generate_text(
                prompt, max_tokens=400, temperature=0.0
            )
            return self._parse_response(response) or self._fallback(
                anomalies, incidents
            )
        except Exception:
            return self._fallback(anomalies, incidents)

    def _build_prompt(self, anomalies: list[Any], incidents: list[Any]) -> str:
        anomaly_texts = []
        for anomaly in anomalies:
            if isinstance(anomaly, dict):
                flags = [
                    name.replace("_", " ")
                    for name, value in anomaly.items()
                    if isinstance(value, bool) and value
                ]
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
                            "confidence": int(item.get("confidence", 0))
                            if item.get("confidence") is not None
                            else 0,
                            "evidence": [str(e) for e in item.get("evidence", []) if e],
                        }
                    )
                return cleaned
        except json.JSONDecodeError:
            pass
        return []

    def _fallback(
        self, anomalies: list[Any], incidents: list[Any]
    ) -> list[dict[str, Any]]:
        ranked = []
        seen_causes: set[str] = set()

        def add_cause(item: dict[str, Any]) -> None:
            cause = str(item.get("cause") or "").strip()
            if not cause:
                return
            normalized = cause.lower()
            if normalized in seen_causes:
                return
            seen_causes.add(normalized)
            ranked.append(item)

        if not anomalies and not incidents:
            return [
                {
                    "cause": "insufficient evidence",
                    "confidence": 25,
                    "evidence": [
                        "No anomaly information or incident matches were available."
                    ],
                }
            ]

        if anomalies:
            add_cause(
                {
                    "cause": "sensor anomaly pattern",
                    "confidence": 50,
                    "evidence": [
                        "Anomaly signals were detected in the sensor telemetry."
                    ],
                }
            )

        for incident in incidents:
            if isinstance(incident, dict):
                root_cause = str(incident.get("root_cause") or "").strip()
                if root_cause:
                    add_cause(
                        {
                            "cause": root_cause,
                            "confidence": max(
                                10,
                                min(
                                    90,
                                    int(
                                        round(
                                            float(incident.get("similarity", 0.0)) * 100
                                        )
                                    ),
                                ),
                            ),
                            "evidence": [
                                f"Matched incident {incident.get('incident_id')}"
                            ],
                        }
                    )

        return ranked or [
            {
                "cause": "insufficient evidence",
                "confidence": 25,
                "evidence": ["No usable anomaly or incident data was available."],
            }
        ]
