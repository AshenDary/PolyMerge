# PolyMerge Team & Current Responsibilities

## Jared — Knowledge Graph / Biomedical Data Engineer

### Current Sprint 1 Work

- Neo4j integration.
- Hetionet graph schema verification.
- Graph data loading/preprocessing support.
- Disease retrieval from Neo4j.
- Disease to compound retrieval using represented `CtD` relationships.
- Compound-gene evidence using `CbG`, `CuG`, and `CdG`.
- Side-effect evidence using `CcSE`.
- Evidence/provenance structure.
- Graph-backed candidate generation.
- Backend disease catalog integration through the ML/Graph service.

### Current Status

Sprint 1 graph foundation is implemented and ready for review. Sprint 2
candidate-set foundations preserve graph-derived coverage and provenance.
Sprint 3 adds Jared's completed DDInter 2.0 severity dataset, PubChem PUG REST
enrichment, RDKit descriptors, graph-derived tabular features, EDA, and
leakage-safe preprocessing. Sprint 4 completed training-only cross-validation
and selected `RandomForestClassifier`; no predictive model is integrated or served.

## Ranee — Backend / Traditional ML Integration

### Current Sprint 1 Work

- Fastify backend API.
- FastAPI ML/Graph service integration.
- Request validation.
- API response contract checks.
- Backend fallback behavior.
- Dependency health checks.
- Python environment compatibility for ML tests.
- Backend and integration tests.
- Traditional model serving contract after model selection.
- Model metadata and unavailable-model handling.

### Current Status

Backend and ML/Graph integration is implemented for Sprint 1. Real graph-backed responses are labeled with `dataStatus: "real_graph"` and `mlStatus: "not_applied"`. Demo fallback remains available only as clearly labeled fallback output. Future model integration should serve a selected traditional ML model, not a neural-network model.

## Pamela — Optimization / Explainability

### Current Sprint 1 / 2 Work

- Greedy set-cover baseline.
- Candidate ranking foundation.
- Optimization tests.
- Safety and optimization verification.
- Sprint 2 multi-drug candidate-set generation, comparison, rejection reasons, and optimization planning.
- Academic evaluation outputs and Streamlit deployment planning.

### Current Status

The optimizer consumes graph-derived candidate-set coverage and produces baseline selected candidates. Future work is richer constraints, comparison views, rejection explanation presentation, academic evaluation reporting, and Streamlit/frontend visualization.

## Handoff Expectations

- Graph evidence must remain separate from future traditional ML predictions.
- Hard safety rules must remain deterministic and independent of model scores.
- `CrC` must not be treated as a DDI label.
- DDInter is the Sprint 3 severity-label source. Unknown is excluded from
  supervised training, and absent interactions are not treated as safe negatives.
- PubChem/RDKit provide molecular features; Hetionet provides graph evidence
  and optional graph features rather than the supervised target.
- Coverage means knowledge-graph treatment coverage, not clinical efficacy.
- Any future model or dataset integration must include provenance and model/version metadata.
- The completed academic comparison used `LogisticRegression`,
  `RandomForestClassifier`, and `HistGradientBoostingClassifier` with the same
  training split, fold-local preprocessing, five-fold strategy, and Macro F1
  primary metric. `RandomForestClassifier` advances to Sprint 5.
