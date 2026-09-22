# PolyMerge

PolyMerge is a biomedical research decision-support platform for exploring
multi-drug candidate combinations. It combines biomedical knowledge-graph
evidence, traditional machine learning, deterministic safety rules,
multi-drug candidate generation, and combinatorial optimization. It is not an
autonomous prescribing system and does not provide medical advice, dosage
recommendations, clinical safety guarantees, or final formulation decisions.

## Current Architecture

```text
Frontend
  ↓
Fastify Backend
  ↓
FastAPI ML/Graph Service
  ↓
Neo4j / Hetionet Knowledge Graph
```

MySQL and Prisma are used for application/system data foundations. Neo4j remains the source of truth for biomedical graph entities and relationships.

## Current Capabilities

- Fastify backend with research-oriented APIs:
  - `GET /health`
  - `GET /health/dependencies`
  - `GET /api/diseases`
  - `GET /api/drugs/:id`
  - `GET /api/drugs/:id/interactions`
  - `POST /api/combinations/search`
  - `GET /api/combinations/:id`
  - `GET /api/combinations/:id/explain`
  - `GET /api/history`
- FastAPI ML/Graph service:
  - `GET /health`
  - `GET /api/diseases`
  - `GET /api/drugs/{drug_id}`
  - `POST /predict/combination`
- Real Neo4j integration through environment-configured connection settings.
- Hetionet-derived graph data loaded into Neo4j.
- Graph-backed disease retrieval from Neo4j disease nodes.
- Graph-backed disease to compound retrieval using `CtD`.
- Compound-gene evidence using `CbG`, `CuG`, and `CdG`.
- Compound side-effect evidence using `CcSE`.
- Evidence/provenance fields such as `source`, `graphVersion`, `relationship`, `metaedge`, `targetId`, and `evidenceType`.
- Graph-backed candidate generation from represented knowledge-graph relationships.
- Disease x drug coverage matrix derived from represented `CtD` edges for the requested target diseases.
- Candidate-set generation from graph-derived single-drug candidates, including multi-drug sets up to the configured maximum drug count.
- Deterministic hard safety filtering that runs independently from ML predictions.
- Greedy set-cover baseline that consumes graph-derived candidate-set coverage.
- Candidate comparison structures that show each drug's contribution to candidate-set disease coverage.
- Backend to ML/Graph service integration with request validation and dependency health checks.
- Static frontend disease-selection workflow that loads diseases from the backend and sends stable disease IDs.

## Current ML Status

No predictive ML model is applied in current graph-backed candidate responses.

- Graph-backed responses use `dataStatus: "real_graph"`.
- Predictive model status is `mlStatus: "not_applied"`.
- `interactionRisk` and `synergyScore` are `null`/not applied for real graph-backed candidates.
- The final academic ML solution is planned as traditional supervised ML, not
  neural networks, deep learning, graph neural networks, transformers, or
  large language models, pretrained foundation models, or AutoML-generated
  solutions.
- The planned comparison algorithms are Logistic Regression, Random Forest, and
  Gradient Boosting.
- The preferred academic deployment target is Streamlit unless another
  framework is instructor-approved.
- Neo4j remains the biomedical evidence source for graph retrieval, provenance,
  coverage, and feature engineering.

If the ML/Graph service is unavailable or violates the response contract, the backend returns an explicitly labeled fallback:

- `dataStatus: "demo"`
- `mlStatus: "demo"`
- `upstreamStatus: "fallback"`
- no graph-backed candidates are returned from that fallback path

Fallback responses must not be interpreted as real graph evidence or real ML predictions.

## Current Limitations

- Candidate-set generation is a deterministic graph-derived foundation for Sprint 2, not a final production optimization system.
- The optimizer is a greedy set-cover baseline over candidate sets, not a production-grade optimization system.
- `/api/drugs/:id` and `/api/drugs/:id/interactions` still provide reference/demo backend responses and are not the primary graph-backed candidate-search flow.
- Explainability is limited and does not yet provide advanced graph visualization or model explanation.
- Hetionet `CrC` means compound resemblance and is not a DDI label.
- Traditional drug-pair interaction classification requires a legitimate
  supervised DDI dataset and a documented target variable before training.
- Absence of a known DDI label must not be interpreted as proof that a drug pair
  is safe.
- Clinical recommendations, dosage decisions, and autonomous prescribing are outside project scope.

## Repository Structure

- `backend/`: Fastify API, request validation, fallback handling, safety-rule integration.
- `ml_engine/`: FastAPI ML/Graph service, Neo4j graph service, candidate generation, safety filtering, greedy set-cover baseline.
- `frontend/`: static research dashboard.
- `data/processed/`: filtered Hetionet fragment used for local development.
- `docs/`: graph schema and API documentation.
- `scripts/`: graph fragment generation/loading and repository management helpers.
- `docker/`: MySQL init scripts.
- `Sprints/`: sprint planning notes.

## Local Setup

Use:

- Node.js `>=20`
- Python `>=3.9`
- Docker / Docker Compose

Copy the environment template:

```bash
cp .env.example .env
```

The `.env` file is ignored by Git and must not be committed.

Start infrastructure:

```bash
docker compose up -d
```

Expected local services:

- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `bolt://localhost:7687`
- MySQL: `localhost:3306`

Backend:

```bash
cd backend
npm install
npx prisma generate
npx prisma migrate dev
npm run dev
```

ML/Graph service:

```bash
cd ml_engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Verification:

```bash
curl http://localhost:3000/health
curl http://localhost:3000/health/dependencies
curl http://localhost:3000/api/diseases
curl http://localhost:8000/health
curl http://localhost:8000/api/diseases
```

Example graph-backed candidate request:

```bash
curl -X POST http://localhost:3000/api/combinations/search \
  -H "Content-Type: application/json" \
  -d '{"diseases":["Disease::DOID:10763","Disease::DOID:9352"]}'
```

## Tests

Backend:

```bash
cd backend
npm test
```

ML/Graph service:

```bash
cd ml_engine
source .venv/bin/activate
python -m pytest -q
```

## API Overview

See `docs/api.md` for the current API contract.

## Data and Scientific Boundaries

- Hetionet is the current biomedical graph source.
- Hetionet does not directly provide DDI labels.
- `CrC` is compound resemblance, not interaction risk.
- Graph coverage is knowledge-graph treatment coverage, not clinical efficacy.
- Safety rules are deterministic guardrails, not a clinical safety guarantee.
- Future traditional ML predictions must be clearly separated from known graph
  evidence and deterministic rule outcomes.
