"""Engineering Copilot chat (Phase 11)."""

from __future__ import annotations

import json
import re
from typing import Any

from llm.client import LLMClient
from models.investigation import InvestigationRun
from services.errors import InvestigationNotFoundError, UploadContentNotFoundError
from services.ingestion_service import IngestionService
from utils.summary_payload import get_summary_text
from sqlalchemy.orm import Session
from utils.logger import get_logger

log = get_logger(__name__)


class ChatService:
    def __init__(self, db: Session, llm_client: LLMClient | None = None) -> None:
        self._db = db
        self._llm_client = llm_client

    def _load_investigation(self, investigation_id: int) -> dict[str, Any]:
        investigation = (
            self._db.query(InvestigationRun)
            .filter(InvestigationRun.id == investigation_id)
            .one_or_none()
        )
        if investigation is None:
            raise InvestigationNotFoundError(
                f"Investigation run {investigation_id} was not found"
            )

        state: dict[str, Any] = {}
        if investigation.state_json:
            try:
                parsed = json.loads(investigation.state_json)
                if isinstance(parsed, dict):
                    state = parsed
            except json.JSONDecodeError:
                log.warning("Invalid investigation state JSON for %s", investigation_id)

        upload_id = getattr(investigation, "upload_id", None)
        if upload_id:
            upload = IngestionService(self._db).get_uploaded_content(upload_id)
            if upload is None or not upload.content_text.strip():
                raise UploadContentNotFoundError(
                    f"Uploaded content was not found for upload_id={upload_id}"
                )
            # limit to first 8KB to avoid huge prompts
            state["uploaded_raw"] = upload.content_text[:8192]

        return state

    def _build_prompt(
        self,
        question: str,
        state: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> str:

        summary = get_summary_text(state) or "No investigation summary available."
        failure_summary = state.get("failure_summary", "")
        uploaded_raw = state.get("uploaded_raw", "")

        anomalies = state.get("anomalies", [])
        incidents = state.get("incidents", [])
        root_causes = state.get("root_causes", [])
        recommendations = state.get("recommendations", [])

        evidence = []

        if failure_summary:
            evidence.append(f"Failure Summary:\n{failure_summary}")

        if anomalies:
            evidence.append("Detected Anomalies:")

            for anomaly in anomalies:
                if not isinstance(anomaly, dict):
                    continue

                flags = [
                    key.replace("_", " ")
                    for key, value in anomaly.items()
                    if isinstance(value, bool) and value
                ]

                if flags:
                    evidence.append(f"- Active anomaly signals: {', '.join(flags)}")

                risk = anomaly.get("risk")
                if risk:
                    evidence.append(f"  Risk Level: {risk}")

                signals = anomaly.get("signals")
                if isinstance(signals, dict) and signals:
                    strongest = max(signals.items(), key=lambda item: abs(item[1]))

                    evidence.append(
                        f"  Strongest sensor deviation: "
                        f"{strongest[0]} ({strongest[1]:+.2f})"
                    )

        if incidents:
            evidence.append("")
            evidence.append("Historical Incident Matches:")

            for incident in incidents[:5]:
                evidence.append(
                    f"- Incident {incident.get('incident_id')} "
                    f"(Similarity={incident.get('similarity')}) "
                    f"Root Cause={incident.get('root_cause')}"
                )

        if root_causes:
            evidence.append("")
            evidence.append("Current Root Cause Hypotheses:")

            for cause in root_causes[:5]:
                evidence.append(
                    f"- {cause.get('cause')} (Confidence={cause.get('confidence')}%)"
                )

        if recommendations:
            evidence.append("")
            evidence.append("Investigation Recommendations:")

            for recommendation in recommendations:
                evidence.append(f"- {recommendation}")

        evidence_block = "\n".join(evidence)

        uploaded_data_block = ""
        if uploaded_raw:
            uploaded_data_block = (
                "User Provided Uploaded Data (source input for the investigation):\n"
                f"{uploaded_raw}"
            )
        else:
            uploaded_data_block = (
                "User Provided Uploaded Data (source input for the investigation):\n"
                "No raw uploaded file content could be loaded."
            )

        history_block = ""

        if history:
            formatted: list[str] = []
            total_chars = 0
            max_history_chars = 8000

            for message in reversed(history):
                role = "User" if message.get("role") == "user" else "Assistant"
                entry = f"{role}: {message.get('content', '')}"
                entry_len = len(entry) + 1
                if formatted and total_chars + entry_len > max_history_chars:
                    break
                formatted.append(entry)
                total_chars += entry_len

            history_block = "\n".join(reversed(formatted))

        return f"""
                You are an Engineering Investigation Copilot.

                Your role is to help users understand engineering investigations,
                sensor telemetry, anomaly detection results, historical incidents,
                root-cause analysis, and investigation recommendations.

                Behavior Rules:

                - Speak naturally and professionally.
                - If the user greets you, greet them normally.
                - If the user asks a question unrelated to the investigation,
                politely explain that you can only assist with the current
                engineering investigation and available evidence.
                - Do not hallucinate facts.
                - Do not invent sensor readings.
                - Do not invent incident records.
                - Do not claim certainty unless evidence supports it.

                Evidence Priority:

                1. Raw uploaded data from the user
                2. Uploaded telemetry and anomaly signals derived from that data
                3. Detected anomaly patterns
                4. Historical incident matches
                5. Root-cause hypotheses
                6. Recommendations

                IMPORTANT:

                The raw uploaded data below is the user's original input.
                The investigation summary and evidence below are the derived
                analysis of that same upload.

                Use the uploaded data as the primary source of truth for what
                the user provided.

                Historical incidents are supporting evidence only.

                If telemetry conflicts with historical incidents,
                trust telemetry first.

                If asked to justify a root cause,
                always explain which anomaly signals,
                sensor behavior,
                or historical incidents support it.

                User Provided Uploaded Data:

                {uploaded_data_block}

                Investigation Summary:

                {summary}

                Investigation Evidence:

                {evidence_block}

                Conversation History:

                {history_block}

                Current User Question:

                {question}

                Answer:
                """

    def _clean_response(self, text: str) -> str:
        """Clean markdown formatting from response (** and other markers)."""
        # Remove markdown bold (**text**)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        # Remove markdown headers (# text)
        text = re.sub(r"^#+\s+(.+?)$", r"\1", text, flags=re.MULTILINE)
        # Remove markdown lists (* item)
        text = re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=re.MULTILINE)
        # Remove markdown code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        return text.strip()

    def answer(
        self,
        investigation_id: int,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:

        state = self._load_investigation(investigation_id)

        prompt = self._build_prompt(
            question=question,
            state=state,
            history=history,
        )

        if self._llm_client is None:
            try:
                self._llm_client = LLMClient()
            except ValueError as exc:
                log.warning(
                    "LLM client unavailable for chat: %s",
                    exc,
                )
                self._llm_client = None

        if self._llm_client is not None:
            try:
                response = self._llm_client.generate_text(
                    prompt,
                    max_tokens=512,
                    temperature=0.3,
                )

                return self._clean_response(response)

            except Exception as exc:
                log.warning(
                    "LLM chat generation failed: %s",
                    exc,
                )

        return (
            "I am unable to access the investigation assistant "
            "right now. Please try again shortly."
        )
