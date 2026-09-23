# Project Context: PolyMerge

## Purpose

PolyMerge is a research decision-support platform for candidate discovery in a biomedical knowledge-graph setting. It helps researchers and pharmacists explore disease clusters, retrieve graph relationships, apply deterministic safety rules, run a greedy set-cover baseline, and inspect evidence/provenance for research candidates.

PolyMerge is not an autonomous prescribing system and does not produce clinically validated safety guarantees, dosage recommendations, or clinical treatment decisions.

## Current Architecture And Direction

```text
Frontend
  ↓
Fastify backend
  ↓
FastAPI ML/Graph service
  ↓
Neo4j biomedical knowledge graph
  ↓
Graph-backed candidate generation / safety filtering / greedy set-cover baseline
```

MySQL is used as the application/system data foundation. The biomedical knowledge graph is not duplicated into MySQL.

## Core Design Principles

- Decision-support only: outputs are research candidates for expert review.
- Deterministic safety rules remain independent from model scores.
- Coverage is a knowledge-graph metric, not a clinical efficacy claim.
- Evidence/provenance must be explicit for known graph relationships, rule outcomes, and future model outputs.
- Future model scores must be labeled clearly as predictions and separated from graph evidence.

## Current Implementation Status

### Implemented Now

- Disease selection workflow in the UI.
- Backend `/api/diseases` retrieves the disease catalog from the graph-backed ML service.
- Backend validates selected diseases against the graph-backed catalog before candidate search.
- ML/Graph service retrieves diseases and compounds from Neo4j.
- Disease to compound retrieval uses represented `CtD` treatment relationships.
- Compound-gene evidence uses `CbG`, `CuG`, and `CdG`.
- Side-effect evidence uses `CcSE`.
- Graph-backed candidate generation returns individual compound candidates with evidence/provenance.
- Hard contraindication rules are preserved and exposed with structured reason payloads.
- Greedy set-cover baseline consumes graph-derived coverage.
- Backend fallback behavior is explicitly labeled as demo fallback when the ML/Graph service is unavailable.
- Research-only terminology is used in API and UI text.

### Planned Next

- Sprint 4 comparison of `LogisticRegression`, `RandomForestClassifier`, and
  `HistGradientBoostingClassifier` using the Sprint 3 split and preprocessing
  contract. `GradientBoostingClassifier` is only a course-compatibility fallback.
- Use macro F1 as the primary model-selection metric and evaluate the selected
  model once on the untouched test set.
- Save the selected preprocessing pipeline, model, and experiment metadata only
  after training and validation are complete.
- Graph visualization.

## Data Reality and Current Limitations

- Hetionet is currently the available knowledge-graph source.
- Hetionet does not directly provide drug-drug interaction labels.
- `CrC` means compound resemblance and must not be treated as DDI.
- Sprint 3 uses DDInter 2.0 severity labels (Major, Moderate, Minor). Unknown is
  excluded from supervised data, with no synthetic no-interaction examples.
- The completed dataset has 130,422 canonical labeled pairs, an 80/20 stratified
  split, and 55 final features.
- Hetionet supplies optional graph features; `CrC` is resemblance only.
- PubChem supplies conservatively verified structures, and RDKit supplies
  deterministic interpretable descriptors. Official PUG REST enrichment produced
  1,315 validated mappings and 67.818% distinct-drug structure coverage; missing
  coverage is explicit.
- Current graph-backed candidates use `mlStatus: "not_applied"`.
- Current predictive ML output is inactive until a traditional model is trained,
  validated, and integrated.
- The optimizer is a greedy baseline, not a production-grade optimizer.

## Scope Boundaries

### In Scope

- Knowledge-graph retrieval.
- Candidate generation from represented graph relationships.
- Hard safety rules.
- Greedy set-cover baseline.
- Candidate ranking foundation.
- Evidence/provenance structures.

### Out of Scope

- Autonomous prescribing.
- Dosage recommendations.
- Clinical validation or regulatory approval.
- Chemical stability/formulation guarantees.
- Predictive DDI severity output until a trained model is validated and integrated.
