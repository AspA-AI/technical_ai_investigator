"""LangGraph nodes routing through the MCP registry with proper state mappings."""

import json
from typing import Any
from sqlalchemy.orm import Session
from models.investigation import InvestigationRun
from models.upload import UploadedFile
from agents.state import InvestigationState
from mcp_registry.server import invoke_mcp_tool
from utils.logger import get_logger
from utils.summary_payload import get_summary_text

log = get_logger(__name__)


def anomaly_detector_node(state: InvestigationState, db: Session) -> dict[str, Any]:
    """Node that detects anomalies and writes detailed engineering telemetry strings."""
    sensor_rows = state.get("sensor_rows", [])
    log.pipeline(
        "Stage 1/6 anomaly detection started sensor_rows=%s",
        len(sensor_rows),
    )
    result = invoke_mcp_tool("anomaly_detector", payload=sensor_rows, db=db)
    log.tool(
        "Stage 1/6 anomaly detection completed anomalies=%s risk=%s",
        len(result.get("anomalies", [])),
        result.get("risk", "low"),
    )

    # FIX: Explicitly capture failure_summary and anomalies list!
    return {
        "anomalies": result.get("anomalies", []),
        "risk_level": result.get("risk", "low"),
        "failure_summary": result.get("failure_summary", ""),
    }


def historical_search_node(state: InvestigationState, db: Session) -> dict[str, Any]:
    """Node that searches historical failure records using the generated physical description."""
    # FIX: This now retrieves the physical summary text from the Anomaly Detector node
    failure_summary = state.get("failure_summary")
    log.pipeline(
        "Stage 1/6 historical search started summary_chars=%s",
        len(str(failure_summary or "")),
    )

    result = invoke_mcp_tool(
        "historical_search", payload=failure_summary, params={"limit": 5}, db=db
    )

    # Track matching state
    match_status = "matched" if (result and len(result) > 0) else "no_match"
    log.tool(
        "Stage 1/6 historical search completed matches=%s status=%s",
        len(result or []),
        match_status,
    )
    return {
        "incidents": result if result else [],
        "historical_match_status": match_status,
    }


def root_cause_analyzer_node(state: InvestigationState, db: Session) -> dict[str, Any]:
    """Node that executes Root Cause Analysis via the MCP server."""
    anomalies = state.get("anomalies", [])
    incidents = state.get("incidents", [])
    log.pipeline(
        "Stage 1/6 root cause analysis started anomalies=%s incidents=%s",
        len(anomalies),
        len(incidents),
    )

    result = invoke_mcp_tool(
        "root_cause_analysis",
        payload={"anomalies": anomalies, "incidents": incidents},
        db=db,
    )
    log.tool("Stage 1/6 root cause analysis completed causes=%s", len(result or []))
    return {"root_causes": result}


def investigation_planner_node(
    state: InvestigationState, db: Session
) -> dict[str, Any]:
    """Node that constructs an investigation plan via the MCP server."""
    root_causes = state.get("root_causes", [])
    log.pipeline(
        "Stage 1/6 investigation planning started root_causes=%s",
        len(root_causes),
    )
    result = invoke_mcp_tool("investigation_planner", payload=root_causes, db=db)
    log.tool("Stage 1/6 investigation planning completed steps=%s", len(result or []))
    return {"recommendations": result}


def summary_generator_node(state: InvestigationState, db: Session) -> dict[str, Any]:
    """Node that compiles the final summary report via the MCP server."""
    log.pipeline("Stage 1/6 summary generation started")
    payload = {
        "anomalies": state.get("anomalies", []),
        "incidents": state.get("incidents", []),
        "root_causes": state.get("root_causes", []),
        "recommendations": state.get("recommendations", []),
        "historical_match_status": state.get("historical_match_status", ""),
    }
    result = invoke_mcp_tool("summary_generator", payload=payload, db=db)
    summary_text = ""
    if isinstance(result, dict):
        summary_text = str(
            result.get("summary_text") or result.get("overview") or ""
        ).strip()
    log.tool(
        "Stage 1/6 summary generation completed summary_chars=%s",
        len(summary_text),
    )
    return {
        "summary": summary_text,
        "summary_text": summary_text,
        "summary_sections": result if isinstance(result, dict) else {},
    }


def archived_issue_search_node(
    state: InvestigationState, db: Session
) -> dict[str, Any]:
    """Stage 2 search over archived GitHub incidents only."""
    summary_query = get_summary_text(state).strip()
    if not summary_query:
        log.pipeline("Stage 2/6 archived issue search skipped: no summary available")
        return {
            "github_matches": [],
            "github_match_status": "no_summary",
        }

    log.pipeline(
        "Stage 2/6 archived issue search started summary_chars=%s",
        len(summary_query),
    )
    result = invoke_mcp_tool(
        "archived_issue_search",
        payload=summary_query,
        params={"limit": 5},
        db=db,
    )
    match_status = "matched" if (result and len(result) > 0) else "no_match"
    log.tool(
        "Stage 2/6 archived issue search completed matches=%s status=%s",
        len(result or []),
        match_status,
    )
    return {
        "github_matches": result if result else [],
        "github_match_status": match_status,
    }


def github_issue_publisher_node(
    state: InvestigationState, db: Session
) -> dict[str, Any]:
    """Node that publishes the completed investigation summary to GitHub."""
    log.pipeline("Stage 2/6 github issue publisher started")
    payload = {
        "asset_id": state.get("upload_id", "unknown-asset"),
        "upload_id": state.get("upload_id", "unknown-asset"),
        "diagnostic_summary": state.get("summary_text") or state.get("summary", ""),
        "summary": state.get("summary_text") or state.get("summary", ""),
        "recommended_tasks": state.get("recommendations", []),
        "recommendations": state.get("recommendations", []),
    }
    result = invoke_mcp_tool("github_issue_publisher", payload=payload, db=db)
    log.tool(
        "Stage 2/6 github issue publisher completed status=%s issue_id=%s",
        result.get("status", "unknown"),
        result.get("issue_id"),
    )
    return {
        "github_issue_status": result.get("status", "unknown"),
        "github_issue_id": result.get("issue_id"),
        "github_issue_url": result.get("issue_url", ""),
        "github_issue_detail": result.get("detail", ""),
    }


def investigation_persistence_node(
    state: InvestigationState, db: Session
) -> dict[str, Any]:
    """Persist the completed investigation state into PostgreSQL."""
    upload_id = str(state.get("upload_id") or "").strip()
    if not upload_id:
        log.pipeline("Stage 3/6 investigation persistence skipped: missing upload_id")
        return {"investigation_status": "skipped"}

    log.pipeline(
        "Stage 3/6 investigation persistence started upload_id=%s", upload_id
    )
    run_status = (
        "no_relevant_historical_match"
        if state.get("historical_match_status") == "no_match"
        else "completed"
    )
    state_json = json.dumps(dict(state), default=str)

    investigation = (
        db.query(InvestigationRun)
        .filter(InvestigationRun.upload_id == upload_id)
        .one_or_none()
    )
    if investigation is None:
        investigation = InvestigationRun(
            upload_id=upload_id,
            status=run_status,
            state_json=state_json,
        )
        db.add(investigation)
        db.flush()
    else:
        investigation.status = run_status
        investigation.state_json = state_json

    upload = (
        db.query(UploadedFile)
        .filter(UploadedFile.upload_id == upload_id)
        .one_or_none()
    )
    if upload is not None:
        upload.investigation_id = investigation.id

    db.commit()
    db.refresh(investigation)
    log.db(
        "Persisted investigation run upload_id=%s investigation_id=%s status=%s",
        upload_id,
        investigation.id,
        run_status,
    )
    return {
        "investigation_id": investigation.id,
        "investigation_status": run_status,
    }


def technical_report_generator_node(
    state: InvestigationState, db: Session
) -> dict[str, Any]:
    """Generate the formal engineering report through the MCP toolchain."""
    investigation_id = int(state.get("investigation_id") or 0)
    if investigation_id <= 0:
        log.pipeline("Stage 4/6 technical report generation skipped: missing investigation_id")
        return {
            "technical_report_status": "skipped",
        }

    log.pipeline(
        "Stage 4/6 technical report generation started investigation_id=%s",
        investigation_id,
    )
    result = invoke_mcp_tool(
        "generate_technical_report",
        payload={"investigation_id": investigation_id},
        db=db,
    )
    report_status = result.get("status", "generated")
    report_path = result.get("report_path", "")
    report_filename = result.get("filename", "")

    investigation = (
        db.query(InvestigationRun)
        .filter(InvestigationRun.id == investigation_id)
        .one_or_none()
    )
    if investigation is not None and investigation.state_json:
        try:
            parsed = json.loads(investigation.state_json)
            if isinstance(parsed, dict):
                parsed.update(
                    {
                        "technical_report_status": report_status,
                        "technical_report_filename": report_filename,
                        "technical_report_path": report_path,
                        "technical_report_preview": result.get("preview", ""),
                    }
                )
                investigation.state_json = json.dumps(parsed, default=str)
                db.commit()
        except json.JSONDecodeError:
            log.warning(
                "Skipping technical report metadata update because state_json is invalid for investigation_id=%s",
                investigation_id,
            )

    log.tool(
        "Stage 4/6 technical report generation completed status=%s path=%s",
        report_status,
        report_path,
    )
    return {
        "technical_report_status": report_status,
        "technical_report_filename": report_filename,
        "technical_report_path": report_path,
        "technical_report_preview": result.get("preview", ""),
    }
