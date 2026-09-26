from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline

from app.data.ddinter_dataset import FEATURE_COLUMNS
from app.models import training_pipeline
from app.models.training_pipeline import (
    ModelSpec,
    approved_model_specs,
    evaluate_model,
    materialize_cv_folds,
    most_frequent_baseline,
)


class RecordingTransformer(BaseEstimator, TransformerMixin):
    fitted_indices: list[tuple[int, ...]] = []

    def fit(self, x, y=None):
        type(self).fitted_indices.append(tuple(int(index) for index in x.index))
        return self

    def transform(self, x):
        return np.asarray(x)


def test_exactly_three_approved_models_and_context_only_baseline():
    specs = approved_model_specs(random_seed=17)

    assert [spec.name for spec in specs] == [
        "LogisticRegression",
        "RandomForestClassifier",
        "HistGradientBoostingClassifier",
    ]
    assert [spec.factory().__class__.__name__ for spec in specs] == [
        "LogisticRegression",
        "RandomForestClassifier",
        "HistGradientBoostingClassifier",
    ]
    assert all(spec.factory().get_params().get("random_state") == 17 for spec in specs)
    assert most_frequent_baseline().name == "MostFrequentBaseline"


def test_model_version_is_stable_and_parameter_sensitive():
    estimator = approved_model_specs(random_seed=42)[0].factory()
    estimator_name = (
        f"{estimator.__class__.__module__}.{estimator.__class__.__qualname__}"
    )
    parameters = estimator.get_params(deep=True)

    first = training_pipeline._model_version(
        "LogisticRegression", estimator_name, parameters
    )
    second = training_pipeline._model_version(
        "LogisticRegression", estimator_name, parameters
    )
    changed = training_pipeline._model_version(
        "LogisticRegression",
        estimator_name,
        {**parameters, "max_iter": parameters["max_iter"] + 1},
    )

    assert first == second
    assert first.startswith("LogisticRegression-v1-")
    assert changed != first


def test_materialized_folds_are_identical_reproducible_and_disjoint():
    y = pd.Series(["Major", "Moderate", "Minor"] * 10)
    folds_a, fingerprint_a = materialize_cv_folds(y, n_splits=5, random_seed=42)
    folds_b, fingerprint_b = materialize_cv_folds(y, n_splits=5, random_seed=42)

    assert fingerprint_a == fingerprint_b
    assert len(folds_a) == 5
    validation_indices = []
    for (fit_a, validation_a), (fit_b, validation_b) in zip(folds_a, folds_b):
        assert np.array_equal(fit_a, fit_b)
        assert np.array_equal(validation_a, validation_b)
        assert set(fit_a).isdisjoint(validation_a)
        validation_indices.extend(validation_a.tolist())
    assert sorted(validation_indices) == list(range(len(y)))


def test_preprocessing_is_fitted_only_on_each_training_fold(monkeypatch):
    RecordingTransformer.fitted_indices = []
    monkeypatch.setattr(
        training_pipeline,
        "build_model_pipeline",
        lambda estimator: Pipeline([
            ("preprocessing", RecordingTransformer()),
            ("classifier", estimator),
        ]),
    )
    x = pd.DataFrame({"feature": np.arange(30, dtype=float)})
    y = pd.Series(["Major", "Moderate", "Minor"] * 10)
    folds, _ = materialize_cv_folds(y, n_splits=5, random_seed=42)
    spec = ModelSpec("AuditModel", lambda: DummyClassifier(strategy="most_frequent"))

    evaluate_model(spec, x, y, folds)

    expected_fit_indices = [tuple(int(index) for index in fit) for fit, _ in folds]
    assert RecordingTransformer.fitted_indices == expected_fit_indices
    for fitted, (_, validation) in zip(RecordingTransformer.fitted_indices, folds):
        assert set(fitted).isdisjoint(validation)


def test_loader_reads_only_training_split_and_enforces_contract(tmp_path, monkeypatch):
    rows = 12
    frame = pd.DataFrame({
        feature: np.arange(rows, dtype=float) + index
        for index, feature in enumerate(FEATURE_COLUMNS)
    })
    frame["ddi_severity"] = ["Major", "Moderate", "Minor"] * 4
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"
    contract_path = tmp_path / "feature_contract.json"
    frame.to_csv(train_path, index=False)
    test_path.write_text("must not be read\n", encoding="utf-8")
    contract_path.write_text(json.dumps({
        "features": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "train_rows": rows,
        "classes": ["Major", "Moderate", "Minor"],
        "train_class_counts": {"Major": 4, "Moderate": 4, "Minor": 4},
        "provenance": {},
    }), encoding="utf-8")
    original_read_csv = pd.read_csv
    reads: list[Path] = []

    def audited_read_csv(path, *args, **kwargs):
        resolved = Path(path).resolve()
        reads.append(resolved)
        if resolved == test_path.resolve():
            raise AssertionError("The untouched test split was read")
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(training_pipeline.pd, "read_csv", audited_read_csv)
    loaded, contract = training_pipeline.load_training_data(train_path, contract_path)

    assert len(loaded) == rows
    assert contract["feature_count"] == 55
    assert reads == [train_path.resolve()]


def test_experiment_metadata_keeps_serving_inactive(tmp_path, monkeypatch):
    rows = 12
    frame = pd.DataFrame({
        feature: np.arange(rows, dtype=float) + index
        for index, feature in enumerate(FEATURE_COLUMNS)
    })
    frame["ddi_severity"] = ["Major", "Moderate", "Minor"] * 4
    data_dir = tmp_path / "data" / "processed" / "sprint3"
    contract_dir = tmp_path / "data" / "interim" / "sprint4"
    data_dir.mkdir(parents=True)
    contract_dir.mkdir(parents=True)
    train_path = data_dir / "train.csv"
    contract_path = contract_dir / "feature_contract.json"
    frame.to_csv(train_path, index=False)
    contract_path.write_text(json.dumps({
        "features": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "train_rows": rows,
        "classes": ["Major", "Moderate", "Minor"],
        "train_class_counts": {"Major": 4, "Moderate": 4, "Minor": 4},
        "provenance": {"target": "DDInter 2.0"},
    }), encoding="utf-8")

    def fake_evaluate(spec, x_train, y_train, folds):
        return {
            "name": spec.name,
            "metrics": {"macro_f1": {"mean": 0.5, "std": 0.01}},
        }

    monkeypatch.setattr(training_pipeline, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(training_pipeline, "evaluate_model", fake_evaluate)
    monkeypatch.setattr(
        training_pipeline,
        "_git_state",
        lambda: {"commit": "test-commit", "working_tree_dirty": False},
    )
    report = training_pipeline.run_training_experiment(
        train_path=train_path,
        contract_path=contract_path,
        output_path=None,
        n_splits=2,
    )

    assert report["serving"] == {
        "status": "inactive",
        "model_artifact_persisted": False,
        "inference_endpoint_enabled": False,
        "candidate_scoring_integration_enabled": False,
        "mlStatus": "not_applied",
    }
    assert report["test_isolation"]["test_split_loaded"] is False
    assert report["selection"]["baseline_is_selection_eligible"] is False
    assert report["primary_metric"] == "macro_f1"
    assert set(report["runtime"]["implementation_files_sha256"]) == {
        "ml_engine/app/models/training_pipeline.py",
        "ml_engine/app/data/preprocessing.py",
    }
