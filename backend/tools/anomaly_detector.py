"""Tool 1: Isolation Forest, Z-Score, Threshold Detection (Phase 5)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from tools.base import BaseTool

NUMERIC_FIELDS = ("temperature", "pressure", "vibration", "rpm")


class AnomalyDetector(BaseTool[list[dict[str, Any]], dict[str, Any]]):
    name = "anomaly_detector"

    def run(self, payload: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        if not payload:
            return {
                "temperature_spike": False,
                "pressure_drop": False,
                "risk": "low",
                "failure_summary": "No sensor rows were provided for anomaly detection.",
                "signals": {},
            }

        frame = pd.DataFrame(payload)
        available = [field for field in NUMERIC_FIELDS if field in frame.columns]
        if not available:
            return {
                "temperature_spike": False,
                "pressure_drop": False,
                "risk": "low",
                "failure_summary": "Sensor rows did not contain the expected telemetry fields.",
                "signals": {},
            }

        numeric = frame[available].apply(pd.to_numeric, errors="coerce").dropna(how="all")
        if numeric.empty:
            return {
                "temperature_spike": False,
                "pressure_drop": False,
                "risk": "low",
                "failure_summary": "Sensor telemetry could not be converted into numeric values.",
                "signals": {},
            }

        last_row = numeric.iloc[-1]
        baseline = numeric.iloc[:-1] if len(numeric) > 1 else numeric
        means = baseline.mean()
        stds = baseline.std(ddof=0).replace(0, np.nan)
        z_scores = ((last_row - means) / stds).fillna(0.0)

        flags = self._evaluate_flags(last_row, means, stds, z_scores)
        risk = self._classify_risk(flags, len(numeric), numeric)
        signals = {
            field: round(
                float(z_scores.get(field, 0.0))
                if not np.isnan(stds.get(field, np.nan))
                else float(last_row[field] - means.get(field, last_row[field])),
                3,
            )
            for field in available
        }

        failure_summary = self._build_failure_summary(flags, signals, last_row)
        return {
            **flags,
            "risk": risk,
            "failure_summary": failure_summary,
            "signals": signals,
            "row_count": int(len(numeric)),
            "latest_measurements": {
                field: round(float(last_row[field]), 3) for field in available
            },
        }

    @staticmethod
    def _evaluate_flags(last_row, means, stds, z_scores) -> dict[str, bool]:
        temperature_spike = bool(
            (last_row.get("temperature") is not None)
            and (
                last_row["temperature"] > means.get("temperature", last_row["temperature"])
                or z_scores.get("temperature", 0.0) >= 1.5
            )
        )
        pressure_drop = bool(
            (last_row.get("pressure") is not None)
            and (
                last_row["pressure"] < means.get("pressure", last_row["pressure"])
                or z_scores.get("pressure", 0.0) <= -1.5
            )
        )
        vibration_spike = bool(
            (last_row.get("vibration") is not None)
            and (
                last_row["vibration"] > means.get("vibration", last_row["vibration"])
                or z_scores.get("vibration", 0.0) >= 1.5
            )
        )
        rpm_drop = bool(
            (last_row.get("rpm") is not None)
            and (
                last_row["rpm"] < means.get("rpm", last_row["rpm"])
                or z_scores.get("rpm", 0.0) <= -1.5
            )
        )
        return {
            "temperature_spike": temperature_spike,
            "pressure_drop": pressure_drop,
            "vibration_spike": vibration_spike,
            "rpm_drop": rpm_drop,
        }

    @staticmethod
    def _classify_risk(flags: dict[str, bool], row_count: int, numeric: pd.DataFrame) -> str:
        score = sum(1 for value in flags.values() if value)

        if len(numeric) >= 10:
            try:
                model = IsolationForest(
                    n_estimators=100,
                    contamination=min(0.2, max(0.01, 1.0 / len(numeric))),
                    random_state=42,
                )
                model.fit(numeric)
                if int(model.predict(numeric.tail(1))[0]) == -1:
                    score += 1
            except Exception:
                pass

        if score >= 3:
            return "high"
        if score == 2:
            return "medium"
        if score == 1 and row_count >= 5:
            return "medium"
        return "low"

    @staticmethod
    def _build_failure_summary(flags: dict[str, bool], signals: dict[str, float], last_row) -> str:
        active = [name.replace("_", " ") for name, enabled in flags.items() if enabled]
        if active:
            headline = ", ".join(active)
        else:
            headline = "no strong anomaly flags"
        top_signal = max(signals.items(), key=lambda item: abs(item[1]), default=("unknown", 0.0))
        return (
            f"Observed {headline} in the latest telemetry. "
            f"The strongest standardized deviation was {top_signal[0]} ({top_signal[1]:+.2f}). "
            f"Latest measurements: temperature={last_row.get('temperature')}, "
            f"pressure={last_row.get('pressure')}, vibration={last_row.get('vibration')}, "
            f"rpm={last_row.get('rpm')}."
        )
