"""Summary Generator: structured LangGraph terminal node (Phase 8)."""

from __future__ import annotations

import json
from typing import Any

from llm.client import LLMClient
from tools.base import BaseTool


class SummaryGenerator(BaseTool[dict[str, Any], dict[str, Any]]):
    name = "summary_generator"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = LLMClient()
            except ValueError:
                self._llm_client = None

    def run(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        if self._llm_client is None:
            return self._fallback(payload)

        try:
            prompt = self._build_prompt(payload)
            response = self._llm_client.generate_text(
                prompt, max_tokens=450, temperature=0.0
            )
            parsed = self._parse_response(response)
            if parsed:
                return self._finalize_payload(parsed, payload)
        except Exception:
            pass
        return self._fallback(payload)

    def _build_prompt(self, payload: dict[str, Any]) -> str:
        anomalies = payload.get("anomalies") or []
        incidents = payload.get("incidents") or []
        root_causes = payload.get("root_causes") or []
        recommendations = payload.get("recommendations") or []

        return (
            "You are an engineering investigation summarizer.\n"
            "Return valid JSON only. Do not wrap the answer in markdown.\n"
            "Make the overview concise, ideally 2-3 sentences.\n"
            "Do not repeat the same anomaly, incident, or root-cause phrase more than once.\n"
            "Merge duplicated findings into a single clear sentence.\n"
            "Use this schema exactly:\n"
            "{\n"
            '  "headline": string,\n'
            '  "overview": string,\n'
            '  "anomalies": [string],\n'
            '  "historical_matches": [{"incident_id": number, "similarity": number, "failure": string, "root_cause": string}],\n'
            '  "root_causes": [{"cause": string, "confidence": number, "evidence": [string]}],\n'
            '  "recommendations": [string],\n'
            '  "action_plan": [string]\n'
            "}\n\n"
            f"Anomalies: {json.dumps(anomalies, default=str)}\n"
            f"Historical incidents: {json.dumps(incidents, default=str)}\n"
            f"Root causes: {json.dumps(root_causes, default=str)}\n"
            f"Recommendations: {json.dumps(recommendations, default=str)}\n"
        )

    def _parse_response(self, response: str) -> dict[str, Any]:
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return self._normalize_payload(parsed)
        except json.JSONDecodeError:
            return {}
        return {}

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        anomalies = self._normalize_strings(payload.get("anomalies"))
        historical_matches = [
            {
                "incident_id": self._maybe_int(item.get("incident_id")),
                "similarity": self._maybe_float(item.get("similarity")),
                "failure": str(item.get("failure") or "").strip(),
                "root_cause": str(item.get("root_cause") or "").strip(),
            }
            for item in self._normalize_dict_list(payload.get("historical_matches"))
        ]
        root_causes = [
            {
                "cause": str(item.get("cause") or "").strip(),
                "confidence": self._maybe_int(item.get("confidence")),
                "evidence": self._normalize_strings(item.get("evidence")),
            }
            for item in self._normalize_dict_list(payload.get("root_causes"))
        ]
        recommendations = self._normalize_strings(payload.get("recommendations"))
        action_plan = self._normalize_strings(payload.get("action_plan"))
        overview = self._sanitize_overview(
            str(payload.get("overview") or "").strip(),
            anomaly_texts=anomalies,
            historical_matches=historical_matches,
            root_causes=root_causes,
        )
        summary_text = str(payload.get("summary_text") or "").strip() or overview or self._build_summary_text(
            overview=overview,
            anomaly_texts=anomalies,
            historical_matches=historical_matches,
            root_causes=root_causes,
            recommendations=action_plan or recommendations,
            historical_match_status="",
        )

        return {
            "headline": str(payload.get("headline") or "Investigation Summary").strip(),
            "overview": overview,
            "anomalies": anomalies,
            "historical_matches": historical_matches,
            "root_causes": root_causes,
            "recommendations": recommendations,
            "action_plan": action_plan or recommendations,
            "summary_text": summary_text,
        }

    def _finalize_payload(
        self, payload: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        """Attach a deterministic summary text to the normalized response."""

        historical_match_status = str(
            source.get("historical_match_status") or ""
        ).strip()
        anomalies = self._normalize_strings(payload.get("anomalies"))
        historical_matches = self._normalize_dict_list(payload.get("historical_matches"))
        root_causes = self._normalize_dict_list(payload.get("root_causes"))
        recommendations = self._normalize_strings(
            payload.get("action_plan") or payload.get("recommendations")
        )
        overview = self._sanitize_overview(
            str(payload.get("overview") or "").strip(),
            anomaly_texts=anomalies,
            historical_matches=historical_matches,
            root_causes=root_causes,
        )

        payload["summary_text"] = str(payload.get("summary_text") or "").strip() or overview or self._build_summary_text(
            overview=str(payload.get("headline") or "").strip(),
            anomaly_texts=anomalies,
            historical_matches=historical_matches,
            root_causes=root_causes,
            recommendations=recommendations,
            historical_match_status=historical_match_status,
        )
        return payload

    def _fallback(self, payload: dict[str, Any]) -> dict[str, Any]:
        anomalies = payload.get("anomalies") or []
        incidents = payload.get("incidents") or []
        root_causes = payload.get("root_causes") or []
        recommendations = self._normalize_strings(payload.get("recommendations"))
        historical_match_status = str(
            payload.get("historical_match_status") or ""
        ).strip()

        anomaly_texts = self._summarize_anomalies(anomalies)
        historical_matches = self._summarize_incidents(incidents)
        normalized_root_causes = self._summarize_root_causes(root_causes)

        headline = "Investigation Summary"
        overview = self._build_overview(anomaly_texts, historical_matches, normalized_root_causes)
        action_plan = recommendations or [
            "Inspect the components highlighted by the investigation evidence",
            "Validate the hypothesis with maintenance and inspection records",
        ]

        summary_text = self._build_summary_text(
            overview=overview,
            anomaly_texts=anomaly_texts,
            historical_matches=historical_matches,
            root_causes=normalized_root_causes,
            recommendations=action_plan,
            historical_match_status=historical_match_status,
        )

        return {
            "headline": headline,
            "overview": overview,
            "anomalies": anomaly_texts,
            "historical_matches": historical_matches,
            "root_causes": normalized_root_causes,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "summary_text": summary_text,
        }

    @staticmethod
    def _normalize_dict_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _normalize_strings(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text)
        return result

    @staticmethod
    def _maybe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _maybe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _summarize_anomalies(self, anomalies: list[Any]) -> list[str]:
        texts: list[str] = []
        for item in anomalies:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    texts.append(text)
                continue
            if isinstance(item, dict):
                flags = [
                    name.replace("_", " ")
                    for name, value in item.items()
                    if isinstance(value, bool) and value
                ]
                if flags:
                    texts.append(", ".join(flags))
        return texts

    def _summarize_incidents(self, incidents: list[Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for item in incidents:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "incident_id": self._maybe_int(item.get("incident_id")),
                    "similarity": self._maybe_float(item.get("similarity")),
                    "failure": str(item.get("failure") or "").strip(),
                    "root_cause": str(item.get("root_cause") or "").strip(),
                }
            )
        return items

    def _summarize_root_causes(self, root_causes: list[Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for item in root_causes:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "cause": str(item.get("cause") or "").strip(),
                    "confidence": self._maybe_int(item.get("confidence")),
                    "evidence": self._normalize_strings(item.get("evidence")),
                }
            )
        return items

    @staticmethod
    def _build_overview(
        anomaly_texts: list[str],
        historical_matches: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> str:
        unique_causes: list[str] = []
        seen_causes: set[str] = set()
        for item in root_causes:
            cause = str(item.get("cause") or "").strip()
            if not cause:
                continue
            normalized = cause.lower()
            if normalized in seen_causes:
                continue
            seen_causes.add(normalized)
            unique_causes.append(cause)

        anomaly_part = (
            f"Detected anomalies: {', '.join(anomaly_texts)}."
            if anomaly_texts
            else "No strong anomaly pattern was identified."
        )
        match_part = (
            f"Historical context: {len(historical_matches)} related incident(s) were found."
            if historical_matches
            else "Historical search did not find a close match."
        )
        cause_part = (
            f"Likely root causes include {', '.join(unique_causes)}."
            if unique_causes
            else "No validated root cause was identified."
        )
        return f"{anomaly_part} {match_part} {cause_part}".strip()

    def _sanitize_overview(
        self,
        overview: str,
        *,
        anomaly_texts: list[str],
        historical_matches: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
    ) -> str:
        cleaned = self._dedupe_sentences(overview)
        if cleaned:
            return cleaned
        return self._build_overview(anomaly_texts, historical_matches, root_causes)

    @staticmethod
    def _dedupe_sentences(text: str) -> str:
        normalized_text = " ".join(text.split()).strip()
        if not normalized_text:
            return ""

        seen: set[str] = set()
        deduped: list[str] = []
        for chunk in normalized_text.replace("?", ".").replace("!", ".").split("."):
            sentence = chunk.strip()
            if not sentence:
                continue
            normalized = " ".join(sentence.lower().split())
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(sentence)

        if not deduped:
            return ""
        return ". ".join(deduped).strip() + "."

    @staticmethod
    def _build_summary_text(
        *,
        overview: str,
        anomaly_texts: list[str],
        historical_matches: list[dict[str, Any]],
        root_causes: list[dict[str, Any]],
        recommendations: list[str],
        historical_match_status: str,
    ) -> str:
        lines = [overview.strip()]
        if anomaly_texts:
            lines.append(f"Anomalies: {', '.join(anomaly_texts)}.")
        if historical_matches:
            incident_ids = [
                str(item.get("incident_id"))
                for item in historical_matches
                if item.get("incident_id")
            ]
            if incident_ids:
                lines.append(f"Historical incidents: {', '.join(incident_ids)}.")
        if root_causes:
            causes = [
                f"{item.get('cause')} ({item.get('confidence')}%)"
                for item in root_causes
                if item.get("cause")
            ]
            if causes:
                lines.append(f"Root causes: {', '.join(causes)}.")
        if recommendations:
            lines.append(
                f"Recommendations: {len(recommendations)} action(s) identified."
            )
        if historical_match_status == "no_match":
            lines.append(
                "The uploaded file does not appear to match the current historical knowledge base."
            )
        return " ".join(line for line in lines if line).strip()
