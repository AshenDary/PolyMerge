# Sprint 4 Implementation Summary

Sprint 4 is implemented through one canonical training-only experiment:

- Implementation: `ml_engine/app/models/training_pipeline.py`
- Runner: `scripts/run_sprint4_training.py`
- Artifact: `data/interim/sprint4/training_experiment.json`
- Results: `docs/sprint4-model-comparison.md`

The experiment compares exactly `LogisticRegression`,
`RandomForestClassifier`, and `HistGradientBoostingClassifier` using one
materialized five-fold stratified split of the Sprint 3 training data. Fold-local
preprocessing uses median imputation and standard scaling. Mean Macro F1 is the
sole selection criterion; the most-frequent baseline is context only.

The clean run selected `RandomForestClassifier` with validation Macro F1
`0.506086 +/- 0.005695`. No hyperparameter tuning occurred. The test split was
not loaded, no fitted estimator was saved, no prediction endpoint was enabled,
and candidate responses remain `mlStatus: "not_applied"`.

Sprint 4 figures are not part of the deliverable. Per-fold metrics, out-of-fold
per-class metrics, and confusion matrices are retained in the canonical JSON
artifact for reproducible reporting without a second training implementation.

**Status**: Implemented / Ready for Sprint 5
