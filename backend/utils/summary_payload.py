"""Helpers for working with structured investigation summaries."""

from __future__ import annotations

from typing import Any, Mapping


def get_summary_sections(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the structured summary payload if one is present."""

    sections = state.get("summary_sections")
    if isinstance(sections, dict):
        return sections

    summary = state.get("summary")
    if isinstance(summary, dict):
        return summary

    return {}


def get_summary_text(state: Mapping[str, Any]) -> str:
    """Return the best available summary text for compatibility layers."""

    summary_text = state.get("summary_text")
    if isinstance(summary_text, str) and summary_text.strip():
        return summary_text.strip()

    summary = state.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    sections = get_summary_sections(state)
    for key in ("summary_text", "overview", "headline"):
        value = sections.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""
