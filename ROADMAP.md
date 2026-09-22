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
- `dataStatus` and `mlStatus` distinguish real graph data from future traditional ML prediction.
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
- Remaining: continue optimization work beyond the greedy baseline without treating traditional ML prediction as active before training and integration.

## Sprint 3 — Dataset, EDA & Traditional Feature Engineering

### Status: Planned

- Finalize the supervised ML problem, with drug-pair interaction classification as the preferred task.
- Finalize the dataset, target variable, and negative-label strategy.
- Document dataset source, license, inclusion criteria, and known limitations.
- Build a data dictionary for raw fields, engineered features, and target labels.
- Inspect missing values, duplicate rows, target/class distribution, and outliers.
- Create at least five meaningful EDA visualizations for the academic workflow.
- Create leakage-safe preprocessing shared by all models.
- Derive traditional tabular features from compound identity encodings, graph relationship counts, gene-target overlap, side-effect overlap, pharmacologic-class features, treatment coverage features, and optional reproducible RDKit descriptors.
- Prepare reproducible train/test data.
- If a suitable DDI classification dataset cannot be finalized, document a fallback supervised drug-disease treatment classification task derived from Hetionet.

## Sprint 4 — Three Traditional ML Model Comparison

### Status: Planned

- Compare exactly three permitted traditional ML algorithms: Logistic Regression, Random Forest, and Gradient Boosting.
- Use the same train/test split for all models.
- Use the same preprocessing logic for all models.
- Use the same cross-validation strategy and folds for all models.
- Use the same primary metric for all model selection decisions.
- Tune only on training data.
- Report validation mean and variability for the primary metric.
- Compare supporting metrics appropriate to the selected target.
- Select the final model using documented evidence.
- Store experiment metadata and model-version information.

Important: Hetionet `CrC` is compound resemblance and must not be treated as a DDI label.

## Sprint 5 — Final Evaluation & PolyMerge Integration

### Status: Planned

- Evaluate the selected model exactly once on the untouched test set.
- Save the leakage-safe preprocessing pipeline.
- Save the selected model.
- Expose model metadata and training-data provenance.
- Integrate traditional ML predictions with PolyMerge candidate scoring where appropriate.
- Keep deterministic safety rules independent from model scores.
- Preserve graph evidence/provenance separately from ML prediction output.
- Do not claim clinical safety, efficacy, or prescribing suitability.
- Continue candidate comparison, rejection reasons, evidence paths, and graph visualization work as research explainability aids.

## Sprint 6 — Deployment, Documentation & Academic Submission

### Status: Planned

- Deploy with Streamlit unless the instructor approves the existing frontend as the deployment target.
- Finalize README and setup instructions.
- Package the dataset artifacts allowed for submission.
- Finalize the data dictionary.
- Finalize `requirements.txt`.
- Capture screenshots for the deployed workflow.
- Prepare the IMRaD paper.
- Add IEEE references.
- Document model limitations, graph limitations, safety boundaries, and reproducibility steps.
- Verify reproducibility from a clean setup.

## Scope Boundaries

PolyMerge remains research decision-support software. It does not provide autonomous prescribing, dosage recommendations, clinical validation, chemical stability guarantees, or clinical safety claims.
