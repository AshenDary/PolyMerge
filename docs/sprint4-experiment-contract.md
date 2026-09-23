# Sprint 4 Experiment Contract

## Supervised Task

DDI severity classification for canonical unordered drug pairs. This is a
research classification task, not a clinical safety or compatibility claim.

## Target

`ddi_severity`, sourced only from DDInter 2.0.

## Classes

- Major
- Moderate
- Minor

Unknown severity is excluded. Unlabeled or absent pairs are not synthetic safe
negatives.

## Dataset

The Sprint 3 processed DDInter 2.0 dataset contains 130,422 canonical labeled
pairs. The machine-readable feature contract is
`data/interim/sprint4/feature_contract.json`; the feature semantics are defined
in `docs/data-dictionary.md`.

## Feature Count

The model matrix contains exactly 55 numeric, symmetric pair features:

- Hetionet graph summaries and graph availability indicators
- PubChem-verified structure availability indicators
- RDKit molecular descriptor summaries

DDInter IDs, names, pair IDs, raw source severity, source files, dataset labels,
mapping IDs/statuses, PubChem identifiers/structures, and provenance fields are
audit metadata and are excluded from `X`. Availability indicators intentionally
remain features because they distinguish unavailable measurements from known
zero values.

`CrC` means Compound resembles Compound. It contributes only documented
resemblance summaries and is never DDI truth, severity, interaction risk, safety
evidence, or a target label.

## Primary Split

- Train: 104,337 rows
- Test: 26,085 rows
- Design: deterministic 80/20 stratified pair split, random state 42

The split contains unseen pairs, but 1,768 of 1,787 distinct test drugs
(98.936766%) also occur in training. It therefore measures new combinations
among largely familiar drugs, not cold-start or fully unseen-drug generalization.
The primary `test.csv` remains untouched during feature selection, preprocessing
fitting, tuning, cross-validation, and model selection.

## Secondary Split

The secondary stress split has 105,979 training rows and 24,443 test rows with
190 held-out drugs. Every test pair includes at least one held-out drug, and no
held-out drug occurs in its training partition. However, 1,526 partner drugs
occur in both partitions, so this is a secondary one-or-more-unseen-drug
cold-start stress evaluation, not a fully drug-disjoint split. It is not the
primary Sprint 4 model-selection split.

## Shared Preprocessing

Use `ml_engine/app/data/preprocessing.py`. Fit median imputation and scaling on
training data or training CV folds only, then transform validation/test data.
All approved features are numeric; missing graph or molecular measurements are
imputed from training data. Known graph zeros remain distinct from missing
measurements through explicit availability indicators.

## Provenance Reporting

- Target annotations: DDInter 2.0
- Chemical identity and verified structures: PubChem PUG REST
- Molecular descriptors: RDKit
- Graph evidence and optional graph features: Hetionet
- Reproducibility: checked-in source manifests, processing scripts, dataset
  profile, feature coverage audit, data dictionary, and feature manifest

Provenance belongs in experiment/model metadata and reports, not in `X`.

## Primary Sprint 4 Metric

Macro F1 (`f1_macro`).

## Future Models

- `LogisticRegression`
- `RandomForestClassifier`
- `HistGradientBoostingClassifier`

No model is trained by this contract-validation work. Model selection uses
training-only cross-validation; final test evaluation belongs to Sprint 5.
`GradientBoostingClassifier` is only a documented course-compatibility fallback.

## Reproducible Validation

Run:

```bash
python3 scripts/validate_sprint4_contract.py
```

The validator exits non-zero on row, target, schema, leakage, symmetry,
missingness, preprocessing, provenance, or split-contract failure.
