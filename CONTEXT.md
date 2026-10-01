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

Traditional ML is built from DDInter severity labels plus PubChem, RDKit, and
Hetionet tabular features. The finalized Random Forest pipeline predicts DDI
severity. On the Sprint 5 integration branch, candidate-set drug pairs are
scored only when the reviewed runtime bridge can build the frozen 55-feature
row; otherwise prediction remains explicitly not applied.

MySQL is used as the application/system data foundation. The biomedical knowledge graph is not duplicated into MySQL.

## Core Design Principles

- Decision-support only: outputs are research candidates for expert review.
- Deterministic safety rules remain independent from model scores.
- Coverage is a knowledge-graph metric, not a clinical efficacy claim.
- Evidence/provenance must be explicit for known graph relationships, rule outcomes, and model outputs.
- Model scores must be labeled clearly as predictions and separated from graph evidence.

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
- Sprint 4 compared the three approved traditional classifiers with clean,
  training-only five-fold cross-validation and selected
  `RandomForestClassifier` by mean Macro F1.
- Sprint 5 Issue #40 completed the one-time final evaluation. Final test Macro
  F1 is `0.524630`; the test split is not available for further tuning.
- The complete preprocessing/classifier contract is frozen with model version,
  artifact checksum, data hashes, environment versions, and evaluation report.
- Sprint 5 Issue #41 added structured `graphEvidence.paths`, deterministic path
  IDs, path-level provenance, and per-drug evidence path references.

### Current Integration State

- Issue #42 serving is integrated on the temporary branch with checksum,
  version, feature-schema, unavailable-model, and corrupt-artifact protections.
- Candidate-set pair inference uses the same frozen 55-feature contract and
  fails closed when a graph candidate pair cannot be deterministically bridged.
- Issue #43 explainability consumes `graphEvidence.paths`, precomputed
  deterministic rule state, and real ML prediction output without mixing the
  channels.
- Issue #39 remains pending final branch review and closeout before the Sprint
  6 handoff.

### Three Independent Result Channels

1. Knowledge-graph evidence: represented `CtD`, gene-context, and side-effect
   paths with source and graph-version provenance.
2. Deterministic rules: accepted/rejected status and structured hard-rule
   reasons.
3. ML prediction: pair-level predicted DDInter severity, model version, and
   inference metadata only when the frozen model actually runs.

These channels must not be collapsed into a single safety score. Graph coverage
is not clinical efficacy, and predicted severity is not a clinical safety
determination.

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
- Current graph-backed candidates use `mlStatus: "applied"` only for successful
  pair-level Random Forest inference; unsupported pairs remain
  `mlStatus: "not_applied"`.
- The selected model is finalized, evaluated, and served from the verified
  joblib artifact without rerunning final evaluation.
- The joblib pipeline is approximately 240 MB and intentionally ignored by Git;
  its metadata and final evaluation report are tracked for reproducibility.
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
- Predictive DDI severity output for graph pairs that cannot be represented by
  the frozen 55-feature contract.
