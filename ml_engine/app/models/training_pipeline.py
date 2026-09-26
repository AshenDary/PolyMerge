"""Reproducible Sprint 4 training-only model comparison.

This module compares the three approved traditional classifiers using one
materialized set of training-only cross-validation folds. It deliberately does
not load the Sprint 3 test split, persist fitted estimators, or expose inference.
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
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import label_binarize

from app.data.ddinter_dataset import ALLOWED_LABELS, FEATURE_COLUMNS, TARGET_COLUMN
from app.data.preprocessing import build_preprocessing_pipeline, split_features_target


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRAIN_PATH = REPO_ROOT / "data" / "processed" / "sprint3" / "train.csv"
DEFAULT_CONTRACT_PATH = REPO_ROOT / "data" / "interim" / "sprint4" / "feature_contract.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "interim" / "sprint4" / "training_experiment.json"
RANDOM_SEED = 42
CV_FOLDS = 5
PRIMARY_METRIC = "macro_f1"


@dataclass(frozen=True)
class ModelSpec:
    """One approved model and its reproducible construction details."""

    name: str
    factory: Callable[[], BaseEstimator]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return repr(value)


def _package_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "scikit-learn", "scipy", "joblib")
    versions: dict[str, str] = {"python": platform.python_version()}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "unavailable"
    return versions


def _git_state() -> dict[str, Any]:
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


def _implementation_files() -> dict[str, str]:
    files = {
        "ml_engine/app/models/training_pipeline.py": Path(__file__).resolve(),
        "ml_engine/app/data/preprocessing.py": Path(
            build_preprocessing_pipeline.__code__.co_filename
        ).resolve(),
    }
    return {name: _sha256(path) for name, path in files.items()}


def approved_model_specs(random_seed: int = RANDOM_SEED) -> tuple[ModelSpec, ...]:
    """Return exactly the three classifiers approved for Sprint 4."""
    return (
        ModelSpec(
            "LogisticRegression",
            lambda: LogisticRegression(
                max_iter=1000,
                random_state=random_seed,
                solver="lbfgs",
            ),
        ),
        ModelSpec(
            "RandomForestClassifier",
            lambda: RandomForestClassifier(
                n_estimators=100,
                random_state=random_seed,
                n_jobs=1,
            ),
        ),
        ModelSpec(
            "HistGradientBoostingClassifier",
            lambda: HistGradientBoostingClassifier(
                learning_rate=0.1,
                max_iter=100,
                random_state=random_seed,
            ),
        ),
    )


def most_frequent_baseline() -> ModelSpec:
    """Return the context-only baseline; it is never eligible for selection."""
    return ModelSpec(
        "MostFrequentBaseline",
        lambda: DummyClassifier(strategy="most_frequent"),
    )


def build_model_pipeline(estimator: BaseEstimator) -> Pipeline:
    """Put preprocessing inside the estimator pipeline for fold-local fitting."""
    return Pipeline(
        steps=[
            ("preprocessing", build_preprocessing_pipeline()),
            ("classifier", estimator),
        ]
    )


def materialize_cv_folds(
    y: pd.Series,
    n_splits: int = CV_FOLDS,
    random_seed: int = RANDOM_SEED,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], str]:
    """Create one reusable fold set and a stable fingerprint of its indices."""
    splitter = StratifiedKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=random_seed,
    )
    placeholder = np.zeros(len(y), dtype=np.uint8)
    folds = [(train, validation) for train, validation in splitter.split(placeholder, y)]
    digest = hashlib.sha256()
    for train_indices, validation_indices in folds:
        digest.update(train_indices.astype("<i8", copy=False).tobytes())
        digest.update(b"|")
        digest.update(validation_indices.astype("<i8", copy=False).tobytes())
        digest.update(b";")
    return folds, digest.hexdigest()


def _fold_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "macro_precision": float(
            precision_score(y_true, y_pred, average="macro", zero_division=0)
        ),
        "macro_recall": float(
            recall_score(y_true, y_pred, average="macro", zero_division=0)
        ),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted")),
        "micro_f1": float(f1_score(y_true, y_pred, average="micro")),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def _metric_summary(fold_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metric_names = tuple(fold_results[0]["metrics"])
    summary: dict[str, dict[str, Any]] = {}
    for metric in metric_names:
        values = np.asarray(
            [fold["metrics"][metric] for fold in fold_results], dtype=float
        )
        summary[metric] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
            "per_fold": values.tolist(),
        }
    return summary


def _probability_metrics(
    y_true: pd.Series,
    probabilities: np.ndarray | None,
) -> dict[str, Any]:
    if probabilities is None:
        return {"macro_ovr_auroc": None, "macro_ovr_auprc": None}
    binary_targets = label_binarize(y_true, classes=list(ALLOWED_LABELS))
    try:
        auroc = roc_auc_score(
            binary_targets,
            probabilities,
            average="macro",
            multi_class="ovr",
        )
        auprc = average_precision_score(
            binary_targets,
            probabilities,
            average="macro",
        )
    except ValueError:
        return {"macro_ovr_auroc": None, "macro_ovr_auprc": None}
    return {
        "macro_ovr_auroc": float(auroc),
        "macro_ovr_auprc": float(auprc),
    }


def _model_version(
    model_name: str,
    estimator_name: str,
    parameters: dict[str, Any],
) -> str:
    payload = {
        "model_name": model_name,
        "estimator": estimator_name,
        "parameters": _json_safe(parameters),
        "preprocessing_sha256": _implementation_files()[
            "ml_engine/app/data/preprocessing.py"
        ],
        "scikit_learn_version": _package_versions()["scikit-learn"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{model_name}-v1-{digest}"


def evaluate_model(
    spec: ModelSpec,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    folds: Iterable[tuple[np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    """Evaluate one model on the supplied folds without touching held-out test data."""
    fold_list = list(folds)
    predictions = np.empty(len(y_train), dtype=object)
    probabilities = np.full((len(y_train), len(ALLOWED_LABELS)), np.nan, dtype=float)
    has_probabilities = True
    fold_results: list[dict[str, Any]] = []
    estimator_template = spec.factory()

    for fold_number, (fit_indices, validation_indices) in enumerate(fold_list, start=1):
        pipeline = build_model_pipeline(clone(estimator_template))
        x_fit = x_train.iloc[fit_indices]
        y_fit = y_train.iloc[fit_indices]
        x_validation = x_train.iloc[validation_indices]
        y_validation = y_train.iloc[validation_indices]
        pipeline.fit(x_fit, y_fit)
        fold_predictions = pipeline.predict(x_validation)
        predictions[validation_indices] = fold_predictions

        if hasattr(pipeline, "predict_proba"):
            fold_probabilities = pipeline.predict_proba(x_validation)
            class_positions = {
                label: position
                for position, label in enumerate(pipeline.classes_)
            }
            probabilities[validation_indices] = np.column_stack(
                [fold_probabilities[:, class_positions[label]] for label in ALLOWED_LABELS]
            )
        else:
            has_probabilities = False

        fold_results.append({
            "fold": fold_number,
            "fit_rows": int(len(fit_indices)),
            "validation_rows": int(len(validation_indices)),
            "metrics": _fold_metrics(y_validation, fold_predictions),
        })

    precision, recall, f1, support = precision_recall_fscore_support(
        y_train,
        predictions,
        labels=list(ALLOWED_LABELS),
        zero_division=0,
    )
    probability_metrics = _probability_metrics(
        y_train,
        probabilities if has_probabilities and np.isfinite(probabilities).all() else None,
    )
    classifier_name = (
        f"{estimator_template.__class__.__module__}."
        f"{estimator_template.__class__.__qualname__}"
    )
    parameters = _json_safe(estimator_template.get_params(deep=True))

    return {
        "name": spec.name,
        "model_version": _model_version(spec.name, classifier_name, parameters),
        "estimator": classifier_name,
        "parameters": parameters,
        "folds": fold_results,
        "metrics": _metric_summary(fold_results),
        "out_of_fold": {
            "confusion_matrix": confusion_matrix(
                y_train,
                predictions,
                labels=list(ALLOWED_LABELS),
            ).tolist(),
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
            **probability_metrics,
        },
    }


def load_training_data(
    train_path: Path = DEFAULT_TRAIN_PATH,
    contract_path: Path = DEFAULT_CONTRACT_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load and validate only the authoritative training split and feature contract."""
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    frame = pd.read_csv(train_path, low_memory=False)
    x_train, y_train = split_features_target(frame)

    if list(x_train.columns) != contract["features"]:
        raise ValueError("Training features do not match the Sprint 4 feature contract")
    if len(x_train.columns) != contract["feature_count"]:
        raise ValueError("Training feature count does not match the Sprint 4 contract")
    if len(frame) != contract["train_rows"]:
        raise ValueError("Training row count does not match the Sprint 4 contract")
    if set(y_train.unique()) != set(contract["classes"]):
        raise ValueError("Training labels do not match the Sprint 4 contract")
    if y_train.value_counts().to_dict() != contract["train_class_counts"]:
        raise ValueError("Training class counts do not match the Sprint 4 contract")
    return frame, contract


def _experiment_identity(identity_payload: dict[str, Any]) -> str:
    canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    return f"sprint4-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def run_training_experiment(
    train_path: Path = DEFAULT_TRAIN_PATH,
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    output_path: Path | None = DEFAULT_OUTPUT_PATH,
    *,
    n_splits: int = CV_FOLDS,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Run and optionally save the training-only Sprint 4 experiment."""
    frame, contract = load_training_data(train_path, contract_path)
    x_train, y_train = split_features_target(frame)
    folds, fold_fingerprint = materialize_cv_folds(y_train, n_splits, random_seed)
    approved_specs = approved_model_specs(random_seed)
    baseline_spec = most_frequent_baseline()
    package_versions = _package_versions()
    implementation_files = _implementation_files()

    identity_payload = {
        "train_sha256": _sha256(train_path),
        "contract_sha256": _sha256(contract_path),
        "random_seed": random_seed,
        "n_splits": n_splits,
        "fold_fingerprint": fold_fingerprint,
        "package_versions": package_versions,
        "implementation_files": implementation_files,
        "models": [
            {
                "name": spec.name,
                "parameters": _json_safe(spec.factory().get_params(deep=True)),
            }
            for spec in approved_specs
        ],
    }
    experiment_id = _experiment_identity(identity_payload)
    baseline_result = evaluate_model(baseline_spec, x_train, y_train, folds)
    model_results = [
        evaluate_model(spec, x_train, y_train, folds) for spec in approved_specs
    ]
    selected = max(
        model_results,
        key=lambda result: result["metrics"][PRIMARY_METRIC]["mean"],
    )

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "DDI severity classification for canonical unordered drug pairs",
        "research_use_only": True,
        "primary_metric": PRIMARY_METRIC,
        "selection": {
            "eligible_models": [spec.name for spec in approved_specs],
            "selected_model": selected["name"],
            "selected_validation_macro_f1_mean": selected["metrics"][PRIMARY_METRIC]["mean"],
            "selected_validation_macro_f1_std": selected["metrics"][PRIMARY_METRIC]["std"],
            "baseline_is_selection_eligible": False,
        },
        "runtime": {
            "packages": package_versions,
            "git": _git_state(),
            "implementation_files_sha256": implementation_files,
            "random_seeds": {
                "cross_validation": random_seed,
                **{spec.name: random_seed for spec in approved_specs},
            },
        },
        "training_data": {
            "path": train_path.relative_to(REPO_ROOT).as_posix(),
            "sha256": identity_payload["train_sha256"],
            "rows": int(len(frame)),
            "feature_count": int(len(FEATURE_COLUMNS)),
            "target": TARGET_COLUMN,
            "class_counts": {
                label: int(count) for label, count in y_train.value_counts().items()
            },
            "feature_contract_path": contract_path.relative_to(REPO_ROOT).as_posix(),
            "feature_contract_sha256": identity_payload["contract_sha256"],
            "provenance": contract["provenance"],
        },
        "test_isolation": {
            "status": "untouched",
            "test_split_loaded": False,
            "test_split_used_for_preprocessing": False,
            "test_split_used_for_tuning": False,
            "test_split_used_for_selection": False,
            "reserved_for": "Sprint 5 final evaluation",
        },
        "preprocessing": {
            "implementation": "ml_engine/app/data/preprocessing.py",
            "fit_scope": "Each training CV fold only",
            "numeric_imputation": "median",
            "scaling": "StandardScaler",
            "class_weighting": None,
            "resampling": None,
        },
        "cross_validation": {
            "strategy": "StratifiedKFold",
            "n_splits": n_splits,
            "shuffle": True,
            "random_seed": random_seed,
            "fold_fingerprint_sha256": fold_fingerprint,
            "identical_folds_for_all_models": True,
        },
        "baseline": baseline_result,
        "models": model_results,
        "serving": {
            "status": "inactive",
            "model_artifact_persisted": False,
            "inference_endpoint_enabled": False,
            "candidate_scoring_integration_enabled": False,
            "mlStatus": "not_applied",
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report
