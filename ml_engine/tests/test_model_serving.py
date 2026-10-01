from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main as ml_main
from app.data.ddinter_dataset import ALLOWED_LABELS, FEATURE_COLUMNS
from app.models.final_evaluation import (
    build_final_pipeline,
    deterministic_model_version,
    sha256_file,
)
from app.services.model_serving import (
    DDIModelService,
    FeatureSchemaError,
    ModelUnavailableError,
)


def _features(seed: int = 0) -> dict[str, float]:
    return {
        name: float((index + seed) % 7)
        for index, name in enumerate(FEATURE_COLUMNS)
    }


def _installed_model(tmp_path: Path) -> DDIModelService:
    tmp_path.mkdir(parents=True, exist_ok=True)
    contract_path = tmp_path / "feature_contract.json"
    contract_path.write_text(
        json.dumps({"features": FEATURE_COLUMNS, "classes": list(ALLOWED_LABELS)}),
        encoding="utf-8",
    )

    frame = pd.DataFrame([_features(seed) for seed in range(9)], columns=FEATURE_COLUMNS)
    labels = list(ALLOWED_LABELS) * 3
    pipeline = build_final_pipeline()
    pipeline.fit(frame, labels)
    artifact_path = tmp_path / "random_forest_ddi_pipeline.joblib"
    joblib.dump(pipeline, artifact_path)

    metadata_path = tmp_path / "final_model_evaluation.json"
    contract_sha256 = sha256_file(contract_path)
    train_sha256 = "training-fixture-sha256"
    preprocessing_sha256 = "preprocessing-fixture-sha256"
    sklearn_version = "1.4.0"
    model_version = deterministic_model_version(
        train_sha256=train_sha256,
        feature_contract_sha256=contract_sha256,
        preprocessing_sha256=preprocessing_sha256,
        versions={"scikit-learn": sklearn_version},
    )
    metadata_path.write_text(
        json.dumps({
            "artifact_format": "joblib",
            "artifact_sha256": sha256_file(artifact_path),
            "artifact_size_bytes": artifact_path.stat().st_size,
            "classes": list(ALLOWED_LABELS),
            "feature_contract_sha256": contract_sha256,
            "feature_count": len(FEATURE_COLUMNS),
            "features": FEATURE_COLUMNS,
            "model_name": "RandomForestClassifier",
            "model_version": model_version,
            "preprocessing_sha256": preprocessing_sha256,
            "scikit_learn_version": sklearn_version,
            "training_dataset_sha256": train_sha256,
        }),
        encoding="utf-8",
    )
    return DDIModelService(
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        feature_contract_path=contract_path,
    )


def test_verified_artifact_returns_prediction_and_version_provenance(tmp_path):
    service = _installed_model(tmp_path)

    result = service.predict(_features())

    assert result["predictedClass"] in ALLOWED_LABELS
    assert result["inferenceStatus"] == "applied"
    assert result["mlStatus"] == "applied"
    assert result["model"]["version"].startswith("RandomForestClassifier-sprint5-v1-")
    assert len(result["model"]["artifactSha256"]) == 64
    assert "score" not in result


def test_missing_artifact_fails_closed_without_prediction(tmp_path):
    service = _installed_model(tmp_path)
    service.artifact_path.unlink()

    with pytest.raises(ModelUnavailableError, match="not installed"):
        service.predict(_features())

    unavailable = service.unavailable_response()
    assert unavailable["predictedClass"] is None
    assert unavailable["inferenceStatus"] == "unavailable"
    assert unavailable["mlStatus"] == "not_applied"
    assert unavailable["model"]["version"].startswith("RandomForestClassifier-sprint5-v1-")


def test_checksum_mismatch_blocks_deserialization(tmp_path):
    service = _installed_model(tmp_path)
    with service.artifact_path.open("ab") as stream:
        stream.write(b"tampered")

    with pytest.raises(ModelUnavailableError, match="size does not match"):
        service.load()


def test_model_version_must_match_provenance_inputs(tmp_path):
    service = _installed_model(tmp_path)
    metadata = json.loads(service.metadata_path.read_text(encoding="utf-8"))
    metadata["model_version"] = "RandomForestClassifier-sprint5-v1-tampered"
    service.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ModelUnavailableError, match="version does not match"):
        service.load()


def test_malformed_feature_contract_is_rejected_before_model_loading(tmp_path):
    service = _installed_model(tmp_path)
    malformed = _features()
    malformed.pop(FEATURE_COLUMNS[0])
    malformed["invented_score"] = 0.9

    with pytest.raises(FeatureSchemaError, match="approved 55-column contract"):
        service.predict(malformed)


def test_ml_api_reports_applied_and_unavailable_states(tmp_path, monkeypatch):
    service = _installed_model(tmp_path)
    monkeypatch.setattr(ml_main, "ddi_model_service", service)
    with TestClient(ml_main.app) as client:
        applied = client.post("/predict/ddi-severity", json={"features": _features()})
    assert applied.status_code == 200
    assert applied.json()["mlStatus"] == "applied"

    unavailable_service = _installed_model(tmp_path / "missing")
    unavailable_service.artifact_path.unlink()
    monkeypatch.setattr(ml_main, "ddi_model_service", unavailable_service)
    with TestClient(ml_main.app) as client:
        unavailable = client.post("/predict/ddi-severity", json={"features": _features()})
    assert unavailable.status_code == 503
    assert unavailable.json()["predictedClass"] is None
    assert unavailable.json()["mlStatus"] == "not_applied"


def test_ml_api_rejects_bad_schema_without_inference(tmp_path, monkeypatch):
    service = _installed_model(tmp_path)
    monkeypatch.setattr(ml_main, "ddi_model_service", service)
    malformed = _features()
    malformed.pop(FEATURE_COLUMNS[-1])

    with TestClient(ml_main.app) as client:
        assert service._pipeline is not None
        predict_called = False

        def unexpected_predict(_):
            nonlocal predict_called
            predict_called = True
            raise AssertionError("pipeline prediction must not run")

        monkeypatch.setattr(service._pipeline, "predict", unexpected_predict)
        response = client.post("/predict/ddi-severity", json={"features": malformed})

    assert response.status_code == 422
    assert response.json()["detail"]["mlStatus"] == "not_applied"
    assert predict_called is False
