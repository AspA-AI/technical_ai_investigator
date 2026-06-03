from __future__ import annotations

from agents.nodes.root_cause import root_cause_analyzer_node
from agents.nodes.summary import summary_generator_node
import tools.root_cause_analyzer as root_cause_module
import tools.summary_generator as summary_module


def test_root_cause_analyzer_node_uses_llm(monkeypatch) -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return '[{"cause": "cooling degradation", "confidence": 88, "evidence": ["Matched incident data"]}]'

    monkeypatch.setattr(root_cause_module, "LLMClient", FakeLLMClient)

    result = root_cause_analyzer_node(
        {
            "anomalies": [{"temperature_spike": True, "pressure_drop": True}],
            "incidents": [{"incident_id": 5, "root_cause": "cooling degradation", "similarity": 0.88}],
        }
    )

    assert isinstance(result["root_causes"], list)
    assert result["root_causes"][0]["cause"] == "cooling degradation"
    assert result["root_causes"][0]["confidence"] == 88


def test_summary_generator_node_uses_llm(monkeypatch) -> None:
    class FakeLLMClient:
        def generate_text(self, prompt: str, max_tokens: int = 0, temperature: float = 0.0) -> str:
            return "Generated investigation summary."

    monkeypatch.setattr(summary_module, "LLMClient", FakeLLMClient)

    result = summary_generator_node(
        {
            "anomalies": [{"temperature_spike": True, "pressure_drop": True}],
            "incidents": [{"incident_id": 42, "failure": "cooling issue", "similarity": 0.85}],
            "root_causes": [{"cause": "cooling degradation", "confidence": 80}],
            "recommendations": ["Inspect cooling system"],
        }
    )

    assert result["summary"] == "Generated investigation summary."


def test_summary_generator_node_falls_back_when_llm_missing(monkeypatch) -> None:
    class BrokenLLMClient:
        def __init__(self) -> None:
            raise ValueError("OPENAI_API_KEY not configured")

    monkeypatch.setattr(summary_module, "LLMClient", BrokenLLMClient)

    result = summary_generator_node(
        {
            "anomalies": [{"temperature_spike": True, "pressure_drop": True}],
            "incidents": [{"incident_id": 99, "failure": "vibration issue", "similarity": 0.95}],
            "root_causes": [{"cause": "bearing wear", "confidence": 75}],
            "recommendations": ["Inspect bearing assembly"],
        }
    )

    assert "Investigation summary:" in result["summary"]
    assert "bearing wear (75%)" in result["summary"]
    assert "99" in result["summary"]
