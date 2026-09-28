from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline

from app.data.ddinter_dataset import ALLOWED_LABELS, FEATURE_COLUMNS, TARGET_COLUMN
from app.models import final_evaluation


class RecordingTransformer(BaseEstimator, TransformerMixin):
    fitted_row_counts: list[int] = []

    def fit(self, x, y=None):
        type(self).fitted_row_counts.append(len(x))
        return self

    def transform(self, x):
        return np.asarray(x, dtype=float)


def _frame(rows: int, offset: int = 0) -> pd.DataFrame:
    data = {
        feature: np.asarray([(offset + row + index) % 7 for row in range(rows)], dtype=float)
        for index, feature in enumerate(FEATURE_COLUMNS)
    }
    frame = pd.DataFrame(data)
    labels = list(ALLOWED_LABELS)
    frame[TARGET_COLUMN] = [labels[row % len(labels)] for row in range(rows)]
    frame["pair_id"] = [f"pair-{offset + row}" for row in range(rows)]
    return frame


def _contract(train_rows: int, test_rows: int) -> dict[str, object]:
    return {
        "features": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "target": TARGET_COLUMN,
        "classes": list(ALLOWED_LABELS),
        "train_rows": train_rows,
        "test_rows": test_rows,
        "train_class_counts": {"Major": 2, "Moderate": 2, "Minor": 2},
        "test_class_counts": {"Major": 1, "Moderate": 1, "Minor": 1},
    }


def _sprint4_experiment() -> dict[str, object]:
    return {
        "selection": {"selected_model": "RandomForestClassifier"},
        "models": [
            {
                "name": "RandomForestClassifier",
                "model_version": "RandomForestClassifier-v1-test",
                "parameters": final_evaluation.FROZEN_RF_PARAMETERS,
                "metrics": {
                    "macro_f1": {
                        "mean": final_evaluation.SPRINT4_VALIDATION_MACRO_F1_MEAN,
                        "std": final_evaluation.SPRINT4_VALIDATION_MACRO_F1_STD,
                    }
                },
            }
        ],
    }


def _write_fixture(tmp_path: Path, train: pd.DataFrame, test: pd.DataFrame) -> final_evaluation.FinalEvaluationPaths:
    train_path = tmp_path / "train.csv"
    test_path = tmp_path / "test.csv"
    contract_path = tmp_path / "feature_contract.json"
    experiment_path = tmp_path / "training_experiment.json"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    contract_path.write_text(json.dumps(_contract(len(train), len(test))), encoding="utf-8")
    experiment_path.write_text(json.dumps(_sprint4_experiment()), encoding="utf-8")
    return final_evaluation.FinalEvaluationPaths(
        train_path=train_path,
        test_path=test_path,
        feature_contract_path=contract_path,
        sprint4_experiment_path=experiment_path,
        artifact_path=tmp_path / "models" / "random_forest.joblib",
        metadata_path=tmp_path / "metadata.json",
        report_path=tmp_path / "report.md",
    )


def _patch_fixture_expectations(
    monkeypatch: pytest.MonkeyPatch,
    paths: final_evaluation.FinalEvaluationPaths,
    *,
    train_rows: int,
    test_rows: int,
) -> None:
    monkeypatch.setattr(final_evaluation, "EXPECTED_TRAIN_ROWS", train_rows)
    monkeypatch.setattr(final_evaluation, "EXPECTED_TEST_ROWS", test_rows)
    monkeypatch.setattr(
        final_evaluation,
        "EXPECTED_TRAIN_SHA256",
        final_evaluation.sha256_file(paths.train_path),
    )
    monkeypatch.setattr(
        final_evaluation,
        "EXPECTED_FEATURE_CONTRACT_SHA256",
        final_evaluation.sha256_file(paths.feature_contract_path),
    )


def test_exact_rf_configuration_and_pipeline_shape():
    pipeline = final_evaluation.build_final_pipeline()

    assert isinstance(pipeline, Pipeline)
    assert list(pipeline.named_steps) == ["preprocessing", "classifier"]
    classifier = pipeline.named_steps["classifier"]
    for key, value in final_evaluation.FROZEN_RF_PARAMETERS.items():
        assert classifier.get_params()[key] == value


def test_feature_and_target_guards_reject_invalid_schema(monkeypatch):
    train = _frame(6)
    test = _frame(3, offset=100)
    monkeypatch.setattr(final_evaluation, "EXPECTED_TRAIN_ROWS", len(train))
    monkeypatch.setattr(final_evaluation, "EXPECTED_TEST_ROWS", len(test))
    broken_test = test.drop(columns=[FEATURE_COLUMNS[-1]])

    with pytest.raises(ValueError, match="feature schema"):
        final_evaluation.validate_preflight(train, broken_test, _contract(len(train), len(test)))


def test_target_class_guard_rejects_unknown_label(monkeypatch):
    train = _frame(6)
    test = _frame(3, offset=100)
    test.loc[0, TARGET_COLUMN] = "Unknown"
    monkeypatch.setattr(final_evaluation, "EXPECTED_TRAIN_ROWS", len(train))
    monkeypatch.setattr(final_evaluation, "EXPECTED_TEST_ROWS", len(test))

    with pytest.raises(ValueError, match="classes|Unknown"):
        final_evaluation.validate_preflight(train, test, _contract(len(train), len(test)))


def test_deterministic_model_version_is_stable_and_hash_sensitive():
    versions = {"scikit-learn": "1.4.0"}
    first = final_evaluation.deterministic_model_version(
        train_sha256="train",
        feature_contract_sha256="contract",
        preprocessing_sha256="preprocessing",
        versions=versions,
    )
    second = final_evaluation.deterministic_model_version(
        train_sha256="train",
        feature_contract_sha256="contract",
        preprocessing_sha256="preprocessing",
        versions=versions,
    )
    changed = final_evaluation.deterministic_model_version(
        train_sha256="changed",
        feature_contract_sha256="contract",
        preprocessing_sha256="preprocessing",
        versions=versions,
    )

    assert first == second
    assert first.startswith("RandomForestClassifier-sprint5-v1-")
    assert changed != first


def test_artifact_checksum_helper(tmp_path):
    path = tmp_path / "payload.txt"
    path.write_text("polymerge\n", encoding="utf-8")

    assert final_evaluation.sha256_file(path) == (
        "fb1ce6d714282f27fbf8afd301fdbe834de009aa367a1bcc61d65c8c9c0f94c0"
    )


def test_final_evaluation_writes_metadata_and_loadable_artifact(tmp_path, monkeypatch):
    train = _frame(6)
    test = _frame(3, offset=100)
    paths = _write_fixture(tmp_path, train, test)
    _patch_fixture_expectations(
        monkeypatch,
        paths,
        train_rows=len(train),
        test_rows=len(test),
    )
    monkeypatch.setattr(
        final_evaluation,
        "EXPECTED_PREPROCESSING_SHA256",
        final_evaluation.sha256_file(
            Path(final_evaluation.build_preprocessing_pipeline.__code__.co_filename)
        ),
    )

    metadata = final_evaluation.run_final_evaluation(paths)
    saved = json.loads(paths.metadata_path.read_text(encoding="utf-8"))
    loaded_pipeline = joblib.load(paths.artifact_path)
    x_test = test[FEATURE_COLUMNS]

    assert saved["final_test_evaluation"] is True
    assert saved["test_used_for_training"] is False
    assert saved["parameters"] == final_evaluation.FROZEN_RF_PARAMETERS
    assert saved["artifact_sha256"] == final_evaluation.sha256_file(paths.artifact_path)
    assert loaded_pipeline.predict(x_test).shape == (len(test),)
    assert paths.report_path.exists()
    assert metadata["metadata_path"] == str(paths.metadata_path)


def test_preprocessing_fit_is_train_only_for_final_pipeline(tmp_path, monkeypatch):
    RecordingTransformer.fitted_row_counts = []
    train = _frame(6)
    test = _frame(3, offset=100)
    paths = _write_fixture(tmp_path, train, test)
    _patch_fixture_expectations(
        monkeypatch,
        paths,
        train_rows=len(train),
        test_rows=len(test),
    )

    def recording_builder():
        return RecordingTransformer()

    monkeypatch.setattr(final_evaluation, "build_preprocessing_pipeline", recording_builder)
    monkeypatch.setattr(
        final_evaluation,
        "EXPECTED_PREPROCESSING_SHA256",
        final_evaluation.sha256_file(Path(recording_builder.__code__.co_filename)),
    )

    final_evaluation.run_final_evaluation(paths)

    assert RecordingTransformer.fitted_row_counts == [len(train)]
    assert len(test) not in RecordingTransformer.fitted_row_counts


def test_existing_metadata_prevents_repeat_final_evaluation(tmp_path):
    train = _frame(6)
    test = _frame(3, offset=100)
    paths = _write_fixture(tmp_path, train, test)
    paths.metadata_path.write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to rerun"):
        final_evaluation.run_final_evaluation(paths)
