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
traditional supervised data foundation using the available Hetionet fragment.
Future DDI work still requires a legitimate dedicated DDI dataset.

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

The Sprint 1 optimizer consumes graph-derived coverage and produces baseline selected compounds. Future work is multi-drug candidate-set generation, richer constraints, comparison, rejection explanations, and frontend visualization.

## Handoff Expectations

- Graph evidence must remain separate from future ML predictions.
- Hard safety rules must remain deterministic and independent of model scores.
- `CrC` must not be treated as a DDI label.
- Sprint 3 fallback `CtD` labels describe represented graph relationships, not
  clinical truth.
- Coverage means knowledge-graph treatment coverage, not clinical efficacy.
- Any future model or dataset integration must include provenance and model/version metadata.
