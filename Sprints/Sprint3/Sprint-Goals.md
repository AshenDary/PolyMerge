# Sprint 3 - Dataset, EDA & Traditional Feature Engineering

## Goal

Prepare a supervised traditional ML dataset while keeping deterministic KG retrieval clearly separate from predictions.

## Planned Supervised Task

- Preferred: drug-pair interaction classification using a legitimate DDI dataset.
- Fallback: drug-disease treatment relationship classification from a documented Hetionet-derived dataset.

## Shared Tasks

- [ ] Finalize supervised problem, dataset, target variable, and negative-label strategy
- [ ] Document dataset source, license, and limitations
- [ ] Build data dictionary
- [ ] Inspect missing values, duplicates, target/class distribution, and outliers
- [ ] Create at least five meaningful EDA visualizations
- [ ] Create leakage-safe preprocessing
- [ ] Derive traditional tabular features from graph and compound data
- [ ] Prepare reproducible train/test data

## Definition of Done

- [ ] Dataset and target choice are documented
- [ ] EDA outputs are reproducible
- [ ] Train/test split is saved or reproducibly generated
- [ ] Graph evidence remains separate from future traditional ML predictions
- [ ] No neural-network or graph-embedding model is introduced
