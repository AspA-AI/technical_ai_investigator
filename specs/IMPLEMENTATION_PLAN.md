# Implementation Plan

## Overview

This document outlines the implementation plan for the **Engineering Failure Investigation Copilot**, aligned phase-for-phase with the Technical Implementation Guide (Phases 1–12) and the AVL interview demonstration flow.

## Implementation Phases

### Phase 1: Project Setup ✅

**Goal**: Establish development environment and dependencies.

**Stack**:

| Layer | Technologies |
|-------|----------------|
| Frontend | React, TypeScript, TailwindCSS, React Flow, Recharts, Axios |
| Backend | Python, FastAPI, PostgreSQL, PGVector, Pandas, NumPy, Scikit-learn |
| AI | OpenAI GPT-4o, OpenAI Embeddings, LangGraph |
| Development | Docker, Docker Compose |

**Tasks**:
- [ ] Configure frontend (React, TypeScript, TailwindCSS, React Flow, Recharts, Axios)
- [ ] Configure backend (Python, FastAPI, PostgreSQL, PGVector, Pandas, NumPy, Scikit-learn)
- [ ] Configure AI stack (OpenAI GPT-4o, OpenAI Embeddings, LangGraph)
- [ ] Set up Docker and Docker Compose

**Acceptance Criteria**:
- All listed technologies are installable and runnable in dev environment
- Docker Compose brings up required services

---

### Phase 2: Project Structure ✅

**Goal**: Create repository layout.

**Target structure**:

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

**Tasks**:
- [ ] Create `frontend/` directory
- [ ] Create `backend/` and subdirectories: `api/`, `agents/`, `tools/`, `models/`, `services/`, `vectorstore/`, `database/`, `datasets/`

**Acceptance Criteria**:
- Directory structure matches guide

**Files to Create**:
- Directory scaffold only (per structure above)

---

### Phase 3: Data Ingestion ✅

**Goal**: Upload and persist CSV sensor logs.

**Tasks**:
- [x] Frontend: React Upload Component
- [x] Backend: `POST /api/upload` — receive file, store raw file
- [x] Parse using Pandas
- [x] Validate columns
- [x] Store processed records into PostgreSQL
- [x] Return `{ "status": "success", "records": <count>, "upload_id": "<id>" }`

**Acceptance Criteria**:
- User can upload CSV (e.g. `engine_001.csv`)
- Response matches guide format with correct `records` count
- Processed data stored in PostgreSQL

**Files to Create/Modify**:
- `frontend/` — upload component
- `backend/api/` — upload route
- `backend/services/` — ingestion service
- `backend/database/` — persistence layer

---

### Phase 4: Vector Database

**Goal**: Store historical incidents with embeddings in PGVector.

**Example incident**:

```json
{
  "incident_id": 31,
  "failure": "engine overheating",
  "root_cause": "cooling degradation",
  "resolution": "replace cooling module"
}
```

**Process**:
1. Create text summary
2. Generate embedding (OpenAI Embeddings)
3. Store embedding in PGVector

**Tools**: OpenAI Embeddings, PostgreSQL, PGVector

**Tasks**:
- [ ] Define incident model / storage schema
- [ ] Implement text summary creation
- [ ] Generate embeddings and store in PGVector
- [ ] Seed or load historical incidents (e.g. via `backend/datasets/`)

**Acceptance Criteria**:
- Incidents can be stored and retrieved for similarity search
- Embedding pipeline uses OpenAI Embeddings + PGVector

**Files to Create/Modify**:
- `backend/vectorstore/`
- `backend/models/`
- `backend/database/`

---

### Phase 5: Tool Implementation

**Goal**: Implement five deterministic tools (+ summary generator used in Phase 6).

#### 5.1 AnomalyDetector

**Input**: Sensor log  
**Process**: Isolation Forest, Z-Score, Threshold Detection  
**Output**: `{ "temperature_spike": true, "pressure_drop": true, "risk": "high" }`

**Tasks**:
- [ ] Implement in `backend/tools/`
- [ ] Unit test against sample sensor log

#### 5.2 HistoricalIncidentSearch

**Input**: Failure summary  
**Process**: Embedding search, PGVector similarity  
**Output**: `[{ "incident_id": 31, "similarity": 0.91 }]`

**Tasks**:
- [ ] Implement search against PGVector
- [ ] Return similarity-ranked incidents

#### 5.3 RootCauseAnalyzer

**Input**: Current anomalies, historical incidents  
**Process**: LLM analysis  
**Output**: `[{ "cause": "bearing wear", "confidence": 82 }]`

**Tasks**:
- [ ] Implement LLM call (GPT-4o) with structured output
- [ ] Wire inputs from anomaly + incident tools

#### 5.4 InvestigationPlanner

**Input**: Root causes  
**Output**: `["Inspect bearing assembly", "Verify cooling pressure", "Check lubrication"]`

**Tasks**:
- [ ] Implement planner tool

#### 5.5 CounterfactualAnalysis

**Input**: `{ "temperature_change": -15 }`  
**Output**: `{ "risk_reduction": 68 }`

**Tasks**:
- [ ] Implement counterfactual tool (used in Phase 12)

**Acceptance Criteria**:
- Each tool produces output matching guide schemas
- Numerical/anomaly/vector work remains in deterministic tools (not GPT)

**Files to Create**:
- `backend/tools/anomaly_detector.py` (or equivalent)
- `backend/tools/historical_incident_search.py`
- `backend/tools/root_cause_analyzer.py`
- `backend/tools/investigation_planner.py`
- `backend/tools/counterfactual_analysis.py`

---

### Phase 6: LangGraph Agent

**Goal**: Coordinate tools in fixed pipeline after sensor log upload.

**Pipeline**:

```
START → Anomaly Detector → Historical Search → Root Cause Analyzer
      → Investigation Planner → Summary Generator → END
```

**State**:

```json
{
  "anomalies": [],
  "incidents": [],
  "root_causes": [],
  "recommendations": [],
  "summary": ""
}
```

**Tasks**:
- [ ] Define LangGraph state schema
- [ ] Implement nodes (one per tool + summary generator)
- [ ] Wire edges in pipeline order
- [ ] Each node updates state; output feeds next node

**Acceptance Criteria**:
- Upload triggers full pipeline
- Final state populated: anomalies, incidents, root_causes, recommendations, summary

**Files to Create**:
- `backend/agents/` — LangGraph graph definition

---

### Phase 7: MCP Server

**Goal**: Expose tools as MCP after Phase 5 tools work.

**MCP tool list**:
- `anomaly_detector`
- `historical_search`
- `root_cause_analysis`
- `investigation_planner`
- `counterfactual_analysis`
- `summary_generator`

**Tasks**:
- [ ] MCP server wrapping each backend tool
- [ ] Verify external consumers can invoke tools (Claude, ChatGPT, Copilot, Internal Engineering Agent — per guide)

**Acceptance Criteria**:
- All six tools exposed with names matching guide

---

### Phase 8: OpenAI Integration

**Goal**: Enforce GPT vs deterministic tool boundaries.

**GPT-4o responsibilities**:
- Root cause analysis
- Investigation summary
- Engineering chat
- Recommendation generation

**GPT must NEVER**:
- Numerical calculations
- Anomaly detection
- Vector search

**Tasks**:
- [ ] Configure OpenAI GPT-4o and Embeddings clients
- [ ] Ensure RootCauseAnalyzer and summary/chat use GPT only where guide specifies
- [ ] Audit that anomaly detection and vector search stay in deterministic tools

**Acceptance Criteria**:
- No GPT code paths for calculation, anomaly detection, or vector search

---

### Phase 9: Frontend Dashboard

**Goal**: Six pages per guide.

| Page | Content |
|------|---------|
| 1 | Upload sensor logs |
| 2 | Investigation dashboard — risk level, anomaly count, historical match count, root cause ranking |
| 3 | Engineering timeline — Recharts: temperature, pressure, vibration, RPM; highlight anomalies |
| 4 | Sensor contribution ranking — bar chart (e.g. Temperature 41%, Vibration 33%, Pressure 18%, RPM 8%) |
| 5 | Historical incidents table — incident ID, similarity, root cause, resolution |
| 6 | Investigation whiteboard — React Flow reasoning graph |

**Whiteboard example flow**:

```
Failure → Temperature Spike → Cooling Degradation → Incident #31 → Recommended Action
```

**Tasks**:
- [ ] Page 1: upload (integrate `POST /api/upload`)
- [ ] Page 2: dashboard widgets
- [ ] Page 3: timeline with Recharts
- [ ] Page 4: contribution bar chart
- [ ] Page 5: incidents table
- [ ] Page 6: React Flow whiteboard

**Acceptance Criteria**:
- All six pages render data from investigation pipeline
- Timeline highlights anomaly points
- Whiteboard shows reasoning graph structure from guide example

**Files to Create**:
- `frontend/src/pages/` (or equivalent per page)

---

### Phase 10: Report Generation

**Goal**: PDF Engineering Investigation Report.

**Endpoint**: `/api/report`

**Process**:
1. Collect: anomalies, incidents, root causes, recommendations
2. Generate PDF

**Tasks**:
- [ ] Implement `/api/report` in FastAPI
- [ ] Aggregate investigation state
- [ ] PDF generation

**Acceptance Criteria**:
- Report includes all four collected artifact types
- Output is Engineering Investigation Report (PDF)

**Files to Create/Modify**:
- `backend/api/` — report route
- `backend/services/` — report service

---

### Phase 11: Engineering Chat

**Goal**: Copilot Q&A over current investigation.

**Example questions**:
- What caused this failure?
- Which incident is most similar?
- What action should be taken?

**Process**:
1. LangGraph retrieves: current investigation state, historical incidents, relevant metrics
2. GPT generates answer

**Tasks**:
- [ ] Chat UI in frontend
- [ ] Backend: retrieve investigation state + incidents + metrics
- [ ] GPT-4o response generation

**Acceptance Criteria**:
- User can ask guide example questions and receive answers grounded in current investigation

---

### Phase 12: What-If Analysis

**Goal**: Counterfactual risk comparison UI.

**Example**: What if vibration decreases by 20%?

**Process**:
1. Counterfactual tool
2. Historical comparison
3. Statistical estimation

**Output example**: Failure risk reduced by 37%

**Display**: Before risk, After risk

**Tasks**:
- [ ] Wire CounterfactualAnalysis tool
- [ ] Historical comparison and statistical estimation
- [ ] Frontend: before/after risk display

**Acceptance Criteria**:
- What-if query produces risk reduction estimate
- UI shows before and after risk

---

## AVL Interview Demonstration Flow

Use this checklist for end-to-end demo validation:

- [ ] 1. Upload sensor log
- [ ] 2. Detect anomalies
- [ ] 3. Search historical incidents
- [ ] 4. Generate root causes
- [ ] 5. Produce investigation plan
- [ ] 6. Visualize failure timeline
- [ ] 7. Show reasoning graph
- [ ] 8. Run what-if analysis
- [ ] 9. Generate final report
- [ ] 10. Ask follow-up questions through Engineering Copilot

---

## File Structure (Target)

```
technical_investigation_copilot/
├── frontend/
│   └── src/                    # Pages 1–6, chat, what-if
├── backend/
│   ├── api/                    # /api/upload, /api/report
│   ├── agents/                 # LangGraph graph
│   ├── tools/                  # 5 tools + summary
│   ├── models/
│   ├── services/               # ingestion, report, chat
│   ├── vectorstore/            # PGVector
│   ├── database/
│   └── datasets/               # sample CSV, incidents
├── specs/
│   ├── SPEC.md
│   ├── API_CONTRACTS.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── SPEC_README.md
└── docker-compose.yml          # Phase 1
```

---

## Phase Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Structure)
        └── Phase 3 (Data ingestion)
              └── Phase 4 (Vector DB)
                    └── Phase 5 (Tools)
                          ├── Phase 6 (LangGraph)
                          │     ├── Phase 9 (Frontend) — partial after state available
                          │     ├── Phase 10 (Report)
                          │     ├── Phase 11 (Chat)
                          │     └── Phase 12 (What-if)
                          └── Phase 7 (MCP) — after tools work
                                Phase 8 (OpenAI boundaries) — parallel with 5–6
```

---

## Success Criteria (Guide-Derived)

- CSV upload → PostgreSQL ingestion with `status` / `records` response
- Historical incidents searchable via PGVector similarity
- All five tools + summary generator produce guide-defined outputs
- LangGraph pipeline runs: Anomaly → Historical → Root Cause → Planner → Summary
- MCP exposes six named tools
- GPT never performs numerical calculation, anomaly detection, or vector search
- Six frontend pages + report PDF + engineering chat + what-if before/after risk
- AVL demonstration flow completable end-to-end

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-01  
**Status**: Ready for implementation (content from Technical Implementation Guide only)
