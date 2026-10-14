"""Validate tracked serving metadata without loading or evaluating a model."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA = "2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d"
EXPECTED_VERSION = "RandomForestClassifier-sprint5-v1-65e9834666ad19c5"


def validate() -> None:
    metadata = json.loads((ROOT / "data/interim/sprint5/final_model_evaluation.json").read_text())
    contract_bytes = (ROOT / "data/interim/sprint4/feature_contract.json").read_bytes()
    contract = json.loads(contract_bytes)
    if metadata["artifact_sha256"] != EXPECTED_SHA or metadata["artifact_size_bytes"] != 251404304:
        raise ValueError("Frozen artifact identity changed")
    if metadata["model_version"] != EXPECTED_VERSION:
        raise ValueError("Frozen model version changed")
    if metadata["feature_contract_sha256"] != hashlib.sha256(contract_bytes).hexdigest():
        raise ValueError("Feature contract checksum mismatch")
    if contract["feature_count"] != 55 or len(set(contract["features"])) != 55:
        raise ValueError("Expected 55 unique features")
    if set(contract["classes"]) != {"Major", "Moderate", "Minor"}:
        raise ValueError("Unexpected severity classes")


if __name__ == "__main__":
    validate()
