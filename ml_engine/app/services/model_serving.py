"""Verified, fail-closed serving for the frozen Sprint 5 DDI classifier."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from threading import Lock
from typing import Any

import joblib
import pandas as pd

from app.data.ddinter_dataset import ALLOWED_LABELS, FEATURE_COLUMNS
from app.models.final_evaluation import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_FEATURE_CONTRACT_PATH,
    DEFAULT_METADATA_PATH,
    deterministic_model_version,
    sha256_file,
    validate_pipeline_shape,
)


class ModelUnavailableError(RuntimeError):
    """Raised when the verified frozen model cannot be used."""


class FeatureSchemaError(ValueError):
    """Raised before inference when a feature payload violates the contract."""


class DDIModelService:
    """Load the trusted repository artifact once, only after integrity checks."""

    def __init__(
        self,
        *,
        artifact_path: Path | None = None,
        metadata_path: Path = DEFAULT_METADATA_PATH,
        feature_contract_path: Path = DEFAULT_FEATURE_CONTRACT_PATH,
    ) -> None:
        configured_path = os.getenv("POLYMERGE_DDI_MODEL_PATH")
        self.artifact_path = artifact_path or (
            Path(configured_path).expanduser().resolve()
            if configured_path
            else DEFAULT_ARTIFACT_PATH
        )
        self.metadata_path = metadata_path
        self.feature_contract_path = feature_contract_path
        self._pipeline: Any | None = None
        self._metadata: dict[str, Any] | None = None
        self._load_error: str | None = None
        self._load_attempted = False
        self._lock = Lock()

    def load(self) -> None:
        """Verify metadata, contract, checksum, and pipeline before activation."""
        if self._load_attempted:
            if self._pipeline is None:
                raise ModelUnavailableError(self._load_error or "Model unavailable")
            return

        with self._lock:
            if self._load_attempted:
                if self._pipeline is None:
                    raise ModelUnavailableError(self._load_error or "Model unavailable")
                return
            self._load_attempted = True
            try:
                metadata = self._read_json(self.metadata_path, "model metadata")
                contract = self._read_json(self.feature_contract_path, "feature contract")
                self._validate_metadata(metadata, contract)
                if not self.artifact_path.is_file():
                    raise FileNotFoundError(
                        f"Frozen model artifact is not installed at {self.artifact_path}"
                    )
                actual_size = self.artifact_path.stat().st_size
                if actual_size != metadata["artifact_size_bytes"]:
                    raise ValueError(
                        "Frozen model artifact size does not match signed metadata"
                    )
                actual_sha256 = sha256_file(self.artifact_path)
                if actual_sha256 != metadata["artifact_sha256"]:
                    raise ValueError(
                        "Frozen model artifact SHA-256 does not match signed metadata"
                    )

                # joblib uses pickle internally. Deserialization occurs only after the
                # configured artifact matches the reviewed SHA-256 metadata.
                pipeline = joblib.load(self.artifact_path)
                validate_pipeline_shape(pipeline)
                fitted_classes = [str(value) for value in pipeline.classes_]
                if set(fitted_classes) != set(ALLOWED_LABELS):
                    raise ValueError(
                        f"Frozen model classes differ from the approved contract: {fitted_classes}"
                    )
                self._pipeline = pipeline
                self._metadata = metadata
            except Exception as error:
                self._load_error = str(error)
                raise ModelUnavailableError(self._load_error) from error

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """Return one model class; never synthesize a score or fallback class."""
        normalized = self.validate_features(features)
        self.load()
        assert self._pipeline is not None
        assert self._metadata is not None
        try:
            predicted_class = str(
                self._pipeline.predict(pd.DataFrame([normalized], columns=FEATURE_COLUMNS))[0]
            )
        except Exception as error:
            raise ModelUnavailableError(f"Frozen model inference failed: {error}") from error
        if predicted_class not in ALLOWED_LABELS:
            raise ModelUnavailableError(
                f"Frozen model returned an unsupported class: {predicted_class}"
            )
        return {
            "predictedClass": predicted_class,
            "inferenceStatus": "applied",
            "mlStatus": "applied",
            "model": {
                "name": self._metadata["model_name"],
                "version": self._metadata["model_version"],
                "artifactSha256": self._metadata["artifact_sha256"],
                "featureContractSha256": self._metadata["feature_contract_sha256"],
            },
        }

    def validate_features(self, features: Any) -> dict[str, float | int | None]:
        if not isinstance(features, dict):
            raise FeatureSchemaError("features must be a JSON object")
        expected = set(FEATURE_COLUMNS)
        supplied = set(features)
        missing = sorted(expected - supplied)
        unexpected = sorted(supplied - expected)
        if missing or unexpected:
            parts = []
            if missing:
                parts.append(f"missing: {', '.join(missing)}")
            if unexpected:
                parts.append(f"unexpected: {', '.join(unexpected)}")
            raise FeatureSchemaError(
                "features must match the approved 55-column contract (" + "; ".join(parts) + ")"
            )

        normalized: dict[str, float | int | None] = {}
        for name in FEATURE_COLUMNS:
            value = features[name]
            if value is None:
                normalized[name] = None
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FeatureSchemaError(f"feature {name} must be a finite number or null")
            if not math.isfinite(float(value)):
                raise FeatureSchemaError(f"feature {name} must be a finite number or null")
            normalized[name] = value
        return normalized

    def status(self) -> dict[str, Any]:
        try:
            self.load()
        except ModelUnavailableError:
            metadata = self._metadata_if_readable()
            return {
                "inferenceStatus": "unavailable",
                "mlStatus": "not_applied",
                "modelVersion": metadata.get("model_version") if metadata else None,
                "artifactSha256": metadata.get("artifact_sha256") if metadata else None,
                "reason": self._load_error,
            }
        assert self._metadata is not None
        return {
            "inferenceStatus": "ready",
            "mlStatus": "not_applied",
            "modelVersion": self._metadata["model_version"],
            "artifactSha256": self._metadata["artifact_sha256"],
        }

    def unavailable_response(self, reason: str | None = None) -> dict[str, Any]:
        metadata = self._metadata or self._metadata_if_readable()
        return {
            "predictedClass": None,
            "inferenceStatus": "unavailable",
            "mlStatus": "not_applied",
            "model": {
                "name": metadata.get("model_name") if metadata else None,
                "version": metadata.get("model_version") if metadata else None,
                "artifactSha256": metadata.get("artifact_sha256") if metadata else None,
                "featureContractSha256": (
                    metadata.get("feature_contract_sha256") if metadata else None
                ),
            },
            "error": reason or self._load_error or "Frozen model unavailable",
        }

    @staticmethod
    def _read_json(path: Path, label: str) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(f"Missing {label}: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid {label}: expected a JSON object")
        return payload

    def _validate_metadata(
        self,
        metadata: dict[str, Any],
        contract: dict[str, Any],
    ) -> None:
        if metadata.get("artifact_format") != "joblib":
            raise ValueError("Unsupported frozen model artifact format")
        if metadata.get("model_name") != "RandomForestClassifier":
            raise ValueError("Frozen metadata does not identify the selected Random Forest")
        if metadata.get("features") != FEATURE_COLUMNS:
            raise ValueError("Frozen metadata feature order differs from application contract")
        if metadata.get("feature_count") != len(FEATURE_COLUMNS):
            raise ValueError("Frozen metadata feature count differs from application contract")
        if metadata.get("classes") != list(ALLOWED_LABELS):
            raise ValueError("Frozen metadata class contract differs from application contract")
        if contract.get("features") != FEATURE_COLUMNS:
            raise ValueError("Feature contract order differs from application contract")
        if contract.get("classes") != list(ALLOWED_LABELS):
            raise ValueError("Feature contract classes differ from application contract")
        contract_sha256 = _portable_text_sha256(self.feature_contract_path)
        if metadata.get("feature_contract_sha256") != contract_sha256:
            raise ValueError("Feature contract SHA-256 does not match frozen metadata")
        if not isinstance(metadata.get("artifact_sha256"), str):
            raise ValueError("Frozen metadata is missing artifact SHA-256")
        if not isinstance(metadata.get("artifact_size_bytes"), int):
            raise ValueError("Frozen metadata is missing artifact size")
        if not isinstance(metadata.get("model_version"), str):
            raise ValueError("Frozen metadata is missing model version")
        try:
            expected_version = deterministic_model_version(
                train_sha256=metadata["training_dataset_sha256"],
                feature_contract_sha256=metadata["feature_contract_sha256"],
                preprocessing_sha256=metadata["preprocessing_sha256"],
                versions={"scikit-learn": metadata["scikit_learn_version"]},
            )
        except (KeyError, TypeError) as error:
            raise ValueError("Frozen metadata is missing model-version inputs") from error
        if metadata["model_version"] != expected_version:
            raise ValueError("Frozen model version does not match its provenance inputs")

    def _metadata_if_readable(self) -> dict[str, Any] | None:
        try:
            return self._read_json(self.metadata_path, "model metadata")
        except Exception:
            return None


def _portable_text_sha256(path: Path) -> str:
    """Hash reviewed JSON bytes consistently across Git LF/CRLF checkouts."""
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


ddi_model_service = DDIModelService()
