# PolyMerge Team & Task Overview

## Current role split

| Role | Focus | Current status |
| --- | --- | --- |
| Backend engineer | Fastify API, Prisma, query/history support, safety layer | Implemented |
| ML engineer | FastAPI services, graph abstraction, candidate generation, baseline optimization | Partially implemented with demo data |
| Research/UI engineer | Research dashboard, explainability display, evidence presentation | Implemented in static frontend |

## Current working status

### Backend

- Research-oriented API surface now exists.
- Hard contraindication rules are preserved and exposed with structured reason payloads.
- Query history is stored in memory for the current runtime.

### ML engine

- Modular placeholder services exist for knowledge graph access, candidate generation, safety filtering, optimization, and ranking.
- The API currently returns clearly labeled demo data until real ML models are integrated.

### Frontend

- Static dashboard supports disease selection, workflow status, candidate summaries, and a simple explainability panel.
- The UI uses research-only messaging and explicitly labels demo data as such.

## Handoff expectations

- Any new model or dataset integration must be declared as real or demo in the API output.
- Any hard contraindication must remain traceable and must not be bypassed by model scores.
- All new artifacts should be documented as implemented, planned, or stretch-goal work.
