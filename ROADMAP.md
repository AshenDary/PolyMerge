# PolyMerge Roadmap

## Sprint 1 — Foundation & Knowledge Graph

### Status: Implemented / Ready For Review

- Reproducible local infrastructure using Docker Compose for Neo4j and MySQL.
- Fastify backend with health, disease catalog, candidate search, history, and explainability endpoints.
- FastAPI ML/Graph service with health, disease catalog, drug metadata, and candidate prediction endpoints.
- Real Neo4j connection using environment variables.
- Hetionet-derived graph schema documented in `docs/knowledge-graph-schema.md`.
- Graph-backed disease retrieval from Neo4j.
- Graph-backed disease to compound retrieval using `CtD`.
- Compound-gene evidence using `CbG`, `CuG`, and `CdG`.
- Compound side-effect evidence using `CcSE`.
- Evidence/provenance fields preserved in graph-derived candidate output.
- Backend `/api/diseases` uses the ML/Graph service rather than a hard-coded disease catalog.
- Backend validates selected diseases against the graph-backed catalog before candidate search.
- Candidate generation returns graph-derived single-compound candidates with stable IDs, treatment evidence, and provenance.
- `dataStatus` and `mlStatus` distinguish real graph data from future ML prediction.
- Deterministic hard safety rules remain independent of model outputs.
- Greedy set-cover baseline consumes graph-derived coverage.
- Backend and ML test suites cover Sprint 1 graph, API, validation, fallback, and optimization behavior.

### Sprint 1 Known Limitations

- Sprint 1 candidate generation produced the single-compound graph foundation consumed by later candidate-set generation.
- Greedy set-cover is a baseline, not the final optimization system.
- `/api/drugs/:id` and `/api/drugs/:id/interactions` remain reference/demo backend endpoints.
- Explainability is basic and does not yet include advanced graph visualization or model explainers.
- No trained ML model is applied. Graph-backed responses use `mlStatus: "not_applied"`.

## Sprint 2 — Real Multi-Drug Candidate Generation & Optimization

### Status: Partially Implemented / In Review

- Implemented: graph-derived disease x drug coverage matrix from represented `CtD` relationships.
- Implemented: stable disease IDs, stable compound IDs, treatment evidence, and provenance are preserved through candidate generation.
- Implemented: multi-drug candidate-set generation from graph-derived candidate coverage.
- Implemented: deterministic hard safety filtering runs on candidate drug sets before optimization.
- Implemented: greedy set-cover baseline consumes candidate sets and configurable constraints.
- Implemented: candidate sets are ranked separately from individual graph candidates.
- Implemented: candidate comparison structures show per-drug coverage contribution.
- Implemented: rejected candidate sets include pre-optimization hard-safety reasons.
- Remaining: broaden graph/integration coverage against live Neo4j fixtures where available.
- Remaining: refine frontend support for reviewing multi-drug candidate-set comparisons and rejection details.
- Remaining: continue optimization work beyond the greedy baseline without treating future DDI, synergy, or GNN models as active.

## Sprint 3 — Graph Embedding Baseline

### Status: Planned

- Prepare graph data for embedding.
- Validate entity and relation mappings.
- Implement a first knowledge graph embedding baseline such as TransE.
- Return model version metadata.
- Report graph embedding outputs separately from deterministic graph evidence.

## Sprint 4 — DDI Graph ML

### Status: Planned

- Select an appropriate public DDI dataset.
- Prepare drug identifiers and dataset provenance.
- Build a PyTorch Geometric representation.
- Implement a baseline DDI model.
- Evaluate AUROC, AUPRC, and F1.
- Store model version and experiment metadata.

Important: Hetionet `CrC` is compound resemblance and must not be treated as a DDI label.

## Sprint 5 — Synergy & Explainability

### Status: Planned

- Implement a synergy prediction baseline.
- Add candidate comparison views.
- Add structured rejection reasons.
- Add evidence path outputs.
- Add graph visualization.
- Prepare GNN explainability outputs when an actual GNN exists.

## Sprint 6 — Integration & Evaluation

### Status: Planned

- Integrate graph retrieval, safety rules, optimization, future ML prediction, ranking, and explainability.
- Compare rule-based baseline, greedy KG baseline, graph embedding baseline, and GNN baseline.
- Track knowledge-graph treatment coverage, number of drugs, predicted interaction risk, evidence strength, uncertainty, AUROC, AUPRC, F1, and reproducibility.

## Scope Boundaries

PolyMerge remains research decision-support software. It does not provide autonomous prescribing, dosage recommendations, clinical validation, chemical stability guarantees, or clinical safety claims.
