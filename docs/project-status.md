# PolyMerge Project Status

Current as of 2026-09-30.

## Current Phase

Sprint 5 - Final Evaluation and Integration is in progress under master Issue
#39. Sprint 1 through Sprint 4 milestones are implemented. Sprint 6 remains
planned and depends on Sprint 5 closeout.

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

- Issue #42, owned by Ranee: selected-model serving and API integration.
- Issue #43 and open PR #46, owned by Pamela: candidate comparison and
  explainability integration.
- Issue #39, owned by Jared: integrated Sprint 5 validation and closeout after
  #42 and #43 are complete.

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
| Runtime serving in `main` | Not active; pending #42 |
| Graph-backed response status | `mlStatus: "not_applied"` |

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
3. ML prediction will record predicted DDI severity and inference metadata once
   #42 is integrated.

Graph coverage does not establish clinical efficacy. Predicted severity does
not establish clinical safety.

## Remaining Before Sprint 6

- Merge and validate #42 model serving and API integration.
- Complete #43 comparison and explainability integration against the final
  graph and ML contracts.
- Run #42/#43 integration tests and the #39 master regression audit.
- Prepare the Sprint 6 deployment and academic-submission handoff.

## Research and Clinical Boundaries

PolyMerge is research decision-support software. It does not provide autonomous
prescribing, dosage recommendations, clinical validation, regulatory approval,
or a clinical safety guarantee. Missing graph relationships and absent DDInter
labels are not evidence of biological absence or safety.
