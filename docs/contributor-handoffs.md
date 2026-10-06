# Sprint 5 Technical Ownership and Handoffs

Current as of 2026-09-30. This document records technical ownership and
integration dependencies; GitHub issues and merged source remain authoritative.

## Jared / AshenDary

### Issue #40 / PR #44 - Complete and Merged

Owned the final `RandomForestClassifier` evaluation and artifact contract:

- One-time evaluation on the primary Sprint 3 test split.
- Frozen preprocessing/classifier configuration.
- Final metrics, model version, artifact checksum, data hashes, and environment
  provenance.
- Serving handoff that requires the complete 55-feature pipeline and fail-closed
  behavior.

The approximately 240 MB joblib artifact is intentionally ignored by Git. The
repository tracks its checksum, metadata, and evaluation report.

### Issue #41 / PR #45 - Complete and Merged

Owned graph evidence and provenance normalization:

- Deterministic `graphEvidence.paths` and path IDs.
- `CtD` treatment, `CbG`/`CuG`/`CdG` gene-context, and `CcSE` side-effect-context
  semantics.
- Candidate-set path union and per-drug `evidencePathIds`.
- Explicit separation from deterministic rules and ML predictions.

Jared retains coordination responsibility for the Issue #39 closeout audit
after downstream integrations are complete.

## Ranee / seavens3nt

### Issue #42 - Open

Owns selected-model serving and API integration:

- Load the frozen Random Forest pipeline without retraining.
- Build the approved feature input in the documented order.
- Expose predicted DDI severity, model version, and inference status separately
  from graph evidence and hard-rule outcomes.
- Define fail-closed behavior when the artifact or input schema is unavailable.

Until #42 merges, current-main graph-backed candidate responses retain
`mlStatus: "not_applied"` and do not provide active DDI predictions.

## Pamela / Qiuyuan26

### Issue #43 / PR #46 - Open and In Progress

Owns candidate comparison and explainability integration:

- Consume merged `graphEvidence.paths` and per-drug path references.
- Present graph evidence, deterministic rejection reasons, and ML predictions as
  distinct channels.
- Align active prediction presentation with the final #42 response contract.

PR #46 is not part of `main` while it remains open. Its implementation should
not infer treatment efficacy or safety from graph paths, and path absence must
not be treated as a known negative biomedical fact.

## Integration Order

1. #40 supplies the finalized model and reproducibility contract to #42.
2. #41 supplies graph path semantics and provenance to #43.
3. #42 supplies the runtime prediction contract needed by #43.
4. #42 and #43 require integrated testing before #39 can close.
5. Sprint 6 begins after the Sprint 5 closeout and handoff.

## Shared Boundaries

- Graph coverage is represented `CtD` coverage, not clinical efficacy.
- `CrC` is resemblance only, never DDI truth, severity, treatment evidence, or
  safety evidence.
- Deterministic hard rules remain independent of model outputs.
- Predicted severity is research classification output, not a clinical safety
  recommendation.
