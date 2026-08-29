# PolyMerge Implementation Roadmap

8-week build across 3 members (see `SKILLS.md` for role definitions). Each sprint lists per-member tasks, a concrete deliverable, and a Definition of Done (DoD) so "done" isn't ambiguous.

## Sprint 0 — Environment Bootstrap (Days 1-3, whole team)

**Goal:** everyone can run the full stack locally before any feature work starts.

- All members: `cp .env.example .env`, `docker-compose up -d`, `npm install` (backend), `pip install -r requirements.txt` (ml_engine).
- Member B: run `npx prisma migrate dev --name init` against the MySQL container; confirm `User` and `QueryLog` tables exist.
- Member A: confirm the Neo4j browser is reachable at `http://localhost:7474` and log in with `neo4j` / `password`.

**DoD:** `curl localhost:3000/health` and `curl localhost:8000/health` both return `{"status":"ok"}`; `docker ps` shows both `neo4j` and `mysql` containers healthy; `npx prisma studio` shows the two tables.

## Sprint 1 — The Skeleton (Weeks 1-2)

**Goal:** end-to-end connectivity without any AI in the loop.

**Member A (ML Data Engineer):**
- Pull a scoped fragment of Hetionet covering one target disease cluster (hypertension, type 2 diabetes, hyperlipidemia) and load it into the local Neo4j instance.
- Write and test 3-5 Cypher queries (e.g., "drugs that treat disease X", "known DDIs for drug Y").
- Deliverable: `ml_engine/app/utils/neo4j_client.py` (connection helper) + one example query script.
- DoD: a query against the loaded fragment returns real drug nodes for at least one disease in the target cluster.

**Member B (ML Backend Engineer):**
- Extend the existing `/api/combinations/search` route's request/response schema; back it with a hardcoded mock drug-set JSON (not the ML engine yet).
- Keep the hard-coded contraindication check (`backend/src/rules/contraindications.js`) wired in and covered by tests.
- Deliverable: an `.http` file or Postman collection demonstrating all routes.
- DoD: all routes return `200` with mock data; `node --test` passes, including the contraindication unit tests.

**Member C (UI Developer / Clinical Validator):**
- Build a minimal frontend (Streamlit single page, or a React skeleton) that lets a user pick disease(s), calls the backend, and displays the mock result as a table.
- Deliverable: `frontend/app.py` or `frontend/src/App.jsx`.
- DoD: selecting diseases and submitting shows the mock combination result on screen.

**Sprint DoD:** disease selection in the UI → Fastify API → mock drug set → displayed in the UI, all running via `docker-compose` + `npm run dev` + `uvicorn`.

## Sprint 2 — The Baseline (Weeks 3-4)

**Goal:** replace mock data with real, non-deep-learning predictions.

**Member A:**
- Generate TransE knowledge-graph embeddings over the Neo4j fragment (e.g., via PyKEEN) and export drug-disease / drug-drug similarity scores.
- Deliverable: `ml_engine/app/services/kg_embeddings.py`, `scripts/train_transe.py`.
- DoD: given a disease ID, the script returns the top-K candidate drugs ranked by embedding similarity.

**Member B:**
- Implement greedy set-cover over Member A's scored pairs; wire it into `POST /predict/combination` in `ml_engine/main.py`.
- Point `backend/src/server.js`'s `/api/combinations/search` at the real ML engine (`ML_SERVICE_URL`) instead of mock data.
- Deliverable: `ml_engine/app/services/combination_search.py`.
- DoD: for a 3-disease cluster, the API returns a real (non-mocked) minimal drug set in under 2 seconds.

**Member C:**
- Replace the hardcoded disease list in the UI with a real list pulled from Neo4j via a new `GET /api/diseases` backend endpoint.
- Display the returned combination with a per-drug confidence score.
- DoD: full real-data path works end to end (UI → backend → ML engine → Neo4j-backed embeddings → results shown).

## Sprint 3 — The GNN Brain (Weeks 5-6)

**Goal:** replace the TransE baseline with a trained GNN for DDI + synergy prediction.

**Member A:**
- Build PyTorch Geometric `Data`/`HeteroData` objects from the KG, with RDKit-derived node features for drugs.
- Train a GCN/GAT (Decagon-style) for multi-label DDI classification using DrugBank/TWOSIDES-derived labels; hold out a test split.
- Deliverable: `ml_engine/app/models/ddi_gnn.py`, a training script, a checkpoint (`.pt`, gitignored), and an eval report (AUROC/F1).
- DoD: the trained GNN beats the Sprint 2 TransE baseline on at least one held-out metric — document the comparison in the eval report.

**Member B:**
- Swap the scoring backend behind `combination_search.py` to call the GNN instead of TransE scores, behind a model-version parameter so models can be swapped without breaking the API contract.
- Add a caching layer (in-memory or Redis) for repeated disease-cluster queries to offset the heavier GNN inference cost.
- DoD: p95 latency for `/api/combinations/search` stays under an agreed threshold (e.g., 3s) with the GNN in the loop.

**Member C:**
- Cross-reference GNN outputs against the Polycap (aspirin + statin + antihypertensives) and PolyIran published FDC trials for the target disease cluster.
- Deliverable: `docs/validation-report.md`.
- DoD: written comparison identifying at least two concordances with published trial formulations, plus hypotheses for any discordances.

## Sprint 4 — Polish & Explainability (Weeks 7-8)

**Goal:** presentation-ready system with a visible reasoning trace for every suggestion.

**Member A:**
- Generate GNNExplainer subgraphs / attention weights per prediction; export as JSON (contributing nodes/edges + importance scores).
- Deliverable: `ml_engine/app/services/explainability.py`.
- DoD: an explainability payload for any DDI prediction generates in under 5 seconds.

**Member B:**
- Expose explainability data via `GET /api/combinations/:id/explain`.
- Ensure API responses clearly separate **rule-based blocks** (from `contraindications.js`) from **model-predicted** risk scores, so the UI can visually distinguish "hard-coded safety override" from "GNN opinion."
- DoD: response schema makes that distinction explicit and is covered by a test.

**Member C:**
- Visualize the interaction graph and explainability weights in the frontend (Cytoscape.js), highlighting the edges that most influenced a prediction.
- Add a persistent disclaimer banner reflecting the project's non-clinical, decision-support-only scope (see `CONTEXT.md`).
- DoD: full demo walkthrough works — select diseases → see recommended drug set → click a drug pair → see the graph highlighting why it was flagged safe/risky, with rule-based blocks visually distinct from model scores.

## Stretch Goal (Post-Sprint 4) — Release Scheduling

Only pursue after Sprint 4's DoD is fully met. Covers the pH-layer / pellet scheduling sub-problem (rule-based + PK-informed classification: which layer of a multiparticulate pill a given drug's pellet should sit in, based on absorption site).

## Cross-Sprint Definition of Done (applies every sprint)

- All new/changed backend logic has a corresponding test in `backend/tests/`; all new ML engine logic has a test in `ml_engine/tests/`.
- Any new environment variable is added to `.env.example` with a comment.
- No secrets, API keys, or trained model checkpoints are committed to git.
- `README.md`'s Quick Start still works from a clean clone after the sprint's changes.

## Risks & Mitigations

- **Data coverage gaps** (DrugBank/Hetionet are incomplete) → mitigate by scoping tightly to one disease cluster for the whole roadmap rather than trying to generalize early.
- **GNN training time** on typical dev hardware → mitigate with subgraph sampling and a reduced-epoch "dev mode" baseline; use a GPU instance for the real training run if available.
- **Model swaps breaking the API contract** → mitigated structurally by the Sprint 1 decision to fully decouple `ml_engine` from `backend` behind a stable HTTP/JSON contract, established before any model logic exists.
