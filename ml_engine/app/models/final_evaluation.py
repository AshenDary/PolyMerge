"""Sprint 5 final Random Forest evaluation and artifact freeze.

This module owns the one official predictive evaluation on the untouched Sprint
3 primary test split. Unit tests should use synthetic fixtures; do not call
``run_final_evaluation`` against the real test split from automated tests.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import label_binarize

from app.data.ddinter_dataset import ALLOWED_LABELS, FEATURE_COLUMNS, TARGET_COLUMN
from app.data.preprocessing import build_preprocessing_pipeline, split_features_target


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRAIN_PATH = REPO_ROOT / "data" / "processed" / "sprint3" / "train.csv"
DEFAULT_TEST_PATH = REPO_ROOT / "data" / "processed" / "sprint3" / "test.csv"
DEFAULT_FEATURE_CONTRACT_PATH = (
    REPO_ROOT / "data" / "interim" / "sprint4" / "feature_contract.json"
)
DEFAULT_SPRINT4_EXPERIMENT_PATH = (
    REPO_ROOT / "data" / "interim" / "sprint4" / "training_experiment.json"
)
DEFAULT_METADATA_PATH = REPO_ROOT / "data" / "interim" / "sprint5" / "final_model_evaluation.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "sprint5-final-model-evaluation.md"
DEFAULT_ARTIFACT_PATH = REPO_ROOT / "models" / "sprint5" / "random_forest_ddi_pipeline.joblib"

EXPECTED_TRAIN_ROWS = 104_337
EXPECTED_TEST_ROWS = 26_085
EXPECTED_FEATURE_COUNT = 55
EXPECTED_TRAIN_SHA256 = "76db357e897b327dfd921a4e3d3e7f2a6c19999be78d2341534fe158cdf4b9c3"
EXPECTED_FEATURE_CONTRACT_SHA256 = "a3adc02c91e1af0cf47d978c3c87d47b22f696edc7f797dc24a14ad246328efa"
EXPECTED_PREPROCESSING_SHA256 = "1ffc9a78941e036e6af99e34a3d310a4bb76235ae54456e9e66d44342eb0a17f"
SPRINT4_VALIDATION_MACRO_F1_MEAN = 0.5060862357426106
SPRINT4_VALIDATION_MACRO_F1_STD = 0.005694734206099396
FROZEN_RF_PARAMETERS: dict[str, Any] = {
    "n_estimators": 100,
    "max_features": "sqrt",
    "n_jobs": 1,
    "random_state": 42,
    "class_weight": None,
}


@dataclass(frozen=True)
class FinalEvaluationPaths:
    train_path: Path = DEFAULT_TRAIN_PATH
    test_path: Path = DEFAULT_TEST_PATH
    feature_contract_path: Path = DEFAULT_FEATURE_CONTRACT_PATH
    sprint4_experiment_path: Path = DEFAULT_SPRINT4_EXPERIMENT_PATH
    artifact_path: Path = DEFAULT_ARTIFACT_PATH
    metadata_path: Path = DEFAULT_METADATA_PATH
    report_path: Path = DEFAULT_REPORT_PATH


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return repr(value)


def package_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "scikit-learn", "scipy", "joblib")
    versions: dict[str, str] = {"python": platform.python_version()}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "unavailable"
    return versions


def git_state() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_dirty": None}
    return {
        "commit": commit.stdout.strip() or None,
        "working_tree_dirty": bool(status.stdout.strip()),
    }


def build_final_pipeline() -> Pipeline:
    classifier = RandomForestClassifier(**FROZEN_RF_PARAMETERS)
    return Pipeline(
        steps=[
            ("preprocessing", build_preprocessing_pipeline()),
            ("classifier", classifier),
        ]
    )


def deterministic_model_version(
    *,
    train_sha256: str,
    feature_contract_sha256: str,
    preprocessing_sha256: str,
    versions: dict[str, str],
) -> str:
    payload = {
        "model_type": "sklearn.ensemble.RandomForestClassifier",
        "parameters": FROZEN_RF_PARAMETERS,
        "feature_contract_sha256": feature_contract_sha256,
        "preprocessing_sha256": preprocessing_sha256,
        "train_dataset_sha256": train_sha256,
        "scikit_learn_version": versions["scikit-learn"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"RandomForestClassifier-sprint5-v1-{digest}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_no_existing_final_outputs(paths: FinalEvaluationPaths) -> None:
    existing = [
        path
        for path in (paths.metadata_path, paths.report_path)
        if path.exists()
    ]
    if existing:
        joined = ", ".join(relative(path) for path in existing)
        raise FileExistsError(
            "Final Sprint 5 evaluation output already exists; refusing to rerun "
            f"official test scoring: {joined}"
        )


def validate_sprint4_selection(sprint4_experiment: dict[str, Any]) -> dict[str, Any]:
    selection = sprint4_experiment.get("selection", {})
    if selection.get("selected_model") != "RandomForestClassifier":
        raise ValueError("Sprint 4 selected model is not RandomForestClassifier")

    candidates = [
        result
        for result in sprint4_experiment.get("models", [])
        if result.get("name") == "RandomForestClassifier"
    ]
    if len(candidates) != 1:
        raise ValueError("Expected exactly one Sprint 4 RandomForestClassifier result")
    rf_result = candidates[0]
    parameters = rf_result.get("parameters", {})
    for name, expected in FROZEN_RF_PARAMETERS.items():
        if parameters.get(name) != expected:
            raise ValueError(f"Sprint 4 RF parameter drifted: {name}")

    macro_f1 = rf_result.get("metrics", {}).get("macro_f1", {})
    if not np.isclose(macro_f1.get("mean"), SPRINT4_VALIDATION_MACRO_F1_MEAN):
        raise ValueError("Sprint 4 validation Macro F1 mean drifted")
    if not np.isclose(macro_f1.get("std"), SPRINT4_VALIDATION_MACRO_F1_STD):
        raise ValueError("Sprint 4 validation Macro F1 std drifted")
    return rf_result


def validate_preflight(
    train: pd.DataFrame,
    test: pd.DataFrame,
    contract: dict[str, Any],
    *,
    train_sha256: str | None = None,
    feature_contract_sha256: str | None = None,
    preprocessing_sha256: str | None = None,
) -> dict[str, Any]:
    x_train, y_train = split_features_target(train)
    x_test, y_test = split_features_target(test)
    allowed = list(ALLOWED_LABELS)

    if len(train) != EXPECTED_TRAIN_ROWS:
        raise ValueError(f"Unexpected train row count: {len(train)}")
    if len(test) != EXPECTED_TEST_ROWS:
        raise ValueError(f"Unexpected test row count: {len(test)}")
    if list(x_train.columns) != FEATURE_COLUMNS or list(x_test.columns) != FEATURE_COLUMNS:
        raise ValueError("Train/test feature schema does not match FEATURE_COLUMNS")
    if len(FEATURE_COLUMNS) != EXPECTED_FEATURE_COUNT:
        raise ValueError("FEATURE_COLUMNS count drifted from 55")
    if contract.get("features") != FEATURE_COLUMNS:
        raise ValueError("Feature contract differs from FEATURE_COLUMNS")
    if contract.get("feature_count") != EXPECTED_FEATURE_COUNT:
        raise ValueError("Feature contract count drifted from 55")
    if contract.get("target") != TARGET_COLUMN or TARGET_COLUMN != "ddi_severity":
        raise ValueError("Target column drifted from ddi_severity")
    if contract.get("classes") != allowed:
        raise ValueError("Feature contract classes drifted")
    if set(y_train.dropna().unique()) != set(allowed):
        raise ValueError("Training target classes differ from allowed labels")
    if set(y_test.dropna().unique()) != set(allowed):
        raise ValueError("Test target classes differ from allowed labels")
    if y_train.isna().any() or y_test.isna().any():
        raise ValueError("Target contains missing labels")
    if "Unknown" in set(y_train.astype(str)) or "Unknown" in set(y_test.astype(str)):
        raise ValueError("Unknown labels are not allowed in final evaluation")
    if "pair_id" in train.columns and "pair_id" in test.columns:
        train_pairs = set(train["pair_id"])
        test_pairs = set(test["pair_id"])
        if train_pairs & test_pairs:
            raise ValueError("Primary test split contains pairs from training")
    if train_sha256 is not None and train_sha256 != EXPECTED_TRAIN_SHA256:
        raise ValueError("Training dataset SHA-256 differs from the expected Sprint 4 hash")
    if (
        feature_contract_sha256 is not None
        and feature_contract_sha256 != EXPECTED_FEATURE_CONTRACT_SHA256
    ):
        raise ValueError("Feature-contract SHA-256 differs from expected Sprint 4 hash")
    if preprocessing_sha256 is not None and preprocessing_sha256 != EXPECTED_PREPROCESSING_SHA256:
        raise ValueError("Preprocessing SHA-256 differs from expected Sprint 4 hash")

    return {
        "training_rows": int(len(train)),
        "test_rows": int(len(test)),
        "feature_count": len(FEATURE_COLUMNS),
        "target": TARGET_COLUMN,
        "classes": allowed,
        "train_class_counts": {
            label: int(count) for label, count in y_train.value_counts().sort_index().items()
        },
        "test_class_counts": {
            label: int(count) for label, count in y_test.value_counts().sort_index().items()
        },
    }


def validate_pipeline_shape(pipeline: Pipeline) -> None:
    if list(pipeline.named_steps) != ["preprocessing", "classifier"]:
        raise ValueError("Final pipeline must contain preprocessing and classifier steps")
    classifier = pipeline.named_steps["classifier"]
    if not isinstance(classifier, RandomForestClassifier):
        raise TypeError("Final classifier is not RandomForestClassifier")
    for name, expected in FROZEN_RF_PARAMETERS.items():
        if classifier.get_params()[name] != expected:
            raise ValueError(f"Final RF parameter mismatch: {name}")


def final_test_metrics(
    pipeline: Pipeline,
    x_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict[str, Any]:
    predictions = pipeline.predict(x_test)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test,
        predictions,
        labels=list(ALLOWED_LABELS),
        zero_division=0,
    )
    metrics: dict[str, Any] = {
        "macro_f1": float(f1_score(y_test, predictions, average="macro")),
        "weighted_f1": float(f1_score(y_test, predictions, average="weighted")),
        "micro_f1": float(f1_score(y_test, predictions, average="micro")),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "macro_ovr_auroc": None,
        "macro_ovr_auprc": None,
    }
    if hasattr(pipeline, "predict_proba"):
        probabilities = pipeline.predict_proba(x_test)
        class_positions = {
            label: position for position, label in enumerate(pipeline.classes_)
        }
        ordered_probabilities = np.column_stack(
            [probabilities[:, class_positions[label]] for label in ALLOWED_LABELS]
        )
        binary_targets = label_binarize(y_test, classes=list(ALLOWED_LABELS))
        try:
            metrics["macro_ovr_auroc"] = float(
                roc_auc_score(
                    binary_targets,
                    ordered_probabilities,
                    average="macro",
                    multi_class="ovr",
                )
            )
            metrics["macro_ovr_auprc"] = float(
                average_precision_score(
                    binary_targets,
                    ordered_probabilities,
                    average="macro",
                )
            )
        except ValueError:
            metrics["macro_ovr_auroc"] = None
            metrics["macro_ovr_auprc"] = None

    return {
        **metrics,
        "class_order": list(ALLOWED_LABELS),
        "per_class": {
            label: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(ALLOWED_LABELS)
        },
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions,
            labels=list(ALLOWED_LABELS),
        ).tolist(),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def render_report(metadata: dict[str, Any]) -> str:
    metrics = metadata["final_test_metrics"]
    per_class = metadata["per_class_metrics"]
    confusion = metadata["confusion_matrix"]
    return f"""# Sprint 5 Final Model Evaluation

## Objective

Perform the one-time final evaluation of the selected Sprint 4 Random Forest on the untouched Sprint 3 primary test split and freeze one complete preprocessing/classifier pipeline for downstream serving integration.

## Sprint 4 Selection

Sprint 4 selected `RandomForestClassifier` using training-only 5-fold `StratifiedKFold` and mean validation Macro F1. The selected validation Macro F1 was `{metadata["sprint4_validation_macro_f1_mean"]:.6f} +/- {metadata["sprint4_validation_macro_f1_std"]:.6f}`. No hyperparameter tuning occurred.

## Frozen Random Forest Configuration

```json
{json.dumps(metadata["parameters"], indent=2, sort_keys=True)}
```

## Dataset Contract

- Train rows: {metadata["training_rows"]}
- Test rows: {metadata["test_rows"]}
- Feature count: {metadata["feature_count"]}
- Target: `{metadata["target"]}`
- Classes: {", ".join(metadata["classes"])}
- Train SHA-256: `{metadata["training_dataset_sha256"]}`
- Test SHA-256: `{metadata["test_dataset_sha256"]}`
- Feature-contract SHA-256: `{metadata["feature_contract_sha256"]}`
- Preprocessing SHA-256: `{metadata["preprocessing_sha256"]}`

## Final Evaluation Procedure

The final pipeline contains `preprocessing` and `classifier` steps. Preprocessing was fitted only as part of `Pipeline.fit` on the full Sprint 3 training split. The test set was used for final evaluation only. It was not used for training, model selection, hyperparameter tuning, feature selection, or threshold tuning.

## Final Test Results

- Macro F1: {metrics["macro_f1"]:.6f}
- Accuracy: {metrics["accuracy"]:.6f}
- Balanced accuracy: {metrics["balanced_accuracy"]:.6f}
- Weighted F1: {metrics["weighted_f1"]:.6f}
- Micro F1: {metrics["micro_f1"]:.6f}
- Macro AUROC: {metrics["macro_ovr_auroc"] if metrics["macro_ovr_auroc"] is not None else "Unavailable"}
- Macro AUPRC: {metrics["macro_ovr_auprc"] if metrics["macro_ovr_auprc"] is not None else "Unavailable"}

## Per-Class Results

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Major | {per_class["Major"]["precision"]:.6f} | {per_class["Major"]["recall"]:.6f} | {per_class["Major"]["f1"]:.6f} | {per_class["Major"]["support"]} |
| Moderate | {per_class["Moderate"]["precision"]:.6f} | {per_class["Moderate"]["recall"]:.6f} | {per_class["Moderate"]["f1"]:.6f} | {per_class["Moderate"]["support"]} |
| Minor | {per_class["Minor"]["precision"]:.6f} | {per_class["Minor"]["recall"]:.6f} | {per_class["Minor"]["f1"]:.6f} | {per_class["Minor"]["support"]} |

## Confusion Matrix

Rows are true labels and columns are predicted labels, ordered as Major, Moderate, Minor.

```text
{confusion[0]}
{confusion[1]}
{confusion[2]}
```

## Validation vs Test

Final test Macro F1 minus Sprint 4 validation mean Macro F1 is `{metadata["validation_to_test_gap"]:.6f}`. This validation-to-test generalization gap is reported only for interpretation; it was not used to retrain, tune, switch models, modify features, modify preprocessing, or adjust thresholds.

## Model Artifact

- Path: `{metadata["artifact_path"]}`
- Format: joblib-serialized sklearn `Pipeline`
- SHA-256: `{metadata["artifact_sha256"]}`
- Size: {metadata["artifact_size_bytes"]} bytes
- Model version: `{metadata["model_version"]}`

## Reproducibility

- Metadata artifact: `{metadata["metadata_path"]}`
- Source commit: `{metadata["source_commit"]}`
- Python: {metadata["python_version"]}
- NumPy: {metadata["numpy_version"]}
- pandas: {metadata["pandas_version"]}
- scikit-learn: {metadata["scikit_learn_version"]}
- SciPy: {metadata["scipy_version"]}
- joblib: {metadata["joblib_version"]}

## Limitations

This is research classification performance, not clinical validation. The model predicts DDInter severity labels for research decision support and is not a clinical safety, contraindication, prescribing, efficacy, or compatibility guarantee.

## Handoff to Issue #42

Issue #42 should load the full joblib pipeline artifact and provide exactly the 55 approved feature columns in the documented order. The artifact includes preprocessing, outputs classes in the explicit order Major, Moderate, Minor, and should fail closed if the artifact is unavailable or the input schema is invalid.
"""


def run_final_evaluation(paths: FinalEvaluationPaths = FinalEvaluationPaths()) -> dict[str, Any]:
    assert_no_existing_final_outputs(paths)
    contract = load_json(paths.feature_contract_path)
    sprint4_experiment = load_json(paths.sprint4_experiment_path)
    rf_sprint4_result = validate_sprint4_selection(sprint4_experiment)

    train_sha256 = sha256_file(paths.train_path)
    test_sha256 = sha256_file(paths.test_path)
    feature_contract_sha256 = sha256_file(paths.feature_contract_path)
    preprocessing_sha256 = sha256_file(Path(build_preprocessing_pipeline.__code__.co_filename))

    train = pd.read_csv(paths.train_path, low_memory=False)
    test = pd.read_csv(paths.test_path, low_memory=False)
    preflight = validate_preflight(
        train,
        test,
        contract,
        train_sha256=train_sha256,
        feature_contract_sha256=feature_contract_sha256,
        preprocessing_sha256=preprocessing_sha256,
    )

    x_train, y_train = split_features_target(train)
    x_test, y_test = split_features_target(test)
    pipeline = build_final_pipeline()
    validate_pipeline_shape(pipeline)
    pipeline.fit(x_train, y_train)
    metrics = final_test_metrics(pipeline, x_test, y_test)

    paths.artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, paths.artifact_path)
    artifact_sha256 = sha256_file(paths.artifact_path)
    artifact_size = paths.artifact_path.stat().st_size
    versions = package_versions()
    model_version = deterministic_model_version(
        train_sha256=train_sha256,
        feature_contract_sha256=feature_contract_sha256,
        preprocessing_sha256=preprocessing_sha256,
        versions=versions,
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    git = git_state()
    run_identity = {
        "timestamp": timestamp,
        "model_version": model_version,
        "test_dataset_sha256": test_sha256,
        "artifact_sha256": artifact_sha256,
    }
    evaluation_run_id = (
        "sprint5-final-"
        + hashlib.sha256(
            json.dumps(run_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
    )
    metadata: dict[str, Any] = {
        "schema_version": "1.0.0",
        "sprint": "Sprint 5",
        "issue": "#40",
        "task": "Final Random Forest Evaluation & Model Artifact Freeze",
        "model_name": "RandomForestClassifier",
        "model_type": "sklearn.ensemble.RandomForestClassifier",
        "model_version": model_version,
        "artifact_path": relative(paths.artifact_path),
        "artifact_format": "joblib",
        "artifact_sha256": artifact_sha256,
        "artifact_size_bytes": artifact_size,
        "parameters": FROZEN_RF_PARAMETERS,
        "feature_count": preflight["feature_count"],
        "features": FEATURE_COLUMNS,
        "feature_contract_path": relative(paths.feature_contract_path),
        "target": TARGET_COLUMN,
        "classes": list(ALLOWED_LABELS),
        "training_rows": preflight["training_rows"],
        "test_rows": preflight["test_rows"],
        "training_dataset_path": relative(paths.train_path),
        "test_dataset_path": relative(paths.test_path),
        "training_dataset_sha256": train_sha256,
        "test_dataset_sha256": test_sha256,
        "feature_contract_sha256": feature_contract_sha256,
        "preprocessing_sha256": preprocessing_sha256,
        "source_commit": git["commit"],
        "evaluation_source_commit": git["commit"],
        "git_working_tree_dirty": git["working_tree_dirty"],
        "python_version": versions["python"],
        "numpy_version": versions["numpy"],
        "pandas_version": versions["pandas"],
        "scikit_learn_version": versions["scikit-learn"],
        "scipy_version": versions["scipy"],
        "joblib_version": versions["joblib"],
        "sprint4_experiment_path": relative(paths.sprint4_experiment_path),
        "sprint4_selected_model_version": rf_sprint4_result.get("model_version"),
        "sprint4_validation_macro_f1_mean": SPRINT4_VALIDATION_MACRO_F1_MEAN,
        "sprint4_validation_macro_f1_std": SPRINT4_VALIDATION_MACRO_F1_STD,
        "final_test_metrics": {
            key: metrics[key]
            for key in (
                "macro_f1",
                "accuracy",
                "balanced_accuracy",
                "weighted_f1",
                "micro_f1",
                "macro_ovr_auroc",
                "macro_ovr_auprc",
            )
        },
        "per_class_metrics": metrics["per_class"],
        "confusion_matrix": metrics["confusion_matrix"],
        "class_order": metrics["class_order"],
        "validation_to_test_gap": (
            metrics["macro_f1"] - SPRINT4_VALIDATION_MACRO_F1_MEAN
        ),
        "evaluation_timestamp_utc": timestamp,
        "evaluation_run_id": evaluation_run_id,
        "metadata_path": relative(paths.metadata_path),
        "report_path": relative(paths.report_path),
        "final_test_evaluation": True,
        "official_final_test_evaluation_count": 1,
        "test_used_for_training": False,
        "test_used_for_tuning": False,
        "test_used_for_selection": False,
        "test_used_for_threshold_selection": False,
        "preprocessing_fit_scope": "Full Sprint 3 train.csv only via sklearn Pipeline.fit",
        "research_use_only": True,
        "serving_integration": {
            "implemented_in_issue_40": False,
            "handoff_issue": "#42",
            "preprocessing_included_in_artifact": True,
            "expected_input_schema": FEATURE_COLUMNS,
            "output_classes": list(ALLOWED_LABELS),
            "unavailable_artifact_behavior": "fail closed; do not fabricate predictions",
        },
    }
    write_json(paths.metadata_path, metadata)
    paths.report_path.parent.mkdir(parents=True, exist_ok=True)
    paths.report_path.write_text(render_report(metadata), encoding="utf-8")
    return metadata
