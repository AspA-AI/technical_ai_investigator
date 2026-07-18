"""Utility metrics for retrieval and LLM-output evaluation."""

from __future__ import annotations

import re
from statistics import mean
from typing import Any


def safe_mean(values: list[float]) -> float:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    return mean(numeric) if numeric else 0.0


def normalize_score_5(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score <= 0:
        return 0.0
    return max(1.0, min(5.0, score))


def duplicate_phrase_ratio(text: str, ngram_size: int = 3) -> float:
    tokens = re.findall(r"\b\w+\b", text.lower())
    if len(tokens) < ngram_size:
        return 0.0
    grams = [" ".join(tokens[idx : idx + ngram_size]) for idx in range(len(tokens) - ngram_size + 1)]
    if not grams:
        return 0.0
    counts = {}
    for gram in grams:
        counts[gram] = counts.get(gram, 0) + 1
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(grams)

