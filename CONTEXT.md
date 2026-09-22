# Project Context: PolyMerge

## Purpose

PolyMerge is a research decision-support platform for candidate discovery in a
biomedical knowledge-graph setting. It helps researchers and pharmacists
explore disease clusters, retrieve graph relationships, apply deterministic
safety rules, run a greedy set-cover baseline, inspect evidence/provenance, and
prepare traditional supervised ML features for research candidates.

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
  ↓
Future traditional supervised ML scoring after dataset selection and training
```

MySQL is used as the application/system data foundation. The biomedical
knowledge graph is not duplicated into MySQL. Neo4j remains the biomedical
evidence source; future traditional ML uses derived tabular features rather
than replacing the graph evidence layer.

## Core Design Principles

- Decision-support only: outputs are research candidates for expert review.
- Deterministic safety rules remain independent from model scores.
- Coverage is a knowledge-graph metric, not a clinical efficacy claim.
- Evidence/provenance must be explicit for known graph relationships, rule outcomes, and future traditional model outputs.
- Future traditional model scores must be labeled clearly as predictions and separated from graph evidence.
- No neural-network, deep-learning, GNN, transformer, large language model,
  pretrained foundation model, or AutoML-generated model is planned for the
  final academic ML solution.

## Current Implementation Status

### Implemented Now

- Disease selection workflow in the UI.
- Backend `/api/diseases` retrieves the disease catalog from the graph-backed ML service.
- Backend validates selected diseases against the graph-backed catalog before candidate search.
- ML/Graph service retrieves diseases and compounds from Neo4j.
- Disease to compound retrieval uses represented `CtD` treatment relationships.
- Compound-gene evidence uses `CbG`, `CuG`, and `CdG`.
- Side-effect evidence uses `CcSE`.
- Graph-backed candidate generation returns single-drug candidates with evidence/provenance.
- Disease x drug coverage is derived from represented `CtD` edges.
- Multi-drug candidate-set generation preserves stable IDs, graph evidence, and provenance.
- Hard contraindication rules are preserved and exposed with structured reason payloads.
- Greedy set-cover baseline consumes graph-derived candidate-set coverage.
- Candidate ranking, comparison fields, and rejection reasons are present as a Sprint 2 foundation.
- Backend fallback behavior is explicitly labeled as demo fallback when the ML/Graph service is unavailable.
- Research-only terminology is used in API and UI text.

### Planned Next

- Finalize the supervised ML problem, preferred as drug-pair interaction classification.
- Select a legitimate dataset, target variable, and negative-label strategy.
- Run required EDA, including missing values, duplicates, class distribution, outliers, and at least five meaningful visualizations.
- Build leakage-safe preprocessing and traditional tabular features.
- Compare exactly three traditional ML algorithms: Logistic Regression, Random Forest, and Gradient Boosting.
- Use the same train/test split, preprocessing logic, cross-validation strategy, and primary metric for all models.
- Evaluate the selected model exactly once on an untouched test set.
- Save the preprocessing pipeline and selected model for deployment.
- Deploy with Streamlit unless another framework is instructor-approved.
- Graph visualization.

## Data Reality and Current Limitations

- Hetionet is currently the available knowledge-graph source.
- Hetionet does not directly provide drug-drug interaction labels.
- `CrC` means compound resemblance and must not be treated as DDI.
- Drug-pair interaction classification requires a dedicated supervised dataset
  and a documented target variable.
- Absence of a known DDI label is not proof that a drug pair is safe.
- Current graph-backed candidates use `mlStatus: "not_applied"`.
- Current predictive ML output is not active until the traditional model is trained and integrated.
- The optimizer is a greedy baseline, not a production-grade optimizer.

## Scope Boundaries

### In Scope

- Knowledge-graph retrieval.
- Candidate generation from represented graph relationships.
- Hard safety rules.
- Greedy set-cover baseline.
- Candidate ranking foundation.
- Traditional ML dataset preparation, EDA, feature engineering, model comparison, and deployment.
- Evidence/provenance structures.

### Out of Scope

- Autonomous prescribing.
- Dosage recommendations.
- Clinical validation or regulatory approval.
- Chemical stability/formulation guarantees.
- Active ML predictions until a real traditional model and dataset are integrated.
