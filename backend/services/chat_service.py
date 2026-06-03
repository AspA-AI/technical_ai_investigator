"""Engineering Copilot chat (Phase 11)."""

from __future__ import annotations

import json
import re
from typing import Any

from llm.client import LLMClient
from models.investigation import InvestigationRun
from services.errors import InvestigationNotFoundError
from sqlalchemy.orm import Session
from utils.logger import get_logger
from config.settings import settings
from pathlib import Path

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

        # attach raw uploaded file content (if available) so the agent can reference user data
        upload_id = getattr(investigation, "upload_id", None)
        if upload_id:
            try:
                raw_dir = Path(settings.RAW_DATA_DIR)
                pattern = f"{upload_id}_*"
                match = next(raw_dir.glob(pattern), None)
                if match and match.is_file():
                    raw_text = match.read_text(errors="ignore")
                    # limit to first 8KB to avoid huge prompts
                    state["uploaded_raw"] = raw_text[:8192]
            except Exception:
                log.debug("Could not load raw uploaded file for %s", upload_id)

        return state

    def _is_greeting(self, question: str) -> bool:
        """Detect if the question is a casual greeting."""
        greetings = [
            "hello",
            "hi",
            "hey",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
            "sup",
            "what's up",
            "how are you",
            "how do you do",
        ]
        ql = question.lower().strip()
        return any(g in ql for g in greetings)

    def _is_off_topic(self, question: str) -> bool:
        """Detect if the question is off-topic (personal/unrelated)."""
        off_topic_keywords = [
            "family",
            "wife",
            "husband",
            "child",
            "birthday",
            "school",
            "relationship",
            "marriage",
            "love",
            "politics",
            "religion",
        ]
        ql = question.lower()
        return any(k in ql for k in off_topic_keywords)

    def _build_prompt(
        self,
        question: str,
        state: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        summary = state.get("summary", "No summary available.")
        failure_summary = state.get("failure_summary", "")
        anomalies = state.get("anomalies", [])
        incidents = state.get("incidents", [])
        root_causes = state.get("root_causes", [])
        recommendations = state.get("recommendations", [])

        prompt_lines = [
            "You are a concise, conversational engineering investigation assistant.",
            "Keep responses natural and brief. Only reference investigation details when the user asks about them.",
            "Use clear language, avoid verbose explanations, and format responses readably (use short paragraphs, not markdown).",
            "If the user asks a casual greeting like 'hello', respond naturally without forcing investigation context.",
            "If asked about your role or capabilities, briefly explain you analyze investigation data without over-elaborating.",
            "Do NOT invent facts or hallucinate beyond the provided investigation state.",
            "",
            "Investigation summary:",
            summary,
        ]

        if failure_summary:
            prompt_lines.extend(["", "Failure summary:", failure_summary])

        if anomalies:
            prompt_lines.extend(["", "Anomalies:", json.dumps(anomalies, indent=2)])

        if incidents:
            prompt_lines.extend(
                ["", "Historical incidents:", json.dumps(incidents, indent=2)]
            )

        if root_causes:
            prompt_lines.extend(["", "Root causes:", json.dumps(root_causes, indent=2)])

        if recommendations:
            prompt_lines.extend(
                ["", "Recommendations:", json.dumps(recommendations, indent=2)]
            )

        # include a short sample of the uploaded raw data when available
        uploaded_raw = state.get("uploaded_raw")
        if uploaded_raw:
            prompt_lines.extend(["", "Uploaded raw file sample:", uploaded_raw])

        # include conversation history context if available
        if history and len(history) > 0:
            prompt_lines.extend(["", "Conversation history (for context):"])
            for msg in history[-4:]:  # keep last 4 messages for context
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                prompt_lines.append(f"{role}: {content}")

        prompt_lines.extend(
            ["", "User's current question:", question, "", "Your response:"]
        )
        return "\n".join(prompt_lines)

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

    def _fallback_answer(self, question: str, state: dict[str, Any]) -> str:
        summary = state.get("summary", "No summary is available.")
        root_causes = state.get("root_causes", [])
        recommendations = state.get("recommendations", [])

        question_text = question.lower().strip()

        # Greeting response
        if self._is_greeting(question):
            return "Hello! I'm here to help analyze this investigation. What would you like to know?"

        if "root cause" in question_text or "cause" in question_text:
            if root_causes:
                causes = ", ".join(
                    str(item.get("cause", "unknown")) for item in root_causes
                )
                return f"The identified root causes are: {causes}."
            return "No root cause was identified in this investigation."

        if (
            "recommend" in question_text
            or "next step" in question_text
            or "action" in question_text
        ):
            if recommendations:
                recs = ", ".join(str(item) for item in recommendations)
                return f"Recommended actions: {recs}"
            return "No specific recommendations are available at this time."

        if "summary" in question_text or "what happened" in question_text:
            return summary

        # Default: reference summary and offer help
        return f"Based on the investigation: {summary}. Feel free to ask about specific aspects like root causes or recommendations."

    def answer(
        self,
        investigation_id: int,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        state = self._load_investigation(investigation_id)

        # Greeting: respond naturally without forcing investigation context
        if self._is_greeting(question):
            return "Hello! I'm here to help analyze this investigation. What would you like to know?"

        # Off-topic: gentle redirect
        if self._is_off_topic(question):
            return "I focus on engineering investigations and the data you've uploaded. Feel free to ask me anything about the current analysis!"

        prompt = self._build_prompt(question, state, history)

        if self._llm_client is None:
            try:
                self._llm_client = LLMClient()
            except ValueError as exc:
                log.warning("LLM client unavailable for chat: %s", exc)
                self._llm_client = None

        if self._llm_client is not None:
            try:
                response = self._llm_client.generate_text(
                    prompt, max_tokens=512, temperature=0.6
                )
                # Clean up markdown formatting
                return self._clean_response(response)
            except Exception as exc:
                log.warning("LLM chat generation failed, falling back: %s", exc)

        return self._fallback_answer(question, state)
