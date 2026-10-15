# PolyMerge

PolyMerge is a research decision-support platform that combines biomedical
knowledge-graph evidence, traditional supervised ML, deterministic hard safety
rules, multi-drug candidate generation, optimization, and explainability. It is
not an autonomous prescribing system and does not provide medical advice,
dosage recommendations, clinical safety guarantees, or final formulation
decisions.

## Current Architecture

```text
Streamlit Frontend
  ↓ HTTP API
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
  - `POST /api/candidate-sets/search`
  - `POST /api/combinations/search`
  - `GET /api/combinations/:id`
  - `GET /api/combinations/:id/explain`
  - `GET /api/history`
- FastAPI ML/Graph service:
  - `GET /health`
  - `GET /health/model`
  - `GET /api/diseases`
  - `GET /api/drugs/{drug_id}`
  - `POST /predict/candidate-sets`
  - `POST /predict/ddi-severity`
  - `POST /predict/combination`
- Real Neo4j integration through environment-configured connection settings.
- Hetionet-derived graph data loaded into Neo4j.
- Graph-backed disease retrieval from Neo4j disease nodes.
- Graph-backed disease to compound retrieval using `CtD`.
- Compound-gene evidence using `CbG`, `CuG`, and `CdG`.
- Compound side-effect evidence using `CcSE`.
- Structured `graphEvidence.paths` with stable path IDs, source and graph
  version, represented relationship semantics, target entities, and provenance.
- Graph-backed candidate generation from represented knowledge-graph relationships.
- Disease x drug coverage matrix derived from represented `CtD` edges for the requested target diseases.
- Candidate-set generation from graph-derived single-drug candidates, including multi-drug sets up to the configured maximum drug count.
- Deterministic hard safety filtering that runs independently from ML predictions.
- Greedy set-cover baseline that consumes graph-derived candidate-set coverage.
- Candidate comparison structures that show each drug's contribution to candidate-set disease coverage.
- Backend to ML/Graph service integration with request validation and dependency health checks.
- Static frontend with Home, Simulation, Explainability, and Model Analysis
  views. The Simulation view keeps disease selection, workflow visualization,
  candidate results, candidate-level graph evidence, deterministic rules, and
  ML prediction state in one demo flow.
- Frozen Random Forest evaluation metadata, checksums, environment versions,
  and a reproducible preprocessing/classifier pipeline contract.

## Current ML Status

The frozen Sprint 5 Random Forest is served through the DDI-severity endpoints
(`POST /predict/ddi-severity` in the ML service and
`POST /api/ddi-severity/predict` in the backend) when its reviewed joblib
artifact is installed and passes checksum/schema verification. The Sprint 5
integration branch also applies the same model to candidate-set drug pairs when
the runtime bridge can deterministically build the frozen 55-feature row from
the reviewed DDInter-Hetionet and PubChem mappings. If a pair cannot be bridged
or the model is unavailable, candidate ML state remains explicitly
`mlStatus: "not_applied"` with no fallback severity.

Feature enrichment uses cached, conservatively accepted PubChem structures,
traditional RDKit descriptors, and symmetric Hetionet graph summaries. Missing
coverage remains distinct from known zero relationships.

The finalized Sprint 3 dataset contains 130,422 canonical labeled drug pairs
and 55 features. PubChem enrichment uses the official PUG REST API, with 1,315
validated mappings and 67.818% structure coverage across distinct drugs.

| Evaluation | Result |
| --- | ---: |
| Sprint 4 CV Macro F1 | 0.506086 +/- 0.005695 |
| Sprint 5 final test Macro F1 | 0.524630 |
| Final test balanced accuracy | 0.475467 |
| Final test Macro AUROC | 0.798793 |
| Final test Macro AUPRC | 0.632468 |

- Graph-backed responses use `dataStatus: "real_graph"`.
- Predictive model status is `mlStatus: "applied"` only after real pair-level
  inference succeeds; otherwise it remains `mlStatus: "not_applied"`.
- `interactionRisk` and `synergyScore` are `null`/not applied for real graph-backed candidates.
- The supervised target is curated DDInter severity: Major, Moderate, or Minor.
- Unknown severity is audited but excluded; no synthetic negatives or
  no-interaction class are created.
- Sprint 4 compared `LogisticRegression`, `RandomForestClassifier`, and
  `HistGradientBoostingClassifier` under one five-fold CV contract and selected
  `RandomForestClassifier` by mean Macro F1.
- Sprint 5 completed the one-time final evaluation on the previously untouched
  test split and froze the selected pipeline; serving does not rerun evaluation.
- The primary test split was used exactly once for final evaluation and must not
  be reused for tuning, feature selection, threshold adjustment, or model
  switching.
- The final model version is
  `RandomForestClassifier-sprint5-v1-65e9834666ad19c5`.
- Reproducibility metadata and the final report are tracked in Git. The
  251,404,304-byte (approximately 240 MB) joblib binary is intentionally ignored
  because of its size and is not hosted in this repository.
- The academic ML solution is restricted to traditional supervised learning;
  neural networks, deep learning, GNNs, transformers, foundation models, and
  AutoML-generated models are out of scope.
- Neo4j remains the evidence source for graph retrieval, provenance, coverage,
  and graph-derived feature engineering.
- Streamlit is the preferred academic deployment unless another framework is
  instructor-approved.

## Streamlit frontend

The Streamlit app hosts the complete existing frontend, including its design,
sidebar navigation, Home, Simulation, candidate results, Explainability, and
Model Analysis. Model Analysis reads preserved Sprint 4/Sprint 5 results and
tracked Sprint 3 EDA figures; it does not regenerate metrics.

Install its dependencies and run it from the repository root:

```bash
python -m pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```

LOCAL STREAMLIT DEMO is supported when the Fastify frontend is running locally.
The embedded frontend uses `http://127.0.0.1:3000` by default. Set
`POLYMERGE_FRONTEND_URL` to override it, or set `POLYMERGE_API_URL` to provide
the backend origin when both are served from the same host.

REMOTE STREAMLIT requires `POLYMERGE_FRONTEND_URL` to point to a public HTTPS
frontend. A remote Streamlit deployment cannot automatically reach a user's
local `127.0.0.1` Fastify process.

## Frontend demo flow

Open the Fastify frontend at `http://127.0.0.1:3000`.

1. Start on Home and choose **Start Simulation**.
2. Search for `hypertension` and select `Disease::DOID:10763`.
3. Choose **Analyze Candidates**. The Analyze step shows elapsed time, not
   invented stage progress. Completion opens Review Candidates.
4. Read the compact summary of selected diseases, returned candidate sets, and
   candidates with predictions. These counts describe the full response.
5. Review the first five candidates in backend rank order. **Show next 5** pages
   through the response without fetching again. Single-drug predictions remain
   **Not applicable**. Choose **Understand this candidate** to enter step 4.
6. Simple View shows a short grounded explanation and treatment connections.
   Expand research details for the full evidence. **Researcher View** exposes
   IDs, provenance, technical pipeline and optional all-results display using
   the same response; switching modes never reruns analysis.
7. Ranking uses configured rule status, graph coverage, fewer drugs, then ID.
   Backend validation can add rejections without reranking. ML remains separate.
   Rule applicability to canonical graph drug IDs is still an audit blocker;
   "No configured rule triggered" is not a clinical safety assessment.
8. Choose **New Simulation** from Simulation or Explainability. It clears
   selection, search, results, explanations, and timers while keeping the catalog.
   Select hypertension and `type 2 diabetes mellitus` (`Disease::DOID:9352`),
   then run the two-disease analysis.
9. Inspect the transformation counts and select an ML-applied candidate. Its
   severity, graph evidence, and rule details update from the existing response.
10. Open Model Analysis and review EDA interpretations, preserved comparison
    metrics, final model results, and limitations.

**New Simulation** also works during a request: the browser request is aborted
and late responses/errors are ignored. This does not cancel server-side graph
work; a new analysis receives a clear busy response while the single worker
remains occupied. If catalog
loading failed, its retry control remains available after reset.

For local Streamlit validation, set `POLYMERGE_FRONTEND_URL` to the actual
Fastify origin, open Streamlit, and repeat navigation, analysis, and reset.
HTTP and script checks do not replace manual browser/iframe acceptance.

Demo sequence: Select Diseases → Analyze → Review Candidates → Understand Result.
Model Analysis retains the frozen metrics and EDA assets. Sprint 6 remains
pending manual presentation review. See [guided demo acceptance](docs/sprint6-guided-demo.md).

Local profiling reduced median single-disease latency from 20,147.848 ms to
925.607 ms and two-disease latency from 57,893.834 ms to 1,051.950 ms across
three sequential runs per case on the same dataset. Full canonical response
equivalence was checked excluding request IDs/timestamps. These are local
observations, not production guarantees. See the
[performance investigation](docs/audits/sprint6-performance-investigation.md).

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
- Structured graph evidence paths, deterministic rule results, and ML
  prediction presentation are wired into the candidate-set explainability flow.
- Hetionet `CrC` means compound resemblance and is not a DDI label.
- Candidate-set ML inference is available only for pairs that can be represented
  by the frozen Sprint 3 feature contract; unsupported pairs fail closed without
  a fabricated prediction.
- Major and Minor recall remains substantially lower than Moderate recall due
  to the observed class-imbalanced performance profile.
- Final model metrics are research classification results, not clinical
  validation or a safety guarantee.
- Absence of a DDInter label is not evidence that a drug pair is safe.
- Clinical recommendations, dosage decisions, and autonomous prescribing are outside project scope.

## Repository Structure

- `backend/`: Fastify API, request validation, fallback handling, safety-rule integration.
- `ml_engine/`: FastAPI ML/Graph service, Neo4j graph service, candidate generation, safety filtering, greedy set-cover baseline.
- `frontend/`: static research dashboard.
- `data/processed/`: filtered Hetionet fragment used for local development.
- `data/original/ddinter/`: tracked manifest; license-controlled raw CSVs are ignored.
- `data/processed/sprint3/`: DDInter severity dataset and train/test split.
- `data/interim/sprint3/`: profile, mapping, conflict, malformed, and Unknown audits.
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

The backend uses separate ML/Graph request budgets:

- `ML_CATALOG_TIMEOUT_MS` for disease catalog loading.
- `ML_HEALTH_TIMEOUT_MS` for dependency health checks.
- `ML_CANDIDATE_TIMEOUT_MS` for long-running candidate generation.

`ML_SERVICE_TIMEOUT_MS` remains the default for other ML requests and as a
fallback for the more specific values. Candidate generation should not use the
short catalog/health timeout because the two-disease local demo can take about
55-70 seconds and may take longer if another request is already using the local
ML/Graph worker.

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
curl -X POST http://localhost:3000/api/candidate-sets/search \
  -H "Content-Type: application/json" \
  -d '{"diseaseIds":["Disease::DOID:10763","Disease::DOID:9352"]}'
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

Sprint 3 data outputs:

```bash
python3 scripts/acquire_ddinter.py
python3 scripts/enrich_pubchem.py
python3 scripts/build_sprint3_dataset.py
python3 scripts/run_sprint3_eda.py
```

## API Overview

See `docs/api.md` for the current API contract.

## Data and Scientific Boundaries

- Hetionet is the current biomedical graph source.
- Hetionet does not directly provide DDI labels.
- `CrC` is compound resemblance, not interaction risk.
- DDInter is the severity-label source; Hetionet supplies optional graph
  features. The legacy CtD prototype is not the primary task.
- Absence from DDInter is not evidence of safety.
- Graph coverage is knowledge-graph treatment coverage, not clinical efficacy.
- Safety rules are deterministic guardrails, not a clinical safety guarantee.
- Traditional ML predictions, once actively served, must remain clearly
  separated from graph evidence and deterministic rule outcomes.
