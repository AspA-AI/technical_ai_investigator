# API Contracts Specification

API endpoints defined in the Technical Implementation Guide.

## 1. Upload Sensor Logs

### 1.1 Upload CSV

**Endpoint**: `POST /api/upload`

**Phase**: 3 — Data ingestion

**Frontend**: React Upload Component

**Request**:
- Content-Type: `multipart/form-data`
- Body: CSV file (e.g. `engine_001.csv`)

**Backend process** (not returned in response; for implementers):
1. FastAPI receives file
2. Store raw file
3. Parse using Pandas
4. Validate columns
5. Store processed records into PostgreSQL

**Response** (200 OK):

```json
{
  "status": "success",
  "records": 1200,
  "upload_id": "a1b2c3d4e5f67890"
}
```

`upload_id` is returned for downstream investigation runs (Phase 6).

**Example**:
- Input file: `engine_001.csv`
- Output: `records` reflects count of processed records stored in PostgreSQL

---

## 2. Report Generation

### 2.1 Generate Investigation Report

**Endpoint**: `/api/report`

**Phase**: 10 — Report generation

**Process**:
1. Collect:
   - Anomalies
   - Incidents
   - GitHub matches
   - Root causes
   - Recommendations
2. Generate markdown technical report
3. Export as PDF, PPTX, DOCX, or raw markdown depending on request format

**Formats supported by the current backend**:
- `pdf`
- `pptx`
- `md`
- `docx`

### 2.2 Preview Technical Report

**Endpoint**: `GET /api/report/{investigation_id}/preview`

**Purpose**:
- Returns the markdown preview used by the report modal in the frontend

### 2.3 GitHub Issue Archival Webhook

**Endpoint**: `POST /api/github/webhooks/issues`

**Purpose**:
- Receives GitHub `issues` webhook payloads
- Archives closed issues into PostgreSQL + PGVector

### 2.4 GitHub Closed-Issue Polling Fallback

**Endpoint**: `POST /api/github/poll/closed-issues`

**Purpose**:
- Fallback path for scanning closed issues when webhook delivery is unavailable

**Output**: Engineering Investigation Report artifacts and preview markdown

---

## 3. Tool Output Schemas (Reference)

These are produced by backend tools / LangGraph pipeline, not standalone REST endpoints in the guide. Documented here for frontend and integration contracts.

### 3.1 AnomalyDetector Output

```json
{
  "temperature_spike": true,
  "pressure_drop": true,
  "risk": "high"
}
```

### 3.2 HistoricalIncidentSearch Output

```json
[
  {
    "incident_id": 31,
    "similarity": 0.91
  }
]
```

### 3.3 RootCauseAnalyzer Output

```json
[
  {
    "cause": "bearing wear",
    "confidence": 82
  }
]
```

### 3.4 InvestigationPlanner Output

```json
[
  "Inspect bearing assembly",
  "Verify cooling pressure",
  "Check lubrication"
]
```

### 3.5 CounterfactualAnalysis

**Input**:

```json
{
  "temperature_change": -15
}
```

**Output**:

```json
{
  "risk_reduction": 68
}
```

### 3.6 LangGraph Investigation State

```json
{
  "anomalies": [],
  "incidents": [],
  "root_causes": [],
  "recommendations": [],
  "summary": ""
}
```

---

## 4. Historical Incident Record (Vector Store)

**Example incident** (Phase 4):

```json
{
  "incident_id": 31,
  "failure": "engine overheating",
  "root_cause": "cooling degradation",
  "resolution": "replace cooling module"
}
```

---

## 5. Engineering Chat (Phase 11)

The guide defines behavior only (no HTTP path specified).

**Example user questions**:
- What caused this failure?
- Which incident is most similar?
- What action should be taken?

**Process**:
- LangGraph retrieves: current investigation state, historical incidents, relevant metrics
- GPT generates answer

---

## 6. What-If Analysis (Phase 12)

The guide defines behavior only (no HTTP path specified).

**Example user question**: What if vibration decreases by 20%?

**Process**:
- Counterfactual tool
- Historical comparison
- Statistical estimation

**Output example**: Failure risk reduced by 37%

**Display**: Before risk, After risk

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-01  
**Status**: Living implementation reference
