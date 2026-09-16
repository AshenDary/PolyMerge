# PolyMerge

PolyMerge is a research-oriented platform for polypill candidate discovery. It helps researchers and pharmacists explore biomedical relationships, candidate drug sets, and explainability traces for selected disease clusters, but it is not an autonomous prescribing system.

## Current implementation status

### Implemented in this repository

- Fastify backend with research-oriented APIs:
  - `GET /api/diseases`
  - `GET /api/drugs/:id`
  - `GET /api/drugs/:id/interactions`
  - `POST /api/combinations/search`
  - `GET /api/combinations/:id`
  - `GET /api/combinations/:id/explain`
  - `GET /api/history`
- Deterministic hard safety/contraindication checks that run independently from ML scores.
- FastAPI ML engine scaffold with modular placeholder services for:
  - knowledge graph access
  - candidate generation
  - safety filtering
  - set-cover optimization
  - candidate ranking
- Static frontend dashboard for disease selection, workflow status, candidate summary, and explainability views.
- Clear evidence/provenance and model metadata fields in API responses.
- Validated Fastify-to-FastAPI requests with bounded timeouts and explicit demo fallback status.

### Mocked / planned

- Real Neo4j-backed disease and drug retrieval is not yet implemented end-to-end.
- No real GNN/DDI prediction model is currently integrated.
- No real synergy prediction model is currently integrated.
- No real Cytoscape graph visualization is implemented yet; the UI currently uses a simple explainability panel.
- No real TWOSIDES or DrugBank integration is implemented yet.
- No clinical validation or dosage recommendation logic is implemented.

## Revised architecture

```text
Frontend
  ↓
Fastify Backend
  ↓
FastAPI ML Engine
  ↓
Neo4j knowledge graph + demo ML services
  ↓
Candidate ranking / research explainability
```

MySQL remains the application/audit/query storage layer. Neo4j stores the biomedical graph. The biomedical graph is not duplicated into MySQL.

## Repository structure

- `backend/`: Fastify + Prisma API, hard safety rules, query/history support.
- `ml_engine/`: FastAPI service plus service modules for graph, candidate generation, safety filtering, optimization, and ranking.
- `frontend/`: static research dashboard.
- `data/processed/`: filtered Hetionet fragment used for local development.
- `scripts/`: graph fragment generation helpers.
- `docker/`: MySQL init scripts.

## Quick start

```bash
# 1) Copy the environment template and start infrastructure
cp .env.example .env
docker-compose up -d

# 2) Backend
cd backend
npm install
npx prisma generate
npx prisma migrate dev --name init
npm run dev

# 3) ML engine (separate terminal)
cd ml_engine
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

Then open the frontend at http://localhost:3000/ and verify health endpoints:

- `curl http://localhost:3000/health`
- `curl http://localhost:8000/health`

## API overview

### Current research-facing endpoints

- `GET /api/diseases`: returns the known disease catalog.
- `GET /api/drugs/:id`: returns drug metadata and relevant graph relationships.
- `GET /api/drugs/:id/interactions`: returns interaction metadata where available.
- `POST /api/combinations/search`: returns demo research candidates and applies hard contraindication filtering.
- `GET /api/combinations/:id`: returns a stored combination result.
- `GET /api/combinations/:id/explain`: returns explainability metadata for each candidate.
- `GET /api/history`: returns prior query history stored in memory.

### Backend-to-ML response contract

`POST /api/combinations/search` validates disease input before forwarding a
request to FastAPI. The backend requires the ML response to include structured
`diseases`, `candidates`, and `metadata`, including both `dataStatus` and
`mlStatus`. Calls are bounded by `ML_SERVICE_TIMEOUT_MS`.

Graph-backed responses use `dataStatus: "real_graph"` and
`mlStatus: "not_applied"`; their interaction-risk and synergy fields remain
`null` because no predictive model is integrated. If the ML service is
unavailable, times out, or violates the response contract, the backend returns
an explicitly labeled demo fallback with `dataStatus: "demo"`,
`mlStatus: "demo_placeholder"`, and `metadata.fallback: true`.

## Terminology updates

The implementation intentionally uses research-oriented wording:

- “knowledge-graph treatment coverage” instead of “100% disease treatment”.
- “Predicted Interaction Risk” / “Model Risk Score” / “PolyMerge Safety Index” instead of a clinical safety claim.
- “Reference information” instead of dosage recommendations.
- “Evidence type” and “evidence source” are represented explicitly.
- Hard safety rules are separated from model predictions.

## Data and scientific reality

- Hetionet is used as the current knowledge graph fragment.
- Hetionet does not directly provide DDI labels.
- Current DDI/synergy values are demo placeholders unless real model data are integrated.
- DrugBank access and licensing must be described accurately; this repository does not claim full DrugBank integration.

## Definition of done for this phase

- Disease selection workflow is available.
- Neo4j disease/drug retrieval is prepared through the ML engine boundary.
- Hard safety rules remain enforced and cannot be bypassed by low model risk.
- Candidate generation and baseline set-cover-style ranking are available.
- Research-only UI and evidence/provenance metadata are present.
- Remaining ML and explainability work is explicitly marked as planned.
