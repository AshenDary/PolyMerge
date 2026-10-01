# PolyMerge Project Status

Current as of 2026-10-01.

## Current Phase

Sprint 5 - Final Evaluation and Integration is repaired on the temporary
integration branch for final Issue #39 validation. Sprint 1 through Sprint 4
milestones are implemented. Sprint 6 remains planned and depends on Sprint 5
closeout.

## Completed Milestones

- Sprint 1: graph-backed retrieval and service foundations.
- Sprint 2: multi-drug candidate sets, deterministic hard-rule filtering, and
  greedy set-cover optimization.
- Sprint 3: DDInter data foundation, PubChem/RDKit enrichment, 55-feature
  contract, EDA, and leakage-safe splits.
- Sprint 4: reproducible comparison of three traditional classifiers and
  selection of `RandomForestClassifier` by validation Macro F1.
- Sprint 5 Issue #40 / PR #44: one-time final test evaluation, frozen pipeline
  contract, model version/checksum, and reproducibility report.
- Sprint 5 Issue #41 / PR #45: structured graph evidence paths and provenance.

## Current Work

- Issue #42 implementation is integrated on the temporary branch with
  fail-closed model serving, checksum/version validation, and candidate-pair
  inference through the reviewed 55-feature bridge.
- Issue #43 implementation is integrated on the temporary branch with canonical
  graph/rule/ML explainability and frontend wiring.
- Issue #39, owned by Jared: final integrated Sprint 5 validation and closeout
  after branch review.

## Current ML State

| Item | Current state |
| --- | --- |
| Selected model | `RandomForestClassifier` |
| Sprint 4 CV Macro F1 | `0.506086 +/- 0.005695` |
| Final test Macro F1 | `0.524630` |
| Final test use | Completed exactly once; not available for tuning |
| Model version | `RandomForestClassifier-sprint5-v1-65e9834666ad19c5` |
| Pipeline artifact | 251,404,304-byte joblib; intentionally not tracked in Git |
| Reproducibility record | Tracked metadata and final evaluation report |
| Runtime serving on integration branch | Active for bridgeable candidate pairs; unavailable pairs fail closed |
| Graph-backed response status | `mlStatus: "applied"` only after real inference; otherwise `not_applied` |

Moderate-class performance is substantially stronger than Major and Minor.
The final results are research classification performance, not clinical
validation.

## Current Graph State

Candidate and candidate-set payloads expose `graphEvidence.source`,
`graphEvidence.graphVersion`, and deterministic `graphEvidence.paths`.
Supported semantics are:

- `treatment` for represented `CtD` relationships.
- `gene_context` for represented `CbG`, `CuG`, and `CdG` relationships.
- `side_effect_context` for represented `CcSE` relationships.

`CrC` means Compound resembles Compound. It is not DDI truth, severity, safety
evidence, contraindication, or treatment evidence.

## Current Integration State

PolyMerge keeps three independent result channels:

1. Graph evidence records represented relationships, graph paths, and
   provenance.
2. Deterministic rules record accepted/rejected status and hard-rule reasons.
3. ML prediction records pair-level predicted DDInter severity and model
   metadata only after the real frozen model runs.

Graph coverage does not establish clinical efficacy. Predicted severity does
not establish clinical safety.

## Remaining Before Sprint 6

- Review and merge the repaired temporary Sprint 5 integration branch.
- Use the passing integration tests and regression audit as evidence for #39
  closeout.
- Prepare the Sprint 6 deployment and academic-submission handoff.

## Research and Clinical Boundaries

PolyMerge is research decision-support software. It does not provide autonomous
prescribing, dosage recommendations, clinical validation, regulatory approval,
or a clinical safety guarantee. Missing graph relationships and absent DDInter
labels are not evidence of biological absence or safety.
