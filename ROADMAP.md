# PolyMerge Roadmap

## Phase 1 — Current MVP foundation

### Status: Implemented

- Static research dashboard with disease selection and candidate summary views.
- Fastify backend routes for disease, drug, interaction, search, result, explainability, and history.
- Demo ML engine response structure with labeled evidence and model metadata.
- Deterministic hard safety checks that reject prohibited combinations regardless of model score.
- Baseline planning for candidate ranking/coverage.

### Planned work

- Real Neo4j-backed disease/drug retrieval.
- Real candidate generation from graph relationships.
- Real set-cover optimization with configurable weights and constraints.

## Phase 2 — Baseline graph + optimization

### Status: Partially implemented

- Candidate generation and ranking modules exist, but they are demo placeholders.
- Safety filtering is implemented.
- Set-cover optimizer is scaffolded, but not yet connected to real graph data.

### Planned work

- Replace demo graph access with live Neo4j queries.
- Add configurable optimization settings for minimum coverage, max drug count, max interaction risk, and evidence level.
- Add explicit uncertainty/evidence penalties where supported.

## Phase 3 — Real ML baseline

### Status: Planned

- TransE or another graph embedding baseline.
- Real top-K retrieval for candidate drugs.
- Research-oriented model metadata and provenance output.

## Phase 4 — GNN + DDI/synergy prediction

### Status: Planned

- GNN-based DDI prediction using a legally usable public dataset such as TWOSIDES when available.
- Synergy prediction pipeline.
- Model versioning and timestamped results.

## Phase 5 — Explainability and comparison

### Status: Planned

- Structured explainability payloads.
- Candidate comparison views.
- Rejection reason explanations for lower-ranked or blocked candidates.
- Cytoscape-style graph visualization where practical.

## Stretch goals

- Multiparticulate release / formulation scheduling.
- Additional evidence provenance interfaces.
- Experiment tracking and query audit records in MySQL.

## Current implementation notes

- The repository now uses research-only terminology, not clinical claims.
- The current API can return demo results when the ML engine is unavailable.
- No real clinical validation, dosage recommendation, or chemical stability modeling is included.
