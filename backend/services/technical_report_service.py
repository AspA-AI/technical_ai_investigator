"""Structured technical report generation and persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from config.settings import settings
from llm.client import LLMClient
from models.investigation import InvestigationRun
from services.errors import InvestigationNotFoundError
from utils.docx_builder import markdown_to_docx_bytes
from utils.logger import get_logger
from utils.summary_payload import get_summary_sections, get_summary_text

log = get_logger(__name__)


class TechnicalReportService:
    """Generate a formal engineering report from a finalized investigation run."""

    def __init__(
        self,
        db: Session,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._db = db
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = LLMClient()
            except ValueError:
                self._llm_client = None

    def generate_markdown_report(
        self, investigation_id: int, *, persist: bool = True
    ) -> dict[str, Any]:
        investigation = self._load_investigation(investigation_id)
        state = self._load_state(investigation)
        markdown = self._synthesize_markdown(investigation, state)
        report_path = self._persist_markdown(investigation, markdown) if persist else ""

        return {
            "investigation_id": investigation.id,
            "upload_id": investigation.upload_id,
            "status": investigation.status,
            "report_path": report_path,
            "filename": f"technical_report_{investigation.id}.md",
            "markdown": markdown,
            "preview": markdown[:2000],
        }

    def get_preview_report(self, investigation_id: int) -> dict[str, Any]:
        investigation = self._load_investigation(investigation_id)
        state = self._load_state(investigation)
        cached_preview = str(state.get("technical_report_preview") or "").strip()
        if cached_preview:
            return {
                "investigation_id": investigation.id,
                "upload_id": investigation.upload_id,
                "status": investigation.status,
                "report_path": str(state.get("technical_report_path") or ""),
                "filename": str(
                    state.get("technical_report_filename")
                    or f"technical_report_{investigation.id}.md"
                ),
                "markdown": cached_preview,
                "preview": cached_preview[:2000],
            }

        return self.generate_markdown_report(investigation_id, persist=False)

    def generate_docx_report(
        self, investigation_id: int, *, persist: bool = True
    ) -> dict[str, Any]:
        investigation = self._load_investigation(investigation_id)
        state = self._load_state(investigation)
        markdown = self._synthesize_markdown(investigation, state)
        docx_bytes = markdown_to_docx_bytes(markdown)
        report_path = self._persist_docx(investigation, docx_bytes) if persist else ""

        return {
            "investigation_id": investigation.id,
            "upload_id": investigation.upload_id,
            "status": investigation.status,
            "report_path": report_path,
            "filename": f"technical_report_{investigation.id}.docx",
            "docx_bytes": docx_bytes,
            "preview": markdown[:2000],
        }

    def _load_investigation(self, investigation_id: int) -> InvestigationRun:
        investigation = (
            self._db.query(InvestigationRun)
            .filter(InvestigationRun.id == investigation_id)
            .one_or_none()
        )
        if investigation is None:
            raise InvestigationNotFoundError(
                f"Investigation run {investigation_id} was not found"
            )
        return investigation

    @staticmethod
    def _load_state(investigation: InvestigationRun) -> dict[str, Any]:
        if not investigation.state_json:
            return {}

        try:
            parsed = json.loads(investigation.state_json)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            log.warning("Invalid investigation state JSON for %s", investigation.id)
        return {}

    def _synthesize_markdown(
        self, investigation: InvestigationRun, state: dict[str, Any]
    ) -> str:
        sections = get_summary_sections(state)
        summary_text = get_summary_text(state) or "Summary not available."
        github_matches = state.get("github_matches") or []
        if not isinstance(github_matches, list):
            github_matches = []

        prompt = self._build_prompt(investigation, state, summary_text, github_matches)
        if self._llm_client is not None:
            try:
                response = self._llm_client.generate_text(
                    prompt, max_tokens=1200, temperature=0.0
                )
                if isinstance(response, str) and response.strip():
                    return response.strip()
            except Exception as exc:
                log.warning(
                    "Technical report LLM synthesis failed for investigation_id=%s: %s",
                    investigation.id,
                    exc,
                )

        return self._fallback_markdown(
            investigation=investigation,
            state=state,
            sections=sections,
            summary_text=summary_text,
            github_matches=github_matches,
        )

    def _build_prompt(
        self,
        investigation: InvestigationRun,
        state: dict[str, Any],
        summary_text: str,
        github_matches: list[dict[str, Any]],
    ) -> str:
        sections = get_summary_sections(state)
        return (
            "You are a senior engineering documentation writer.\n"
            "Rewrite the investigation into a formal technical report in valid markdown only.\n"
            "Requirements:\n"
            "- Use clear headings.\n"
            "- Include executive summary, anomaly findings, historical NASA evidence, "
            "archived GitHub issue evidence, root cause, recommendations, and sources.\n"
            "- Clearly separate NASA telemetry evidence from archived human-investigation evidence.\n"
            "- Cite GitHub issue URLs inline when available.\n"
            "- Mention when no close historical match was found.\n"
            "- Do not invent data.\n\n"
            f"Investigation ID: {investigation.id}\n"
            f"Upload ID: {investigation.upload_id}\n"
            f"Status: {investigation.status}\n"
            f"Summary: {summary_text}\n"
            f"Structured Summary: {json.dumps(sections, default=str)}\n"
            f"Historical Matches: {json.dumps(state.get('incidents') or [], default=str)}\n"
            f"Archived GitHub Matches: {json.dumps(github_matches, default=str)}\n"
            f"Recommendations: {json.dumps(state.get('recommendations') or [], default=str)}\n"
        )

    def _fallback_markdown(
        self,
        *,
        investigation: InvestigationRun,
        state: dict[str, Any],
        sections: dict[str, Any],
        summary_text: str,
        github_matches: list[dict[str, Any]],
    ) -> str:
        anomalies = self._normalize_strings(sections.get("anomalies") or state.get("anomalies"))
        incidents = state.get("incidents") or []
        recommendations = self._normalize_strings(
            sections.get("recommendations") or state.get("recommendations")
        )
        root_causes = sections.get("root_causes") or state.get("root_causes") or []

        lines: list[str] = []
        lines.append("# Engineering Technical Report")
        lines.append("")
        lines.append(f"- Investigation ID: `{investigation.id}`")
        lines.append(f"- Upload ID: `{investigation.upload_id}`")
        lines.append(f"- Status: `{investigation.status}`")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append(summary_text)
        lines.append("")
        lines.append("## Anomaly Findings")
        if anomalies:
            for item in anomalies:
                lines.append(f"- {item}")
        else:
            lines.append("- No anomaly pattern was identified.")
        lines.append("")
        lines.append("## Historical NASA Evidence")
        if incidents:
            for incident in incidents[:5]:
                if isinstance(incident, dict):
                    incident_id = incident.get("incident_id", "?")
                    similarity = incident.get("similarity")
                    failure = incident.get("failure", "")
                    root_cause = incident.get("root_cause", "")
                    lines.append(
                        f"- Incident `{incident_id}`"
                        + (
                            f" ({round(float(similarity) * 100)}% similarity)"
                            if isinstance(similarity, (int, float))
                            else ""
                        )
                        + (f": {failure}" if failure else "")
                        + (f" | Root cause: {root_cause}" if root_cause else "")
                    )
        else:
            lines.append("- No close NASA historical match was found.")
        lines.append("")
        lines.append("## Archived GitHub Evidence")
        if github_matches:
            for match in github_matches[:5]:
                if isinstance(match, dict):
                    issue_url = str(match.get("issue_url") or "").strip()
                    failure = str(match.get("failure") or "").strip()
                    root_cause = str(match.get("root_cause") or "").strip()
                    similarity = match.get("similarity")
                    label = issue_url or f"Archived Issue {match.get('incident_id', '?')}"
                    line = f"- {label}"
                    if isinstance(similarity, (int, float)):
                        line += f" ({round(float(similarity) * 100)}% similarity)"
                    if failure:
                        line += f": {failure}"
                    if root_cause:
                        line += f" | Root cause: {root_cause}"
                    lines.append(line)
        else:
            lines.append("- No archived GitHub issue match was found.")
        lines.append("")
        lines.append("## Root Cause and Recommendations")
        if root_causes:
            for item in root_causes:
                if isinstance(item, dict):
                    cause = str(item.get("cause") or "").strip()
                    confidence = item.get("confidence")
                    if cause:
                        suffix = (
                            f" ({confidence}% confidence)"
                            if isinstance(confidence, (int, float))
                            else ""
                        )
                        lines.append(f"- {cause}{suffix}")
        else:
            lines.append("- No validated root cause was identified.")
        if recommendations:
            lines.append("")
            for recommendation in recommendations:
                lines.append(f"- {recommendation}")
        else:
            lines.append("- No recommendations were generated.")
        lines.append("")
        lines.append("## Source Traceability")
        lines.append(
            "- NASA telemetry evidence was used for the initial diagnostic stage."
        )
        lines.append(
            "- Archived GitHub issue evidence was used as a second-stage institutional knowledge search."
        )
        return "\n".join(lines).strip() + "\n"

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

    def _persist_markdown(self, investigation: InvestigationRun, markdown: str) -> str:
        output_dir = Path(settings.REPORT_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"technical_report_{investigation.id}.md"
        output_path.write_text(markdown, encoding="utf-8")
        log.db("Persisted technical report markdown to %s", output_path)
        return str(output_path)

    def _persist_docx(self, investigation: InvestigationRun, docx_bytes: bytes) -> str:
        output_dir = Path(settings.REPORT_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"technical_report_{investigation.id}.docx"
        output_path.write_bytes(docx_bytes)
        log.db("Persisted technical report docx to %s", output_path)
        return str(output_path)
