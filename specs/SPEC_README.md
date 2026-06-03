# Engineering Failure Investigation Copilot - Specification Documents

## Overview

This directory contains the specification for the Engineering Failure Investigation Copilot platform. The specification is organized into multiple documents covering different aspects of the system, derived from the Technical Implementation Guide.

## Specification Documents

### 1. [SPEC.md](./SPEC.md) - Main Specification

**Purpose**: Comprehensive overview of the platform

**Contents**:
- System overview and purpose
- Key features and implementation phases
- High-level architecture
- Technology stack
- Project structure
- Tool specifications (5 tools + summary generator)
- LangGraph agent workflow and state
- Data models (incidents, investigation state)
- MCP server exposure
- OpenAI integration boundaries
- Frontend dashboard pages
- API endpoints summary
- AVL interview demonstration flow

**Use this for**: Understanding the overall system, requirements, and architecture

---

### 2. [API_CONTRACTS.md](./API_CONTRACTS.md) - API Contracts

**Purpose**: API endpoint specifications defined in the Technical Implementation Guide

**Contents**:
- Upload sensor logs (`POST /api/upload`)
- Report generation (`/api/report`)
- Request/response schemas from the guide
- Error response format (aligned with platform patterns)

**Use this for**: API integration, frontend development, testing

---

### 3. [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Implementation Plan

**Purpose**: Step-by-step implementation guide aligned with guide phases 1–12

**Contents**:
- Phase-by-phase task breakdown
- Dependencies between phases
- Acceptance criteria per phase
- Target file structure
- AVL interview demonstration flow checklist

**Use this for**: Project planning, task assignment, progress tracking

---

## Quick Start Guide

### For Project Managers

1. Read [SPEC.md](./SPEC.md) for system overview
2. Review [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for phase order (1–12)
3. Use the plan to assign tasks and track progress

### For Developers

1. Start with [SPEC.md](./SPEC.md) for context
2. Follow [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for implementation order
3. Reference [API_CONTRACTS.md](./API_CONTRACTS.md) when building endpoints

### For Frontend Developers

1. Read [SPEC.md](./SPEC.md) §9 (Frontend Dashboard)
2. Use [API_CONTRACTS.md](./API_CONTRACTS.md) for upload and report integration
3. Implement pages 1–6 as defined in the guide

### For QA / Demonstration (AVL Interview)

1. Follow [SPEC.md](./SPEC.md) §12 (AVL Interview Demonstration Flow)
2. Validate each tool output against schemas in [SPEC.md](./SPEC.md) §5
3. Confirm LangGraph pipeline order in [SPEC.md](./SPEC.md) §6

## System Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + TypeScript)             │
│  Upload │ Dashboard │ Timeline │ Ranking │ Incidents │      │
│  Whiteboard (React Flow) │ Engineering Chat │ What-If       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP/REST (Axios)
                     │
┌────────────────────▼────────────────────────────────────────┐
│              FastAPI Backend                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        LangGraph Investigation Agent                  │  │
│  │  Anomaly → Historical → Root Cause → Planner →       │  │
│  │  Summary                                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Anomaly  │ │Historical│ │Root Cause│ │Investigation│    │
│  │ Detector │ │  Search  │ │ Analyzer │ │  Planner   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐                                  │
│  │Counter-  │ │ Summary  │                                  │
│  │factual   │ │ Generator│                                  │
│  └──────────┘ └──────────┘                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌────▼────┐ ┌───▼────┐
    │PostgreSQL│ │PGVector │ │ OpenAI │
    │ + Pandas │ │Embeddings│ │ GPT-4o │
    └─────────┘ └─────────┘ └────────┘
```

## Technology Stack (from Guide)

| Layer | Technologies |
|-------|----------------|
| Frontend | React, TypeScript, TailwindCSS, React Flow, Recharts, Axios |
| Backend | Python, FastAPI, PostgreSQL, PGVector, Pandas, NumPy, Scikit-learn |
| AI | OpenAI GPT-4o, OpenAI Embeddings, LangGraph |
| Development | Docker, Docker Compose |

## Implementation Phases (Guide)

| Phase | Topic |
|-------|--------|
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

## Document Status

| Document | Version | Status | Source |
|----------|---------|--------|--------|
| SPEC.md | 1.0 | Ready for implementation | Technical Implementation Guide |
| API_CONTRACTS.md | 1.0 | Ready for implementation | Technical Implementation Guide |
| IMPLEMENTATION_PLAN.md | 1.0 | Ready for implementation | Technical Implementation Guide |

---

**Specification Version**: 1.0  
**Created**: 2026-06-01  
**Status**: Ready for Implementation
