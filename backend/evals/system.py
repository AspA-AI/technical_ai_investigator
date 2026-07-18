"""System evaluation harness for retrieval and LLM-output quality.

The evaluator intentionally skips pytest-style unit execution and focuses on
the two layers that matter most for this product:

1. Retrieval quality for NASA and archived GitHub knowledge bases
2. LLM output quality for summary generation and technical report synthesis
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import Session

from evals.judge import LLMJudge
from evals.metrics import duplicate_phrase_ratio, normalize_score_5, safe_mean
from services.technical_report_service import TechnicalReportService
from tools.summary_generator import SummaryGenerator
from utils.logger import get_logger
from vectorstore.incident_store import IncidentVectorStore

log = get_logger(__name__)

EVAL_NASA_SOURCE = "eval_nasa"
EVAL_GITHUB_SOURCE = "eval_github"
EVAL_OUTPUT_DIR = Path("docs/evaluations")


@dataclass(frozen=True)
class BenchmarkIncident:
    incident_id: int
    source_type: str
    failure: str
    root_cause: str
    resolution: str
    summary_text: str


@dataclass(frozen=True)
class RetrievalCase:
    name: str
    source_type: str
    query: str
    expected_ids: list[int]
    limit: int = 5


@dataclass(frozen=True)
class SummaryCase:
    name: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReportCase:
    name: str
    state: dict[str, Any]
    investigation_id: int
    upload_id: str
    status: str = "completed"


@dataclass(frozen=True)
class BenchmarkSuite:
    incidents: list[BenchmarkIncident]
    retrieval_cases: list[RetrievalCase]
    summary_cases: list[SummaryCase]
    report_cases: list[ReportCase]


@dataclass
class RetrievalCaseResult:
    name: str
    source_type: str
    expected_ids: list[int]
    ranked_ids: list[int]
    precision_at_1: float
    precision_at_3: float
    recall_at_3: float
    hit_at_1: float
    hit_at_3: float
    mrr: float
    avg_top_similarity: float


@dataclass
class LLMCaseResult:
    name: str
    candidate_type: str
    text: str
    rule_checks: dict[str, Any]
    judge_scores: dict[str, Any]


@dataclass
class EvaluationResult:
    retrieval_cases: list[RetrievalCaseResult] = field(default_factory=list)
    summary_cases: list[LLMCaseResult] = field(default_factory=list)
    report_cases: list[LLMCaseResult] = field(default_factory=list)
    aggregates: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""


def build_default_benchmark_suite() -> BenchmarkSuite:
    incidents = [
        BenchmarkIncident(
            incident_id=910101,
            source_type=EVAL_NASA_SOURCE,
            failure="NASA-style turbofan degradation trajectory with bearing wear",
            root_cause="bearing wear",
            resolution="Inspect bearing assembly and replace worn bearing",
            summary_text=(
                "Severe vibration growth with stable pressure and minor temperature "
                "increase indicates bearing wear near end of life."
            ),
        ),
        BenchmarkIncident(
            incident_id=910102,
            source_type=EVAL_NASA_SOURCE,
            failure="NASA-style turbofan compressor degradation trajectory",
            root_cause="HPC degradation",
            resolution="Inspect high-pressure compressor blades and seals",
            summary_text=(
                "Compressor performance declines under multiple operating conditions "
                "with RPM instability and temperature drift, consistent with HPC degradation."
            ),
        ),
        BenchmarkIncident(
            incident_id=910103,
            source_type=EVAL_NASA_SOURCE,
            failure="NASA-style turbofan fan degradation trajectory",
            root_cause="fan degradation",
            resolution="Inspect fan assembly and verify rotor balance",
            summary_text=(
                "RPM drop, fan imbalance, and vibration rise indicate fan degradation."
            ),
        ),
        BenchmarkIncident(
            incident_id=920101,
            source_type=EVAL_GITHUB_SOURCE,
            failure="Archived issue about bearing wear and repeated vibration alarms",
            root_cause="bearing wear",
            resolution="Replace bearing after lubrication inspection",
            summary_text=(
                "GitHub issue thread documenting repeated vibration alarms, team discussion, "
                "bearing inspection, and final confirmation of worn bearing."
            ),
        ),
        BenchmarkIncident(
            incident_id=920102,
            source_type=EVAL_GITHUB_SOURCE,
            failure="Archived issue about lubrication loss and vibration spike",
            root_cause="insufficient lubrication",
            resolution="Re-lubricate assembly and verify maintenance interval",
            summary_text=(
                "Closed GitHub investigation covering lubrication loss, vibration spike, "
                "and corrective maintenance actions."
            ),
        ),
        BenchmarkIncident(
            incident_id=920103,
            source_type=EVAL_GITHUB_SOURCE,
            failure="Archived issue about compressor seal degradation",
            root_cause="compressor seal degradation",
            resolution="Inspect compressor seals across the operating range",
            summary_text=(
                "Archived issue notes compressor seal degradation under varying loads and "
                "links the conclusion to the final maintenance action."
            ),
        ),
    ]

    retrieval_cases = [
        RetrievalCase(
            name="nasa_bearing_wear",
            source_type=EVAL_NASA_SOURCE,
            query="severe vibration growth stable pressure minor temperature increase bearing wear",
            expected_ids=[910101],
            limit=5,
        ),
        RetrievalCase(
            name="nasa_compressor_degradation",
            source_type=EVAL_NASA_SOURCE,
            query="compressor degradation multiple operating conditions rpm instability",
            expected_ids=[910102],
            limit=5,
        ),
        RetrievalCase(
            name="nasa_fan_degradation",
            source_type=EVAL_NASA_SOURCE,
            query="fan degradation rpm drop vibration rise",
            expected_ids=[910103],
            limit=5,
        ),
        RetrievalCase(
            name="github_bearing_thread",
            source_type=EVAL_GITHUB_SOURCE,
            query="bearing wear discussion with vibration alarms and replacement",
            expected_ids=[920101],
            limit=5,
        ),
        RetrievalCase(
            name="github_lubrication_thread",
            source_type=EVAL_GITHUB_SOURCE,
            query="lubrication loss vibration spike maintenance discussion",
            expected_ids=[920102],
            limit=5,
        ),
        RetrievalCase(
            name="github_compressor_thread",
            source_type=EVAL_GITHUB_SOURCE,
            query="compressor seal degradation archived issue investigation",
            expected_ids=[920103],
            limit=5,
        ),
    ]

    summary_cases = [
        SummaryCase(
            name="bearing_wear_summary",
            payload={
                "anomalies": [
                    "severe vibration growth",
                    "stable pressure",
                    "minor temperature increase",
                ],
                "incidents": [
                    {
                        "incident_id": 910101,
                        "similarity": 0.93,
                        "failure": "NASA-style turbofan degradation trajectory with bearing wear",
                        "root_cause": "bearing wear",
                    }
                ],
                "root_causes": [
                    {"cause": "bearing wear", "confidence": 90, "evidence": ["vibration growth"]},
                ],
                "recommendations": [
                    "Inspect bearing assembly",
                    "Replace worn bearing",
                    "Verify lubrication",
                ],
                "historical_match_status": "matched",
            },
        ),
        SummaryCase(
            name="compressor_summary",
            payload={
                "anomalies": [
                    "temperature spike",
                    "vibration spike",
                    "rpm drop",
                ],
                "incidents": [
                    {
                        "incident_id": 910102,
                        "similarity": 0.91,
                        "failure": "NASA-style turbofan compressor degradation trajectory",
                        "root_cause": "HPC degradation",
                    }
                ],
                "root_causes": [
                    {"cause": "HPC degradation", "confidence": 88, "evidence": ["rpm drop"]},
                ],
                "recommendations": [
                    "Inspect high-pressure compressor blades and seals",
                    "Validate maintenance records",
                ],
                "historical_match_status": "matched",
            },
        ),
    ]

    report_cases = [
        ReportCase(
            name="bearing_report",
            investigation_id=710101,
            upload_id="eval-bearing-001",
            state={
                "anomalies": [
                    "severe vibration growth",
                    "stable pressure",
                    "minor temperature increase",
                ],
                "incidents": [
                    {
                        "incident_id": 910101,
                        "similarity": 0.93,
                        "failure": "NASA-style turbofan degradation trajectory with bearing wear",
                        "root_cause": "bearing wear",
                        "resolution": "Inspect bearing assembly and replace worn bearing",
                    }
                ],
                "github_matches": [
                    {
                        "incident_id": 920101,
                        "similarity": 0.89,
                        "failure": "Archived issue about bearing wear and repeated vibration alarms",
                        "root_cause": "bearing wear",
                        "issue_url": "https://github.com/example/repo/issues/101",
                    }
                ],
                "root_causes": [
                    {"cause": "bearing wear", "confidence": 90, "evidence": ["vibration growth"]},
                ],
                "recommendations": [
                    "Inspect bearing assembly",
                    "Replace worn bearing",
                    "Verify lubrication",
                ],
                "summary_sections": {
                    "headline": "Bearing wear investigation",
                    "overview": (
                        "Vibration growth with stable pressure and a modest temperature rise "
                        "points toward bearing wear."
                    ),
                },
                "summary_text": (
                    "Vibration growth with stable pressure and a modest temperature rise "
                    "points toward bearing wear."
                ),
            },
        ),
        ReportCase(
            name="compressor_report",
            investigation_id=710102,
            upload_id="eval-compressor-001",
            state={
                "anomalies": [
                    "temperature spike",
                    "vibration spike",
                    "rpm drop",
                ],
                "incidents": [
                    {
                        "incident_id": 910102,
                        "similarity": 0.91,
                        "failure": "NASA-style turbofan compressor degradation trajectory",
                        "root_cause": "HPC degradation",
                        "resolution": "Inspect high-pressure compressor blades and seals",
                    }
                ],
                "github_matches": [
                    {
                        "incident_id": 920103,
                        "similarity": 0.88,
                        "failure": "Archived issue about compressor seal degradation",
                        "root_cause": "compressor seal degradation",
                        "issue_url": "https://github.com/example/repo/issues/103",
                    }
                ],
                "root_causes": [
                    {"cause": "HPC degradation", "confidence": 88, "evidence": ["rpm drop"]},
                ],
                "recommendations": [
                    "Inspect high-pressure compressor blades and seals",
                    "Validate maintenance records",
                ],
                "summary_sections": {
                    "headline": "Compressor degradation investigation",
                    "overview": (
                        "Temperature rise, vibration growth, and RPM instability are consistent "
                        "with compressor degradation."
                    ),
                },
                "summary_text": (
                    "Temperature rise, vibration growth, and RPM instability are consistent "
                    "with compressor degradation."
                ),
            },
        ),
    ]

    return BenchmarkSuite(
        incidents=incidents,
        retrieval_cases=retrieval_cases,
        summary_cases=summary_cases,
        report_cases=report_cases,
    )


def seed_benchmark_corpus(db: Session, suite: BenchmarkSuite | None = None) -> int:
    suite = suite or build_default_benchmark_suite()
    store = IncidentVectorStore(db)
    seeded = 0
    for incident in suite.incidents:
        store.upsert_incident(
            incident_id=incident.incident_id,
            summary_text=incident.summary_text,
            failure=incident.failure,
            root_cause=incident.root_cause,
            resolution=incident.resolution,
            source_type=incident.source_type,
        )
        seeded += 1
    return seeded


def evaluate_system(db: Session) -> EvaluationResult:
    suite = build_default_benchmark_suite()
    seeded = seed_benchmark_corpus(db, suite)
    log.service("Seeded %s benchmark incidents for evaluation", seeded)

    store = IncidentVectorStore(db)
    judge = LLMJudge()

    retrieval_results = [
        _evaluate_retrieval_case(store, case) for case in suite.retrieval_cases
    ]
    summary_results = [
        _evaluate_summary_case(case, judge) for case in suite.summary_cases
    ]
    report_results = [
        _evaluate_report_case(case, judge) for case in suite.report_cases
    ]

    aggregates = _build_aggregates(retrieval_results, summary_results, report_results)
    return EvaluationResult(
        retrieval_cases=retrieval_results,
        summary_cases=summary_results,
        report_cases=report_results,
        aggregates=aggregates,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def persist_evaluation_result(result: EvaluationResult, output_dir: Path | None = None) -> tuple[Path, Path]:
    output_dir = output_dir or EVAL_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"system_eval_{stamp}.json"
    md_path = output_dir / f"system_eval_{stamp}.md"

    json_path.write_text(
        json.dumps(asdict(result), indent=2, default=str),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown_report(result), encoding="utf-8")
    return json_path, md_path


def render_markdown_report(result: EvaluationResult) -> str:
    lines: list[str] = []
    lines.append("# System Evaluation Report")
    lines.append("")
    lines.append(f"- Generated at: `{result.generated_at}`")
    lines.append("")

    lines.append("## Overall")
    lines.append(_markdown_table(
        ["Metric", "Value"],
        [
            ["Overall score (0-5)", f"{result.aggregates.get('overall_score_5', 0.0):.2f}"],
            ["Overall score (0-100)", f"{result.aggregates.get('overall_score_100', 0.0):.1f}"],
            ["Retrieval score", f"{result.aggregates.get('retrieval_score_5', 0.0):.2f}"],
            ["LLM-output score", f"{result.aggregates.get('llm_score_5', 0.0):.2f}"],
        ],
    ))
    lines.append("")

    lines.append("## Retrieval Metrics")
    lines.append("")
    lines.append("### NASA Search")
    lines.append(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Hit@1", f"{result.aggregates.get('nasa_hit_at_1', 0.0):.3f}"],
                ["Hit@3", f"{result.aggregates.get('nasa_hit_at_3', 0.0):.3f}"],
                ["Precision@3", f"{result.aggregates.get('nasa_precision_at_3', 0.0):.3f}"],
                ["Recall@3", f"{result.aggregates.get('nasa_recall_at_3', 0.0):.3f}"],
                ["MRR", f"{result.aggregates.get('nasa_mrr', 0.0):.3f}"],
                ["Avg top similarity", f"{result.aggregates.get('nasa_avg_top_similarity', 0.0):.3f}"],
            ],
        )
    )
    lines.append("")
    lines.append("### Archived GitHub Search")
    lines.append(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Hit@1", f"{result.aggregates.get('github_hit_at_1', 0.0):.3f}"],
                ["Hit@3", f"{result.aggregates.get('github_hit_at_3', 0.0):.3f}"],
                ["Precision@3", f"{result.aggregates.get('github_precision_at_3', 0.0):.3f}"],
                ["Recall@3", f"{result.aggregates.get('github_recall_at_3', 0.0):.3f}"],
                ["MRR", f"{result.aggregates.get('github_mrr', 0.0):.3f}"],
                ["Avg top similarity", f"{result.aggregates.get('github_avg_top_similarity', 0.0):.3f}"],
            ],
        )
    )
    lines.append("")

    lines.append("## LLM Output Metrics")
    lines.append("")
    lines.append("### Summary Generation")
    lines.append(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Groundedness", f"{result.aggregates.get('summary_groundedness', 0.0):.2f}"],
                ["Completeness", f"{result.aggregates.get('summary_completeness', 0.0):.2f}"],
                ["Clarity", f"{result.aggregates.get('summary_clarity', 0.0):.2f}"],
                ["Conciseness", f"{result.aggregates.get('summary_conciseness', 0.0):.2f}"],
                ["Structure", f"{result.aggregates.get('summary_structure', 0.0):.2f}"],
                ["Duplicate phrase ratio", f"{result.aggregates.get('summary_duplicate_ratio', 0.0):.3f}"],
            ],
        )
    )
    lines.append("")
    lines.append("### Technical Report Generation")
    lines.append(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Groundedness", f"{result.aggregates.get('report_groundedness', 0.0):.2f}"],
                ["Completeness", f"{result.aggregates.get('report_completeness', 0.0):.2f}"],
                ["Clarity", f"{result.aggregates.get('report_clarity', 0.0):.2f}"],
                ["Conciseness", f"{result.aggregates.get('report_conciseness', 0.0):.2f}"],
                ["Structure", f"{result.aggregates.get('report_structure', 0.0):.2f}"],
                ["Duplicate phrase ratio", f"{result.aggregates.get('report_duplicate_ratio', 0.0):.3f}"],
                ["Section coverage", f"{result.aggregates.get('report_section_coverage', 0.0):.3f}"],
            ],
        )
    )
    lines.append("")

    lines.append("## Case Details")
    lines.append("")
    lines.append("### Retrieval Cases")
    for case in result.retrieval_cases:
        lines.append(f"- `{case.name}` | ranked: `{case.ranked_ids}` | expected: `{case.expected_ids}`")
    lines.append("")
    lines.append("### Summary Cases")
    for case in result.summary_cases:
        lines.append(
            f"- `{case.name}` | overall: `{case.judge_scores.get('overall', 0.0):.2f}` | duplicate ratio: `{case.rule_checks.get('duplicate_phrase_ratio', 0.0):.3f}`"
        )
    lines.append("")
    lines.append("### Report Cases")
    for case in result.report_cases:
        lines.append(
            f"- `{case.name}` | overall: `{case.judge_scores.get('overall', 0.0):.2f}` | sections: `{case.rule_checks.get('section_coverage', 0.0):.3f}`"
        )

    return "\n".join(lines).strip() + "\n"


def _evaluate_retrieval_case(store: IncidentVectorStore, case: RetrievalCase) -> RetrievalCaseResult:
    matches = store.similarity_search(case.query, limit=case.limit, source_type=case.source_type)
    ranked_ids = [int(item.get("incident_id", 0)) for item in matches]
    expected_ids = [int(item) for item in case.expected_ids]
    top1 = ranked_ids[:1]
    top3 = ranked_ids[:3]
    top_similarity = float(matches[0].get("similarity", 0.0)) if matches else 0.0
    hits_top1 = len(set(top1) & set(expected_ids))
    hits_top3 = len(set(top3) & set(expected_ids))
    reciprocal_rank = 0.0
    for idx, incident_id in enumerate(ranked_ids, start=1):
        if incident_id in expected_ids:
            reciprocal_rank = 1.0 / idx
            break

    precision_at_3 = hits_top3 / 3 if 3 else 0.0
    recall_at_3 = hits_top3 / len(expected_ids) if expected_ids else 0.0

    return RetrievalCaseResult(
        name=case.name,
        source_type=case.source_type,
        expected_ids=expected_ids,
        ranked_ids=ranked_ids,
        precision_at_1=hits_top1 / 1 if top1 else 0.0,
        precision_at_3=precision_at_3,
        recall_at_3=recall_at_3,
        hit_at_1=1.0 if hits_top1 else 0.0,
        hit_at_3=1.0 if hits_top3 else 0.0,
        mrr=reciprocal_rank,
        avg_top_similarity=top_similarity,
    )


def _evaluate_summary_case(case: SummaryCase, judge: LLMJudge) -> LLMCaseResult:
    candidate = SummaryGenerator().run(case.payload)
    summary_text = str(candidate.get("summary_text") or "").strip()
    overview = str(candidate.get("overview") or "").strip()
    candidate_text = json.dumps(candidate, indent=2, default=str)
    required_keys = {
        "headline",
        "overview",
        "anomalies",
        "historical_matches",
        "root_causes",
        "recommendations",
        "action_plan",
        "summary_text",
    }
    rule_checks = {
        "json_valid": bool(candidate),
        "required_key_coverage": len(required_keys & set(candidate.keys())) / len(required_keys),
        "duplicate_phrase_ratio": duplicate_phrase_ratio(summary_text or overview),
        "summary_length_words": len((summary_text or overview).split()),
    }
    judge_scores = judge.score_summary(
        case_name=case.name,
        context=json.dumps(case.payload, indent=2, default=str),
        candidate_text=candidate_text,
    )
    return LLMCaseResult(
        name=case.name,
        candidate_type="summary",
        text=candidate_text,
        rule_checks=rule_checks,
        judge_scores=judge_scores,
    )


def _evaluate_report_case(case: ReportCase, judge: LLMJudge) -> LLMCaseResult:
    mock_investigation = SimpleNamespace(
        id=case.investigation_id,
        upload_id=case.upload_id,
        status=case.status,
    )
    service = TechnicalReportService(db=SimpleNamespace())  # type: ignore[arg-type]
    markdown = service._fallback_markdown(  # noqa: SLF001
        investigation=mock_investigation,
        state=case.state,
        sections=case.state.get("summary_sections") or {},
        summary_text=str(case.state.get("summary_text") or ""),
        github_matches=case.state.get("github_matches") or [],
    )

    required_sections = [
        "## Executive Summary",
        "## Anomaly Findings",
        "## Historical NASA Evidence",
        "## Archived GitHub Evidence",
        "## Root Cause and Recommendations",
        "## Source Traceability",
    ]
    section_coverage = sum(1 for section in required_sections if section in markdown) / len(required_sections)
    rule_checks = {
        "section_coverage": section_coverage,
        "duplicate_phrase_ratio": duplicate_phrase_ratio(markdown),
        "has_issue_url": "https://" in markdown,
        "markdown_length_words": len(markdown.split()),
    }
    judge_scores = judge.score_report(
        case_name=case.name,
        context=json.dumps(case.state, indent=2, default=str),
        candidate_text=markdown,
    )
    return LLMCaseResult(
        name=case.name,
        candidate_type="report",
        text=markdown,
        rule_checks=rule_checks,
        judge_scores=judge_scores,
    )


def _build_aggregates(
    retrieval_cases: list[RetrievalCaseResult],
    summary_cases: list[LLMCaseResult],
    report_cases: list[LLMCaseResult],
) -> dict[str, Any]:
    nasa_cases = [case for case in retrieval_cases if case.source_type == EVAL_NASA_SOURCE]
    github_cases = [case for case in retrieval_cases if case.source_type == EVAL_GITHUB_SOURCE]

    summary_groundedness = [normalize_score_5(case.judge_scores.get("groundedness")) for case in summary_cases]
    summary_completeness = [normalize_score_5(case.judge_scores.get("completeness")) for case in summary_cases]
    summary_clarity = [normalize_score_5(case.judge_scores.get("clarity")) for case in summary_cases]
    summary_conciseness = [normalize_score_5(case.judge_scores.get("conciseness")) for case in summary_cases]
    summary_structure = [normalize_score_5(case.judge_scores.get("structure")) for case in summary_cases]
    summary_overall = [normalize_score_5(case.judge_scores.get("overall")) for case in summary_cases]

    report_groundedness = [normalize_score_5(case.judge_scores.get("groundedness")) for case in report_cases]
    report_completeness = [normalize_score_5(case.judge_scores.get("completeness")) for case in report_cases]
    report_clarity = [normalize_score_5(case.judge_scores.get("clarity")) for case in report_cases]
    report_conciseness = [normalize_score_5(case.judge_scores.get("conciseness")) for case in report_cases]
    report_structure = [normalize_score_5(case.judge_scores.get("structure")) for case in report_cases]
    report_overall = [normalize_score_5(case.judge_scores.get("overall")) for case in report_cases]

    nasa_hit_at_1 = safe_mean([case.hit_at_1 for case in nasa_cases])
    nasa_hit_at_3 = safe_mean([case.hit_at_3 for case in nasa_cases])
    nasa_precision_at_3 = safe_mean([case.precision_at_3 for case in nasa_cases])
    nasa_recall_at_3 = safe_mean([case.recall_at_3 for case in nasa_cases])
    nasa_mrr = safe_mean([case.mrr for case in nasa_cases])
    nasa_avg_top_similarity = safe_mean([case.avg_top_similarity for case in nasa_cases])

    github_hit_at_1 = safe_mean([case.hit_at_1 for case in github_cases])
    github_hit_at_3 = safe_mean([case.hit_at_3 for case in github_cases])
    github_precision_at_3 = safe_mean([case.precision_at_3 for case in github_cases])
    github_recall_at_3 = safe_mean([case.recall_at_3 for case in github_cases])
    github_mrr = safe_mean([case.mrr for case in github_cases])
    github_avg_top_similarity = safe_mean([case.avg_top_similarity for case in github_cases])

    retrieval_score = safe_mean(
        [
            nasa_hit_at_1,
            nasa_hit_at_3,
            nasa_recall_at_3,
            nasa_mrr,
            github_hit_at_1,
            github_hit_at_3,
            github_recall_at_3,
            github_mrr,
        ]
    )
    llm_score = safe_mean(
        [
            safe_mean(summary_overall),
            safe_mean(report_overall),
        ]
    )
    overall_score_5 = safe_mean([retrieval_score, llm_score])

    return {
        "nasa_hit_at_1": nasa_hit_at_1,
        "nasa_hit_at_3": nasa_hit_at_3,
        "nasa_precision_at_3": nasa_precision_at_3,
        "nasa_recall_at_3": nasa_recall_at_3,
        "nasa_mrr": nasa_mrr,
        "nasa_avg_top_similarity": nasa_avg_top_similarity,
        "github_hit_at_1": github_hit_at_1,
        "github_hit_at_3": github_hit_at_3,
        "github_precision_at_3": github_precision_at_3,
        "github_recall_at_3": github_recall_at_3,
        "github_mrr": github_mrr,
        "github_avg_top_similarity": github_avg_top_similarity,
        "summary_groundedness": safe_mean(summary_groundedness),
        "summary_completeness": safe_mean(summary_completeness),
        "summary_clarity": safe_mean(summary_clarity),
        "summary_conciseness": safe_mean(summary_conciseness),
        "summary_structure": safe_mean(summary_structure),
        "summary_duplicate_ratio": safe_mean(
            [case.rule_checks.get("duplicate_phrase_ratio", 0.0) for case in summary_cases]
        ),
        "report_groundedness": safe_mean(report_groundedness),
        "report_completeness": safe_mean(report_completeness),
        "report_clarity": safe_mean(report_clarity),
        "report_conciseness": safe_mean(report_conciseness),
        "report_structure": safe_mean(report_structure),
        "report_duplicate_ratio": safe_mean(
            [case.rule_checks.get("duplicate_phrase_ratio", 0.0) for case in report_cases]
        ),
        "report_section_coverage": safe_mean(
            [case.rule_checks.get("section_coverage", 0.0) for case in report_cases]
        ),
        "retrieval_score_5": retrieval_score,
        "llm_score_5": llm_score,
        "overall_score_5": overall_score_5,
        "overall_score_100": overall_score_5 * 20.0,
    }


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator, *body])
