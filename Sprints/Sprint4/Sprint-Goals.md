# Sprint 4 - Traditional Supervised ML Model Comparison

## Goal

Train and compare the course-required traditional supervised models using the
Sprint 3 dataset, split, preprocessing helper, and target definition.

## Shared Tasks

- [x] Train `LogisticRegression`
- [x] Train `RandomForestClassifier`
- [x] Train `HistGradientBoostingClassifier`
- [x] Use `data/processed/sprint3/train.csv` for model comparison
- [x] Keep `data/processed/sprint3/test.csv` untouched for Sprint 5
- [x] Use `ml_engine/app/data/preprocessing.py`
- [x] Fit preprocessing on training folds only
- [x] Use macro F1 as the same primary metric for all three models
- [x] Document pair-split drug overlap and cold-start limitations
- [x] Keep the test split out of feature selection, tuning, and model selection
- [x] Report a most-frequent baseline for context only
- [x] Use fixed unweighted parameters with no resampling or tuning

## Important Constraint

DDInter 2.0 is the label source. Hetionet `CrC` is resemblance context only.
Unknown is not a supervised class, and no missing pair is a safe negative.
`GradientBoostingClassifier` is only a course-compatibility fallback.

## Outcome

`RandomForestClassifier` was selected by mean five-fold validation Macro F1.
The canonical artifact is `data/interim/sprint4/training_experiment.json`.
Model serving remains inactive and Sprint 5 owns final test evaluation.

**Status**: Implemented / Ready for Sprint 5
