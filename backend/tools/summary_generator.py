"""Summary Generator: LangGraph terminal node (Phase 8)."""

from __future__ import annotations

from typing import Any

from llm.client import LLMClient
from tools.base import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)


class SummaryGenerator(BaseTool[dict[str, Any], str]):
    name = "summary_generator"

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

    def run(self, payload: dict[str, Any], **kwargs: Any) -> str:
        if self._llm_client is None:
            reason = self._init_error or "the language model client is not configured"
            log.warning("SummaryGenerator: %s; returning a heuristic (non-LLM) summary.", reason)
            return self._fallback(payload, reason=reason)

        try:
            prompt = self._build_prompt(payload)
            return self._llm_client.generate_text(prompt, max_tokens=300, temperature=0.0)
        except Exception as exc:
            reason = f"the language model request failed ({exc})"
            log.warning("SummaryGenerator: %s; returning a heuristic (non-LLM) summary.", reason)
            return self._fallback(payload, reason=reason)

    def _build_prompt(self, payload: dict[str, Any]) -> str:
        anomalies = payload.get("anomalies") or []
        incidents = payload.get("incidents") or []
        root_causes = payload.get("root_causes") or []
        recommendations = payload.get("recommendations") or []

        anomaly_text = "; ".join(
            ", ".join(
                [name.replace("_", " ") for name, value in item.items() if isinstance(value, bool) and value]
            )
            for item in anomalies
            if isinstance(item, dict)
        ) or "No major anomaly pattern identified"

        incident_text = "; ".join(
            f"Incident {item.get('incident_id')}: {item.get('failure')} ({item.get('similarity')})"
            for item in incidents
            if isinstance(item, dict)
        ) or "No close historical matches found"

        root_cause_text = "; ".join(
            f"{item.get('cause')} ({item.get('confidence')}%)"
            for item in root_causes
            if isinstance(item, dict) and item.get("cause")
        ) or "No validated root cause yet"

        recommendation_text = "; ".join(
            [str(item) for item in recommendations]
        ) or "No recommendations generated"

        return (
            "You are an engineering investigation summarizer. "
            "Based on the investigation outputs, provide a short, clear summary in one paragraph. "
            "Use the provided anomaly pattern, historical incident matches, root causes, and investigation recommendations. "
            "Do not simulate any tool computation.\n\n"
            f"Anomaly pattern: {anomaly_text}.\n"
            f"Historical matches: {incident_text}.\n"
            f"Root causes: {root_cause_text}.\n"
            f"Recommendations: {recommendation_text}.\n\n"
            "Return a concise investigation summary with the most significant findings first."
        )

    def _fallback(self, payload: dict[str, Any], reason: str | None = None) -> str:
        anomalies = payload.get("anomalies") or []
        incidents = payload.get("incidents") or []
        root_causes = payload.get("root_causes") or []
        recommendations = payload.get("recommendations") or []

        anomaly_texts = []
        for item in anomalies:
            if isinstance(item, dict):
                flags = [
                    name.replace("_", " ")
                    for name, value in item.items()
                    if isinstance(value, bool) and value
                ]
                if flags:
                    anomaly_texts.append(", ".join(flags))

        incident_ids = [
            str(item.get("incident_id"))
            for item in incidents
            if isinstance(item, dict) and item.get("incident_id") is not None
        ]
        causes = [
            f"{item.get('cause')} ({item.get('confidence')}%)"
            for item in root_causes
            if isinstance(item, dict) and item.get("cause")
        ]

        lines = [
            "Investigation summary:",
            f"- Anomaly pattern: {anomaly_texts[0] if anomaly_texts else 'No major anomaly pattern identified'}",
            f"- Historical matches: {', '.join(incident_ids) if incident_ids else 'No close historical matches found'}",
            f"- Root causes: {', '.join(causes) if causes else 'No validated root cause yet'}",
            f"- Recommendations: {len(recommendations)} investigation step(s) identified",
        ]
        if reason:
            lines.append(
                f"(Note: this is a heuristic summary generated without the language model "
                f"because {reason}.)"
            )
        return " ".join(lines)
