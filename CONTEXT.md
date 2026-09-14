# Project Context: PolyMerge

## Purpose

PolyMerge is a research platform for candidate discovery in a biomedical knowledge-graph setting. It helps researchers and pharmacists explore disease clusters, retrieve graph relationships, score candidate drug combinations with research-only predictive models, apply deterministic safety rules, and compare ranked candidate sets.

PolyMerge is not an autonomous prescribing system and does not produce clinically validated safety guarantees or dosage recommendations.

## Research-oriented architecture

The current repository reflects a staged MVP architecture:

```text
Frontend
  ↓
Fastify backend
  ↓
FastAPI ML engine
  ↓
Neo4j biomedical knowledge graph
  ↓
Candidate generation / optimization / explainability
```

MySQL is used for application metadata, query history, experiments, and audit logging. The biomedical knowledge graph is not duplicated into MySQL.

## Core design principles

- Decision-support only: outputs are research candidates for expert review.
- Deterministic safety rules always win over model scores.
- Coverage is a knowledge-graph metric, not a clinical guarantee.
- Evidence/provenance must be explicit for known relationships, model predictions, rule outcomes, and insufficient evidence.
- Model scores must be labeled clearly as predictions or demo values when they are not backed by real datasets.

## Data reality and current limitations

- Hetionet is currently the available knowledge-graph fragment in this repository.
- Hetionet does not directly provide drug-drug interaction labels.
- DDI prediction is therefore still a planned capability unless a real dataset is integrated.
- DrugBank access/licensing must be described accurately; this repository does not claim a full DrugBank integration.
- The current implementation uses demo data where real ML outputs are not yet available.

## Current implementation status

### Implemented now

- Disease selection workflow in the UI.
- Backend endpoints for disease lookup, drug lookup, interaction metadata, search, result retrieval, explainability, and history.
- Hard contraindication enforcement preserved and exposed in structured responses.
- Demo ML pipeline returning labeled research candidates.
- Candidate ranking and baseline optimization scaffolding.
- Research-only terminology in the UI and API responses.

### Planned next

- Real Neo4j-backed disease and drug retrieval.
- Real ML/GNN DDI prediction and synergy prediction.
- Real candidate optimization with configurable weights.
- Enhanced explainability with structured graphs and provenance.
- Real dataset integration (TWOSIDES or another legally usable DDI dataset, if available).

## Scope boundaries

### In scope

- Knowledge-graph retrieval.
- Candidate generation.
- Hard safety rules.
- Baseline optimization.
- Candidate ranking.
- Explainability structures.

### Out of scope

- Autonomous prescribing.
- Dosage recommendations.
- Clinical validation or regulatory approval.
- Chemical stability/formulation modeling.

## Success criteria for the current phase

- Disease selection can be exercised through the UI and backend.
- Candidate results are clearly labeled as demo values when real ML data are unavailable.
- Hard contraindications can reject a candidate even when model risk is low.
- The repository documents the difference between implemented MVP functionality and planned ML features.
