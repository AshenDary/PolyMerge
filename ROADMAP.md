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
- Remaining: continue optimization work beyond the greedy baseline without
  treating future supervised model scores as active.

## Sprint 3 — Dataset, EDA & Traditional Feature Engineering

### Status: DDInter Migration Implemented / Ready For Review

- Implemented: official DDInter 2.0 acquisition, checksums, license, and provenance.
- Implemented: 130,422 canonical Major/Moderate/Minor severity pairs; Unknown is
  audited and excluded, with no synthetic negative labels.
- Implemented: duplicate, reverse-pair, malformed, and label-conflict audits.
- Implemented: conservative PubChem structure mapping for 1,315 drugs and six RDKit descriptors.
- Implemented: symmetric pair features with explicit graph/structure availability indicators.
- Implemented: 55-feature matrix and per-feature coverage/distribution audit.
- Implemented: secondary one-or-more-unseen-drug cold-start split for research analysis.
- Implemented: data dictionary, profile, EDA findings, and seven figures.
- Implemented: leakage-safe scikit-learn preprocessing helper for Sprint 4.
- Implemented: deterministic 80/20 stratified train/test split.
- Implemented: 104,337 training rows and 26,085 test rows in the primary split.
- Implemented: Sprint 3 tests for dataset validity, features, preprocessing,
  and split behavior.
- Preserved: old CtD data only as a clearly named legacy prototype.
- Not implemented in Sprint 3: model training, GNNs, graph embeddings, neural networks, or transformers.

## Sprint 4 — Traditional Supervised ML Model Comparison

### Status: Implemented / Ready for Sprint 5

- Compared exactly `LogisticRegression`, `RandomForestClassifier`, and
  `HistGradientBoostingClassifier` using fixed parameters.
- Used one materialized five-fold stratified split of the Sprint 3 training data.
- Fitted median imputation and standard scaling separately within each training fold.
- Selected `RandomForestClassifier` by mean validation Macro F1.
- Reported a most-frequent predictor as a non-competing context baseline.
- Kept the Sprint 3 test split untouched for Sprint 5 final evaluation.
- Kept model persistence, serving, and candidate scoring inactive.

Important: Hetionet `CrC` is compound resemblance and must not be treated as a DDI label.

## Sprint 5 — Final Evaluation & Integration

### Status: Planned

- Evaluate the selected model exactly once on the untouched test set.
- Save the leakage-safe preprocessing pipeline and selected model.
- Expose model metadata and training-data provenance.
- Integrate traditional ML predictions with candidate scoring where appropriate.
- Keep deterministic safety rules independent from model scores.
- Preserve graph evidence/provenance separately from ML prediction output.
- Continue candidate comparison, rejection reasons, evidence paths, and graph
  visualization as research explainability aids.

## Sprint 6 — Deployment, Documentation & Academic Submission

### Status: Planned

- Deploy with Streamlit unless the instructor approves the existing frontend.
- Finalize README, setup instructions, data dictionary, and requirements.
- Package submission-eligible dataset and model artifacts.
- Capture workflow screenshots and prepare the IMRaD paper with IEEE references.
- Document model and graph limitations, safety boundaries, and reproducibility.
- Verify the complete workflow from a clean setup.

## Scope Boundaries

PolyMerge remains research decision-support software. It does not provide autonomous prescribing, dosage recommendations, clinical validation, chemical stability guarantees, or clinical safety claims.
