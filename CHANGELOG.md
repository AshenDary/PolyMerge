# PolyMerge Milestone Changelog

This changelog summarizes verified project milestones. It does not represent
semantic software releases.

## Sprint 5 - In Progress

### Added

- Final `RandomForestClassifier` evaluation contract and one-time primary-test
  result through Issue #40 / PR #44.
- Final model version, pipeline checksum, data provenance, environment metadata,
  and evaluation report.
- Structured `graphEvidence.paths`, deterministic path IDs, and path-level
  provenance through Issue #41 / PR #45.
- Treatment, gene-context, and side-effect path semantics with per-drug path
  references in candidate comparisons.
- Runtime Random Forest serving with checksum, version, feature-schema,
  unavailable-model, and corrupt-artifact protections.
- Candidate-set pair predictions through the reviewed 55-feature bridge when a
  graph candidate pair can be represented without fabricating features.
- Canonical explainability payloads and frontend wiring for graph evidence,
  deterministic rules, and ML prediction channels.

### Changed

- Candidate-set graph evidence now preserves a deterministic, deduplicated union
  of member-drug paths.
- Sprint 5 documentation distinguishes finalized model evaluation from runtime
  serving and candidate-pair inference.

### Pending

- Issue #39 final review, integration PR, and Sprint 5 closeout.

## Sprint 4 - Model Comparison Complete

### Added

- Reproducible training-only five-fold comparison of `LogisticRegression`,
  `RandomForestClassifier`, and `HistGradientBoostingClassifier`.
- Selection of `RandomForestClassifier` by mean validation Macro F1.
- Fixed feature, preprocessing, split, and experiment contracts.

## Sprint 3 - ML Data Foundation Complete

### Added

- DDInter 2.0 Major/Moderate/Minor severity dataset and provenance audits.
- Conservative PubChem mapping, RDKit descriptors, and Hetionet tabular
  features.
- Canonical 55-feature contract, deterministic train/test split, EDA, and data
  dictionary.

Unknown severity remains excluded from supervised modeling, and absent DDInter
records are not treated as safe or no-interaction examples.
