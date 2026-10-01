# Sprint 5 - Final Evaluation & PolyMerge Integration

## Goal

Complete final evaluation and integrate model predictions with PolyMerge without
mixing predictions, graph evidence, or deterministic rule outcomes.

## Status

In progress under master Issue #39. Issues #40 and #41 are complete; Issues #42
and #43 remain open.

## Shared Tasks

- [x] Evaluate selected model exactly once on the primary test split (#40)
- [x] Freeze the preprocessing/classifier pipeline contract (#40)
- [x] Record model artifact checksum, version, and reproducibility metadata (#40)
- [x] Expose traceable graph evidence and provenance paths (#41)
- [ ] Integrate predictions with PolyMerge candidate scoring where appropriate
- [x] Keep deterministic safety rules independent
- [x] Preserve graph evidence/provenance separately from ML prediction
- [ ] Add candidate comparison and rejection reason presentation
- [x] Add deterministic treatment, gene-context, and side-effect evidence paths
- [ ] Complete graph evidence presentation and visualization where useful
- [ ] Run the #42/#43 integration and Sprint 5 master regression audit

## Definition of Done

- [ ] Candidate results include explainability payloads
- [x] Rejection reasons are structured independently from graph evidence
- [ ] Predictions remain clearly labeled as model outputs
- [x] No clinical validation claims are introduced
