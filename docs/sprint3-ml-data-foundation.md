# Sprint 3 ML Data Foundation

## Dataset Decision

The preferred DDI task is blocked for Sprint 3 because the repository contains no
legitimate DDI label dataset such as TWOSIDES, OFFSIDES-derived DDI labels, or
DrugBank interaction labels with approved redistribution/access. Hetionet `CrC`
is chemical resemblance only and is not used as a DDI label.

Implemented fallback:

```text
Compound + Disease -> traditional tabular graph-count features -> ctd_label
```

This is represented CtD relationship classification, not clinical efficacy
classification.

## Outputs

- Full dataset: `data/processed/sprint3/ml_dataset.csv`
- Training split: `data/processed/sprint3/train.csv`
- Test split: `data/processed/sprint3/test.csv`
- Profile: `data/interim/sprint3/dataset_profile.json`
- EDA findings: `docs/sprint3-eda-findings.md`
- EDA figures: `docs/figures/sprint3/*.svg`
- Data dictionary: `docs/data-dictionary.md`

## Current Dataset Summary

- Rows: 426
- Positives: 142 represented `CtD` rows
- Non-positives: 284 deterministic sampled rows without represented `CtD`
- Split: 80/20 stratified row split
- Train rows: 340
- Test rows: 86
- Random state: 42

## Feature Engineering

Features are traditional numeric tabular features from represented graph
relationships: drug gene counts, side-effect counts, pharmacologic-class counts,
chemical-resemblance neighbor counts, graph-degree counts, disease graph-degree
counts, and exact `CpD` pair evidence. No graph embeddings, neural networks,
TransE, RotatE, PyTorch, or GNN features are used.

CtD count features are row-leakage-safe: for a positive row, the current
Compound-Disease CtD edge is subtracted from the compound and disease CtD counts.

RDKit descriptors are not used in Sprint 3 because the checked-in fragment does
not contain molecular structures such as SMILES with a verified mapping.

## Preprocessing Contract

Sprint 4 should use:

- `ml_engine/app/data/preprocessing.py`
- `split_features_target(train_df)`
- `build_preprocessing_pipeline(train_df)`

The preprocessor is a scikit-learn `ColumnTransformer` intended to be fitted on
training data only. It excludes `ctd_label` and row metadata from feature inputs.

Sprint 4 model comparison should train exactly:

- `LogisticRegression`
- `RandomForestClassifier`
- `GradientBoostingClassifier`

All three should consume the same train/test split, preprocessing helper, target
definition, feature definitions, and primary metric.

## Leakage and Limitations

- The default split is course-compatible 80/20 stratified row splitting.
- The same compounds and diseases may appear in both train and test. This is a
  known leakage risk for graph-derived drug-disease rows.
- A future group-aware split by compound or disease would be scientifically
  stronger for generalization analysis, but it should be documented separately
  from the course-compatible default.
- The non-positive class means "not represented in this fragment after
  deterministic sampling"; absence of known relation is not evidence of clinical
  non-treatment or safety.
