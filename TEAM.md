# PolyMerge Team & Sprint 1 Status

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

Sprint 1 graph foundation is implemented and ready for review. Sprint 3 adds a
DDInter 2.0 severity data foundation and optional mapped Hetionet graph features.
No predictive model has been trained or integrated.

## Ranee — Backend / ML Integration

### Current Sprint 1 Work

- Fastify backend API.
- FastAPI ML/Graph service integration.
- Request validation.
- API response contract checks.
- Backend fallback behavior.
- Dependency health checks.
- Python environment compatibility for ML tests.
- Backend and integration tests.

### Current Status

Backend and ML/Graph integration is implemented for Sprint 1. Real graph-backed responses are labeled with `dataStatus: "real_graph"` and `mlStatus: "not_applied"`. Demo fallback remains available only as clearly labeled fallback output.

## Pamela — Optimization / Explainability

### Current Sprint 1 Work

- Greedy set-cover baseline.
- Candidate ranking foundation.
- Optimization tests.
- Safety and optimization verification.
- Sprint 2 multi-drug optimization planning.

### Current Status

The Sprint 1 optimizer consumes graph-derived coverage and produces baseline selected compounds. Sprint 3 now supplies a DDInter 2.0 severity dataset for future traditional ML; no model is trained yet.

## Handoff Expectations

- Graph evidence must remain separate from future ML predictions.
- Hard safety rules must remain deterministic and independent of model scores.
- `CrC` must not be treated as a DDI label.
- Sprint 3 labels come only from curated DDInter severity. Unknown is excluded,
  and absent interactions are never treated as safe negatives.
- Hetionet features have limited exact-name coverage and do not define the target.
- Coverage means knowledge-graph treatment coverage, not clinical efficacy.
- Any future model or dataset integration must include provenance and model/version metadata.
