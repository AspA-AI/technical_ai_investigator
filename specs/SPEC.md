# Engineering Failure Investigation Copilot - Specification

## 1. Overview

### 1.1 Purpose

Build an **Engineering Failure Investigation Copilot** that ingests sensor logs, detects anomalies with deterministic tools, searches historical incidents via vector similarity, analyzes root causes with LLM assistance, plans investigations, supports counterfactual what-if analysis, and presents results through a frontend dashboard—including an engineering chat copilot and PDF report generation.

### 1.2 Key Features

**Data Ingestion:**
- User uploads CSV sensor logs (e.g. `engine_001.csv`)
- FastAPI receives file, stores raw file, parses with Pandas, validates columns, stores processed records in PostgreSQL

**Vector Database (Historical Incidents):**
- Store historical incidents in PostgreSQL and index embeddings with PGVector
- Example incident fields: `incident_id`, `failure`, `root_cause`, `resolution`
- Process: create text summary → generate embedding → store in PGVector
- MVP source data: NASA C-MAPSS Turbofan Engine Degradation Dataset, and optionally the AI4I Predictive Maintenance Dataset
- The raw dataset is transformed into incident-style records before embedding and retrieval

**Deterministic Tools (5 + Summary):**
1. **AnomalyDetector** — Isolation Forest, Z-Score, Threshold Detection on sensor log
2. **HistoricalIncidentSearch** — embedding search via PGVector similarity
3. **RootCauseAnalyzer** — LLM analysis using current anomalies + historical incidents
4. **InvestigationPlanner** — produces investigation steps from root causes
5. **CounterfactualAnalysis** — what-if input (e.g. temperature change) → risk reduction estimate
6. **Summary Generator** — final investigation summary (LangGraph terminal node)

**LangGraph Agent:**
- Coordinates all tools in a fixed pipeline after user uploads sensor log
- Shared state: `anomalies`, `incidents`, `root_causes`, `recommendations`, `summary`
- Each node updates state; node output becomes next node input

**MCP Server (after tools work):**
- Expose every tool as MCP tool for consumption by Claude, ChatGPT, Copilot, Internal Engineering Agent

**OpenAI GPT-4o:**
- Root cause analysis, investigation summary, engineering chat, recommendation generation
- GPT must **never** perform: numerical calculations, anomaly detection, vector search (these are deterministic tools)

**Frontend Dashboard (6 pages):**
1. Upload sensor logs
2. Investigation dashboard (risk, anomaly count, historical match count, root cause ranking)
3. Engineering timeline (Recharts: temperature, pressure, vibration, RPM; anomaly highlights)
4. Sensor contribution ranking (bar chart)
5. Historical incidents table
6. Investigation whiteboard (React Flow reasoning graph)

**Report Generation:**
- Collect anomalies, incidents, root causes, recommendations → generate PDF Engineering Investigation Report

**Engineering Chat:**
- User questions: what caused failure, which incident is most similar, what action to take
- LangGraph retrieves current investigation state, historical incidents, relevant metrics; GPT generates answer

**What-If Analysis:**
- User asks e.g. “What if vibration decreases by 20%?”
- Counterfactual tool + historical comparison + statistical estimation
- Output: failure risk reduction (e.g. 37%); display before/after risk

### 1.3 Implementation Phases (Guide)

| Phase | Name |
|-------|------|
| 1 | Project setup |
| 2 | Project structure |
| 3 | Data ingestion |
| 4 | Vector database |
| 5 | Tool implementation |
| 6 | LangGraph agent |
| 7 | MCP server |
| 8 | OpenAI integration |
| 9 | Frontend dashboard |
| 10 | Report generation |
| 11 | Engineering chat |
| 12 | What-if analysis |

### 1.4 Implementation Milestones

| Step | Phase | What you get |
|------|-------|--------------|
| 1–2 | Docker, structure, logging | ✅ Done |
| 3 | CSV upload → Postgres | ✅ Now |
| 4 | Historical incidents + PGVector | Next |
| 5 | 5 deterministic tools (+ summary) | Planned |
| 6 | LangGraph pipeline (`upload_id` → investigation) | Planned |
| 7 | MCP exposure | Planned |
| 8 | GPT boundaries wired into analyzers | Planned |
| 9 | Dashboard fed with real API data | Planned |
| 10–12 | PDF report, engineering chat, what-if | Planned |

**AVL Interview Demonstration Flow** (end-to-end):
1. Upload sensor log
2. Detect anomalies
3. Search historical incidents
4. Generate root causes
5. Produce investigation plan
6. Visualize failure timeline
7. Show reasoning graph
8. Run what-if analysis
9. Generate final report
10. Ask follow-up questions through Engineering Copilot

### 1.5 Implementation Status

**Not yet implemented** — repository initialized; specification derived from Technical Implementation Guide.

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                             │
│  React │ TypeScript │ TailwindCSS │ React Flow │ Recharts   │
│  Axios                                                        │
│  Pages: Upload │ Dashboard │ Timeline │ Ranking │           │
│         Incidents │ Whiteboard │ Chat │ What-If              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP/REST
                     │
┌────────────────────▼─────────────────────────────────────────┐
│              FastAPI Backend                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        LangGraph Investigation Agent                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  backend/tools/     — AnomalyDetector, HistoricalSearch,    │
│                       RootCauseAnalyzer, InvestigationPlanner,│
│                       CounterfactualAnalysis, Summary       │
│  backend/agents/    — LangGraph graph definition              │
│  backend/services/  — ingestion, report, chat               │
│  backend/vectorstore/ — PGVector operations                 │
└────────────────────┬─────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌────▼────┐ ┌───▼────┐
    │PostgreSQL│ │PGVector │ │ OpenAI │
    │ + Pandas │ │Embeddings│ │ GPT-4o │
    └─────────┘ └─────────┘ └────────┘
```

### 2.2 Technology Stack

**Frontend:**
- React
- TypeScript
- TailwindCSS
- Material UI
- React Flow
- Recharts
- Axios

**Backend:**
- Python
- FastAPI
- PostgreSQL
- PGVector
- Pandas
- NumPy
- Scikit-learn

**AI Stack:**
- OpenAI GPT-4o
- OpenAI Embeddings
- LangGraph

**Development:**
- Docker
- Docker Compose

### 2.3 Project Structure (Phase 2)

```
frontend/

backend/

backend/api/
backend/agents/
backend/tools/
backend/models/
backend/services/
backend/vectorstore/
backend/database/
backend/datasets/
```

## 3. Data Ingestion (Phase 3)

### 3.1 User Input

User uploads **CSV sensor logs**.

Example file: `engine_001.csv`

### 3.2 Frontend

React Upload Component → `POST /api/upload`

### 3.3 Backend Process

1. FastAPI receives file
2. Store raw file
3. Parse using Pandas
4. Validate columns
5. Store processed records into PostgreSQL

### 3.4 Response

```json
{
  "status": "success",
  "records": 1200
}
```

## 4. Vector Database (Phase 4)

### 4.1 Goal

Store historical incidents in PostgreSQL and make them searchable through PGVector.

### 4.2 MVP Historical Incident Source

For the MVP, the historical incident knowledge base is generated from the NASA C-MAPSS Turbofan Engine Degradation Dataset, and optionally the AI4I Predictive Maintenance Dataset.

These datasets provide:
- multivariate sensor measurements
- operational settings
- degradation and failure progression patterns
- labels or trajectories that can be converted into incident summaries

The pipeline is:
1. Parse raw dataset records
2. Convert each engine run or failure sequence into an incident-style summary
3. Store the incident record in PostgreSQL
4. Generate embeddings for the summary
5. Index the embedding in PGVector for similarity search

### 4.3 Example Incident

```json
{
  "incident_id": 31,
  "failure": "engine overheating",
  "root_cause": "cooling degradation",
  "resolution": "replace cooling module"
}
```

### 4.4 Tools Used

- OpenAI Embeddings
- PostgreSQL
- PGVector

## 5. Tool Specifications (Phase 5)

### 5.1 Tool 1 — AnomalyDetector

**Input:** Sensor log

**Process:**
- Isolation Forest
- Z-Score
- Threshold Detection

**Output:**

```json
{
  "temperature_spike": true,
  "pressure_drop": true,
  "risk": "high"
}
```

### 5.2 Tool 2 — HistoricalIncidentSearch

**Input:** Failure summary

**Process:**
- Embedding search
- PGVector similarity

**Output:**

```json
[
  {
    "incident_id": 31,
    "similarity": 0.91
  }
]
```

### 5.3 Tool 3 — RootCauseAnalyzer

**Input:**
- Current anomalies
- Historical incidents

**Process:** LLM analysis

**Output:**

```json
[
  {
    "cause": "bearing wear",
    "confidence": 82
  }
]
```

### 5.4 Tool 4 — InvestigationPlanner

**Input:** Root causes

**Output:**

```json
[
  "Inspect bearing assembly",
  "Verify cooling pressure",
  "Check lubrication"
]
```

### 5.5 Tool 5 — CounterfactualAnalysis

**Input:**

```json
{
  "temperature_change": -15
}
```

**Output:**

```json
{
  "risk_reduction": 68
}
```

### 5.6 Summary Generator (LangGraph node)

Terminal node in LangGraph pipeline; produces investigation `summary` for state (see §6).

## 6. LangGraph Agent (Phase 6)

### 6.1 Purpose

Coordinate all tools. User uploads sensor log; LangGraph executes:

```
START
  ↓
Anomaly Detector
  ↓
Historical Search
  ↓
Root Cause Analyzer
  ↓
Investigation Planner
  ↓
Summary Generator
  ↓
END
```

### 6.2 LangGraph State

```json
{
  "anomalies": [],
  "incidents": [],
  "root_causes": [],
  "recommendations": [],
  "summary": ""
}
```

Each node updates state. Node output becomes next node input.

### 6.3 Node-to-Tool Mapping

| Node | Tool |
|------|------|
| Anomaly Detector | AnomalyDetector |
| Historical Search | HistoricalIncidentSearch |
| Root Cause Analyzer | RootCauseAnalyzer |
| Investigation Planner | InvestigationPlanner |
| Summary Generator | Summary Generator |

(CounterfactualAnalysis is used in What-If flow — Phase 12 — not in the main linear pipeline above.)

## 7. MCP Server (Phase 7)

After tools are working, expose every tool as MCP tool.

**MCP Tool List:**
- `anomaly_detector`
- `historical_search`
- `root_cause_analysis`
- `investigation_planner`
- `counterfactual_analysis`
- `summary_generator`

Future LLMs can consume these tools (Claude, ChatGPT, Copilot, Internal Engineering Agent).

## 8. OpenAI Integration (Phase 8)

### 8.1 GPT-4o Responsibilities

- Root cause analysis
- Investigation summary
- Engineering chat
- Recommendation generation

### 8.2 GPT Must NEVER Perform

- Numerical calculations
- Anomaly detection
- Vector search

These must be **deterministic tools**.

## 9. Frontend Dashboard (Phase 9)

### 9.1 Page 1 — Upload Sensor Logs

Upload interface for CSV sensor logs.

### 9.2 Page 2 — Investigation Dashboard

**Widgets:**
- Risk level
- Anomaly count
- Historical match count
- Root cause ranking

### 9.3 Page 3 — Engineering Timeline

**Recharts** display:
- Temperature
- Pressure
- Vibration
- RPM

Highlight anomaly points.

### 9.4 Page 4 — Sensor Contribution Ranking

Bar chart example:
- Temperature 41%
- Vibration 33%
- Pressure 18%
- RPM 8%

### 9.5 Page 5 — Historical Incidents

**Table columns:**
- Incident ID
- Similarity score
- Root cause
- Resolution

### 9.6 Page 6 — Investigation Whiteboard

**React Flow** reasoning graph.

Example graph:

```
Failure
  ↓
Temperature Spike
  ↓
Cooling Degradation
  ↓
Incident #31
  ↓
Recommended Action
```

## 10. Report Generation (Phase 10)

**Endpoint:** `/api/report` (FastAPI)

**Process:**
1. Collect: anomalies, incidents, root causes, recommendations
2. Generate PDF

**Output:** Engineering Investigation Report

## 11. Engineering Chat (Phase 11)

**Example user questions:**
- What caused this failure?
- Which incident is most similar?
- What action should be taken?

**Process:**
1. LangGraph retrieves: current investigation state, historical incidents, relevant metrics
2. GPT generates answer

## 12. What-If Analysis (Phase 12)

**Example user question:** What if vibration decreases by 20%?

**Process:**
1. Counterfactual tool
2. Historical comparison
3. Statistical estimation

**Output example:** Failure risk reduced by 37%

**Display:**
- Before risk
- After risk

## 13. API Endpoints Summary

| Method | Endpoint | Phase | Purpose |
|--------|----------|-------|---------|
| POST | `/api/upload` | 3 | Upload and ingest CSV sensor logs |
| — | `/api/report` | 10 | Generate Engineering Investigation Report (PDF) |

(See [API_CONTRACTS.md](./API_CONTRACTS.md) for request/response detail.)

## 14. AVL Interview Demonstration Flow

1. Upload sensor log
2. Detect anomalies
3. Search historical incidents
4. Generate root causes
5. Produce investigation plan
6. Visualize failure timeline
7. Show reasoning graph
8. Run what-if analysis
9. Generate final report
10. Ask follow-up questions through Engineering Copilot

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-01  
**Status**: Ready for implementation (content from Technical Implementation Guide only)
