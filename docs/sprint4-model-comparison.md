# Sprint 4 Model Comparison Report

## Experiment

- Dataset: `data/processed/sprint3/train.csv` (104,337 canonical drug pairs)
- Target: `ddi_severity`
- Classes: Major, Moderate, Minor
- Features: 55 numeric symmetric pair features
- Cross-validation: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`
- Fold fingerprint: `fae1f6e6165e5d065540990eb4f3fda8f9c42a79d9609b0efecb4a16021896a3`
- Primary metric: mean validation Macro F1
- Preprocessing: median imputation and `StandardScaler`, fitted separately on each training fold
- Random state: 42
- Clean commit: `81aa3d413dcd45d5110b7b7aef6cb77307423897`
- Canonical artifact: `data/interim/sprint4/training_experiment.json`

The target labels come from DDInter 2.0. PubChem and RDKit provide molecular
features, while Hetionet provides graph context. Hetionet `CrC` is compound
resemblance context and is not DDI evidence. Unknown labels are excluded, and
unlabeled pairs are not converted into synthetic negatives.

## Model Parameters

These are fixed Sprint 4 comparison parameters, not tuned or "best"
hyperparameters. No grid search, randomized search, or other hyperparameter
tuning was performed.

| Model | Fixed parameters |
|---|---|
| LogisticRegression | `max_iter=1000`, `solver="lbfgs"`, `random_state=42`, `class_weight=None` |
| RandomForestClassifier | `n_estimators=100`, `max_features="sqrt"`, `n_jobs=1`, `random_state=42`, `class_weight=None` |
| HistGradientBoostingClassifier | `max_iter=100`, `learning_rate=0.1`, `random_state=42`, `class_weight=None` |

All other estimator parameters retain the scikit-learn 1.4.0 defaults recorded
in the canonical artifact.

## Validation Results

All class metrics, AUROC, and AUPRC below are computed from out-of-fold
predictions on the training split. AUROC and AUPRC are macro one-vs-rest values.

| Model | Mean Macro F1 | Std Macro F1 | Major F1 | Moderate F1 | Minor F1 | Macro AUROC | Macro AUPRC |
|---|---:|---:|---:|---:|---:|---:|---:|
| LogisticRegression | 0.290759 | 0.001509 | 0.013229 | 0.851459 | 0.007602 | 0.620185 | 0.402097 |
| RandomForestClassifier | 0.506086 | 0.005695 | 0.341365 | 0.869865 | 0.307134 | 0.787447 | 0.618778 |
| HistGradientBoostingClassifier | 0.407769 | 0.005931 | 0.211538 | 0.860662 | 0.151255 | 0.739625 | 0.545643 |

## Baseline

The `MostFrequentBaseline` is non-selection-eligible. It achieved validation
Macro F1 `0.283800 +/- 0.000004`, Major F1 `0.000000`, Moderate F1 `0.851401`,
Minor F1 `0.000000`, macro AUROC `0.500000`, and macro AUPRC `0.333333`.

## Selected Model

`RandomForestClassifier` advances to Sprint 5 because it has the highest mean
validation Macro F1 among the three eligible models. The untouched Sprint 3
test split was not loaded or evaluated. Sprint 5 owns final test evaluation,
model persistence, and any later integration.

## Figures

Sprint 4 does not require or publish figures. The canonical JSON artifact
contains per-fold scores, out-of-fold per-class metrics, and confusion matrices
for reproducible downstream reporting without another training run.

## Limitations

- The Moderate class dominates the dataset; the Minor class is underrepresented.
- The primary pair split contains mostly drugs already represented in training,
  so it mainly measures new-pair generalization rather than drug cold start.
- Hetionet graph coverage remains sparse, and missing coverage is not known zero evidence.
- These cross-validation results are research evidence, not clinical validation.
- The test set remains untouched and reserved for Sprint 5 final evaluation.
- No hyperparameter tuning was performed in Sprint 4.

## Reproducibility

Run `python3 scripts/run_sprint4_training.py` from the repository root. The
canonical implementation is `ml_engine/app/models/training_pipeline.py`; it
does not persist a trained estimator or activate model serving. Current
candidate responses remain `mlStatus: "not_applied"`.

**Status**: Implemented / Ready for Sprint 5
