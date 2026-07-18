"""LLM-as-a-judge and heuristic fallbacks for evaluation outputs."""

from __future__ import annotations

import json
import re
from typing import Any

from llm.client import LLMClient
from utils.logger import get_logger

log = get_logger(__name__)


class LLMJudge:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = LLMClient()
            except ValueError:
                self._llm_client = None

    def score_summary(
        self,
        *,
        case_name: str,
        context: str,
        candidate_text: str,
    ) -> dict[str, Any]:
        return self._score(
            task_name="summary generation",
            case_name=case_name,
            context=context,
            candidate_text=candidate_text,
            expected_structure="summary dict with headline, overview, anomalies, historical_matches, root_causes, recommendations, action_plan, summary_text",
        )

    def score_report(
        self,
        *,
        case_name: str,
        context: str,
        candidate_text: str,
    ) -> dict[str, Any]:
        return self._score(
            task_name="technical report generation",
            case_name=case_name,
            context=context,
            candidate_text=candidate_text,
            expected_structure="markdown report with executive summary, anomaly findings, historical evidence, GitHub evidence, root causes, recommendations, and traceability",
        )

    def _score(
        self,
        *,
        task_name: str,
        case_name: str,
        context: str,
        candidate_text: str,
        expected_structure: str,
    ) -> dict[str, Any]:
        if self._llm_client is not None:
            try:
                prompt = self._build_prompt(
                    task_name=task_name,
                    case_name=case_name,
                    context=context,
                    candidate_text=candidate_text,
                    expected_structure=expected_structure,
                )
                response = self._llm_client.generate_text(
                    prompt, max_tokens=700, temperature=0.0
                )
                parsed = self._extract_json(response)
                if parsed:
                    return self._normalize_scores(parsed)
            except Exception as exc:
                log.warning("LLM judge failed for case=%s task=%s: %s", case_name, task_name, exc)

        return self._heuristic_score(
            task_name=task_name,
            context=context,
            candidate_text=candidate_text,
            expected_structure=expected_structure,
        )

    @staticmethod
    def _build_prompt(
        *,
        task_name: str,
        case_name: str,
        context: str,
        candidate_text: str,
        expected_structure: str,
    ) -> str:
        return (
            "You are grading an engineering AI evaluation output.\n"
            "Return JSON only with numeric scores from 1 to 5.\n"
            "Use these fields exactly: groundedness, completeness, clarity, conciseness, structure, overall, rationale.\n"
            "Overall should be the average of the five category scores.\n"
            "Focus on whether the candidate is supported by the context, covers the needed content, reads clearly, avoids repetition, "
            "and follows the expected structure.\n\n"
            f"Task: {task_name}\n"
            f"Case: {case_name}\n"
            f"Expected structure: {expected_structure}\n\n"
            f"Context:\n{context}\n\n"
            f"Candidate:\n{candidate_text}\n"
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _normalize_scores(payload: dict[str, Any]) -> dict[str, Any]:
        scores = {
            "groundedness": LLMJudge._as_score(payload.get("groundedness")),
            "completeness": LLMJudge._as_score(payload.get("completeness")),
            "clarity": LLMJudge._as_score(payload.get("clarity")),
            "conciseness": LLMJudge._as_score(payload.get("conciseness")),
            "structure": LLMJudge._as_score(payload.get("structure")),
        }
        overall = LLMJudge._as_score(payload.get("overall"))
        if overall <= 0:
            overall = sum(scores.values()) / len(scores)
        scores["overall"] = overall
        scores["rationale"] = str(payload.get("rationale") or "").strip()
        return scores

    @staticmethod
    def _as_score(value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(1.0, min(5.0, score))

    @staticmethod
    def _heuristic_score(
        *,
        task_name: str,
        context: str,
        candidate_text: str,
        expected_structure: str,
    ) -> dict[str, Any]:
        context_tokens = set(re.findall(r"\b\w+\b", context.lower()))
        candidate_tokens = set(re.findall(r"\b\w+\b", candidate_text.lower()))
        overlap = len(context_tokens & candidate_tokens) / max(1, len(context_tokens))
        length_words = len(candidate_text.split())
        candidate_lower = candidate_text.lower()
        if task_name == "summary generation":
            structure_hit = all(
                token in candidate_lower
                for token in ["headline", "overview", "historical_matches", "root_causes", "summary_text"]
            )
        elif task_name == "technical report generation":
            structure_hit = all(
                heading in candidate_lower
                for heading in [
                    "executive summary",
                    "anomaly findings",
                    "historical nasa evidence",
                    "archived github evidence",
                    "root cause and recommendations",
                    "source traceability",
                ]
            )
        else:
            structure_hit = False

        groundedness = 1.0 + 4.0 * min(1.0, overlap * 2.0)
        completeness = 1.0 + 4.0 * min(1.0, overlap + (0.2 if structure_hit else 0.0))
        clarity = 5.0 if 30 <= length_words <= 300 else max(1.0, 5.0 - abs(length_words - 120) / 60.0)
        conciseness = 5.0 if (60 <= length_words <= 260 and duplicate_penalty(candidate_text) < 0.08) else max(
            1.0, 5.0 - abs(length_words - 150) / 70.0
        )
        structure = 5.0 if structure_hit else 3.0
        overall = (groundedness + completeness + clarity + conciseness + structure) / 5.0
        return {
            "groundedness": round(groundedness, 2),
            "completeness": round(completeness, 2),
            "clarity": round(clarity, 2),
            "conciseness": round(conciseness, 2),
            "structure": round(structure, 2),
            "overall": round(overall, 2),
            "rationale": f"Heuristic fallback judge for {task_name}.",
        }


def duplicate_penalty(text: str) -> float:
    tokens = re.findall(r"\b\w+\b", text.lower())
    if len(tokens) < 6:
        return 0.0
    grams = [" ".join(tokens[idx : idx + 3]) for idx in range(len(tokens) - 2)]
    if not grams:
        return 0.0
    unique = len(set(grams))
    return 1.0 - unique / len(grams)
