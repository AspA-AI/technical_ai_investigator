from __future__ import annotations

import json

from tools.anomaly_detector import AnomalyDetector
from tools.counterfactual_analysis import CounterfactualAnalysis
from tools.historical_incident_search import HistoricalIncidentSearch
from tools.investigation_planner import InvestigationPlanner
from tools.root_cause_analyzer import RootCauseAnalyzer
from tools.summary_generator import SummaryGenerator


def test_anomaly_detector_identifies_sensor_outliers() -> None:
    rows = [
        {
            "timestamp": f"2026-01-01T00:0{i}:00Z",
            "temperature": 100.0,
            "pressure": 12.0,
            "vibration": 4.0,
            "rpm": 1500.0,
        }
        for i in range(9)
    ]
    rows.append(
        {
            "timestamp": "2026-01-01T00:09:00Z",
            "temperature": 145.0,
            "pressure": 3.5,
            "vibration": 11.0,
            "rpm": 900.0,
        }
    )

    result = AnomalyDetector().run(rows)

    assert result["temperature_spike"] is True
    assert result["pressure_drop"] is True
    assert result["vibration_spike"] is True
    assert result["rpm_drop"] is True
    assert result["risk"] == "high"
    assert "failure_summary" in result and result["failure_summary"]
    assert result["signals"]["temperature"] > 0
    assert result["latest_measurements"]["rpm"] == 900.0


def test_historical_incident_search_uses_vector_store() -> None:
    class FakeVectorStore:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int]] = []

        def similarity_search(self, query: str, limit: int = 5):
            self.calls.append((query, limit))
            return [{"incident_id": 31, "similarity": 0.91}]

    vector_store = FakeVectorStore()
    search = HistoricalIncidentSearch(vector_store=vector_store)

    result = search.run(" compressor degradation and vibration rise ", limit=3)

    assert result == [{"incident_id": 31, "similarity": 0.91}]
    assert vector_store.calls == [("compressor degradation and vibration rise", 3)]


def test_root_cause_analyzer_ranks_matching_causes() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return json.dumps([
                {
                    "cause": "HPC degradation",
                    "confidence": 92,
                    "evidence": ["Matched similar historical failure"],
                },
                {
                    "cause": "cooling degradation",
                    "confidence": 85,
                    "evidence": ["Temperature spike and pressure drop"],
                },
                {
                    "cause": "bearing wear",
                    "confidence": 78,
                    "evidence": ["Vibration rise matched prior incidents"],
                },
            ])

    result = RootCauseAnalyzer(llm_client=FakeLLMClient()).run(
        {
            "anomalies": [
                {
                    "temperature_spike": True,
                    "pressure_drop": True,
                    "vibration_spike": True,
                    "rpm_drop": True,
                }
            ],
            "incidents": [
                {
                    "incident_id": 88,
                    "similarity": 0.9,
                    "root_cause": "HPC degradation",
                }
            ],
        }
    )

    causes = [item["cause"] for item in result]

    assert "HPC degradation" in causes
    assert "cooling degradation" in causes
    assert "bearing wear" in causes
    assert all("confidence" in item for item in result)
    assert any(item["evidence"] for item in result)


def test_investigation_planner_generates_unique_steps() -> None:
    planner = InvestigationPlanner()
    steps = planner.run(
        [
            {"cause": "cooling degradation"},
            {"cause": "bearing wear"},
            {"cause": "lubrication stress"},
            {"cause": "drive train inefficiency"},
            {"cause": "HPC degradation"},
            {"cause": "insufficient evidence"},
        ]
    )

    assert steps == [
        "Inspect cooling system pressure and flow",
        "Check heat exchanger performance",
        "Inspect bearing assembly for wear and lubrication loss",
        "Verify lubrication volume, viscosity, and delivery path",
        "Inspect drive train alignment and rotating components",
        "Inspect high-pressure compressor blades and seals",
        "Collect additional telemetry and review maintenance history",
        "Correlate findings with similar historical incidents",
        "Validate the final hypothesis with maintenance and inspection records",
    ]


def test_counterfactual_analysis_computes_risk_delta() -> None:
    result = CounterfactualAnalysis().run(
        {
            "baseline_risk": 80,
            "temperature_change": -10,
            "pressure_change": -5,
            "vibration_change": -2,
            "rpm_change": 10,
        }
    )

    assert result["risk_reduction"] == 32
    assert result["before_risk"] == 80
    assert result["after_risk"] == 48
    assert result["assumptions"]["temperature_change"] == -10.0


def test_summary_generator_compacts_pipeline_state() -> None:
    summary = SummaryGenerator().run(
        {
            "anomalies": [
                {
                    "temperature_spike": True,
                    "pressure_drop": True,
                    "risk": "high",
                }
            ],
            "incidents": [{"incident_id": 31}],
            "root_causes": [{"cause": "bearing wear", "confidence": 82}],
            "recommendations": ["Inspect bearing assembly"],
        }
    )

    assert summary.startswith("Investigation summary:")
    assert "temperature spike, pressure drop" in summary
    assert "31" in summary
    assert "bearing wear (82%)" in summary
    assert "1 investigation step(s)" in summary


def test_root_cause_analyzer_parses_llm_json_output() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return '[{"cause": "cooling degradation", "confidence": 88, "evidence": ["Matched incident data"]}]'

    analyzer = RootCauseAnalyzer(llm_client=FakeLLMClient())
    result = analyzer.run({"anomalies": [{"temperature_spike": True}], "incidents": [{"incident_id": 21, "root_cause": "cooling degradation", "similarity": 0.92}]})

    assert isinstance(result, list)
    assert result[0]["cause"] == "cooling degradation"
    assert result[0]["confidence"] == 88
    assert result[0]["evidence"] == ["Matched incident data"]


def test_root_cause_analyzer_falls_back_on_invalid_llm_response() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return 'not valid json'

    analyzer = RootCauseAnalyzer(llm_client=FakeLLMClient())
    result = analyzer.run({"anomalies": [{"pressure_drop": True}], "incidents": [{"incident_id": 33, "root_cause": "bearing wear", "similarity": 0.75}]})

    assert any(item["cause"] == "bearing wear" for item in result)
    assert all("confidence" in item for item in result)


def test_summary_generator_returns_llm_summary() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return "This is a generated investigation summary."

    summary_tool = SummaryGenerator(llm_client=FakeLLMClient())
    summary = summary_tool.run({
        "anomalies": [{"temperature_spike": True}],
        "incidents": [{"incident_id": 42, "failure": "cooling issue", "similarity": 0.85}],
        "root_causes": [{"cause": "cooling degradation", "confidence": 80}],
        "recommendations": ["Inspect cooling system"],
    })

    assert summary == "This is a generated investigation summary."


def test_summary_generator_fallback_on_llm_error() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            raise RuntimeError("LLM unavailable")

    summary_tool = SummaryGenerator(llm_client=FakeLLMClient())
    summary = summary_tool.run({
        "anomalies": [{"temperature_spike": True, "pressure_drop": True}],
        "incidents": [{"incident_id": 99, "failure": "vibration issue", "similarity": 0.95}],
        "root_causes": [{"cause": "bearing wear", "confidence": 75}],
        "recommendations": ["Inspect bearing assembly"],
    })

    assert "Investigation summary:" in summary
    assert "bearing wear (75%)" in summary
    assert "99" in summary


def test_root_cause_analyzer_surfaces_degraded_notice_on_llm_error() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            raise RuntimeError("boom")

    result = RootCauseAnalyzer(llm_client=FakeLLMClient()).run(
        {
            "anomalies": [{"pressure_drop": True}],
            "incidents": [{"incident_id": 33, "root_cause": "bearing wear", "similarity": 0.75}],
        }
    )

    assert result, "expected a heuristic fallback result"
    assert all(item.get("degraded") is True for item in result)
    assert all(item.get("notice") for item in result)
    assert any("without the language model" in item["notice"] for item in result)
    assert any("boom" in item["notice"] for item in result)


def test_root_cause_analyzer_not_degraded_when_llm_succeeds() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return '[{"cause": "cooling degradation", "confidence": 88, "evidence": ["x"]}]'

    result = RootCauseAnalyzer(llm_client=FakeLLMClient()).run(
        {"anomalies": [{"temperature_spike": True}], "incidents": []}
    )

    assert all("degraded" not in item for item in result)
    assert all("notice" not in item for item in result)


def test_summary_generator_surfaces_degraded_note_on_llm_error() -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            raise RuntimeError("boom")

    summary = SummaryGenerator(llm_client=FakeLLMClient()).run(
        {
            "anomalies": [{"temperature_spike": True}],
            "incidents": [],
            "root_causes": [{"cause": "bearing wear", "confidence": 75}],
            "recommendations": ["Inspect bearing assembly"],
        }
    )

    assert summary.startswith("Investigation summary:")
    assert "heuristic summary generated without the language model" in summary
    assert "boom" in summary
