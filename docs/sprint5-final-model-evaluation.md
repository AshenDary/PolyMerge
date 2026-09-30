# Sprint 5 Final Model Evaluation

## Objective

Perform the one-time final evaluation of the selected Sprint 4 Random Forest on the untouched Sprint 3 primary test split and freeze one complete preprocessing/classifier pipeline for downstream serving integration.

## Sprint 4 Selection

Sprint 4 selected `RandomForestClassifier` using training-only 5-fold `StratifiedKFold` and mean validation Macro F1. The selected validation Macro F1 was `0.506086 +/- 0.005695`. No hyperparameter tuning occurred.

## Frozen Random Forest Configuration

```json
{
  "class_weight": null,
  "max_features": "sqrt",
  "n_estimators": 100,
  "n_jobs": 1,
  "random_state": 42
}
```

## Dataset Contract

- Train rows: 104337
- Test rows: 26085
- Feature count: 55
- Target: `ddi_severity`
- Classes: Major, Moderate, Minor
- Train SHA-256: `76db357e897b327dfd921a4e3d3e7f2a6c19999be78d2341534fe158cdf4b9c3`
- Test SHA-256: `4a9ea90c5e198ebc815a9aa078caec22d9e418bcdfba1dedadff467ef87d0ab7`
- Feature-contract SHA-256: `a3adc02c91e1af0cf47d978c3c87d47b22f696edc7f797dc24a14ad246328efa`
- Preprocessing SHA-256: `1ffc9a78941e036e6af99e34a3d310a4bb76235ae54456e9e66d44342eb0a17f`

## Final Evaluation Procedure

The final pipeline contains `preprocessing` and `classifier` steps. Preprocessing was fitted only as part of `Pipeline.fit` on the full Sprint 3 training split. The test set was used for final evaluation only. It was not used for training, model selection, hyperparameter tuning, feature selection, or threshold tuning.

## Final Test Results

- Macro F1: 0.524630
- Accuracy: 0.787349
- Balanced accuracy: 0.475467
- Weighted F1: 0.740851
- Micro F1: 0.787349
- Macro AUROC: 0.7987927112157346
- Macro AUPRC: 0.6324678883126454

## Per-Class Results

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Major | 0.774956 | 0.243730 | 0.370831 | 5383 |
| Moderate | 0.786886 | 0.980036 | 0.872904 | 19335 |
| Minor | 0.890675 | 0.202634 | 0.330155 | 1367 |

## Confusion Matrix

Rows are true labels and columns are predicted labels, ordered as Major, Moderate, Minor.

```text
[1312, 4067, 4]
[356, 18949, 30]
[25, 1065, 277]
```

## Validation vs Test

Final test Macro F1 minus Sprint 4 validation mean Macro F1 is `0.018544`. This validation-to-test generalization gap is reported only for interpretation; it was not used to retrain, tune, switch models, modify features, modify preprocessing, or adjust thresholds.

## Model Artifact

- Path: `models/sprint5/random_forest_ddi_pipeline.joblib`
- Format: joblib-serialized sklearn `Pipeline`
- SHA-256: `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`
- Size: 251404304 bytes
- Model version: `RandomForestClassifier-sprint5-v1-65e9834666ad19c5`

The approximately 240 MB joblib binary is intentionally ignored and is not
stored in Git. The repository stores the evaluation metadata and this report so
the expected artifact can be identified and verified by version and checksum.

## Reproducibility

- Metadata artifact: `data/interim/sprint5/final_model_evaluation.json`
- Source commit: `827fbc88987efa5c8fbe9dd7422745ec6adeb7ae`
- Python: 3.9.6
- NumPy: 1.26.4
- pandas: 2.2.0
- scikit-learn: 1.4.0
- SciPy: 1.13.1
- joblib: 1.5.3

## Limitations

This is research classification performance, not clinical validation. The model predicts DDInter severity labels for research decision support and is not a clinical safety, contraindication, prescribing, efficacy, or compatibility guarantee.

## Handoff to Issue #42

Issue #42 should load the full joblib pipeline artifact and provide exactly the 55 approved feature columns in the documented order. The artifact includes preprocessing, outputs classes in the explicit order Major, Moderate, Minor, and should fail closed if the artifact is unavailable or the input schema is invalid.
