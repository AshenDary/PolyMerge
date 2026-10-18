import sys
import hashlib
import json
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_release_metadata import validate, EXPECTED_VERSION
from deployment_smoke import reject_scores, validate_candidates


class ReleaseChecks(unittest.TestCase):
    def test_real_channels_and_path_identity(self) -> None:
        identity = ["Hetionet", "Compound::1", "CtD", "Disease::1", "v1"]
        path = {"pathId": "graph-path:" + hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()[:24],
                "sourceEntity": {"id": "Compound::1"}, "targetEntity": {"id": "Disease::1"},
                "relationship": {"type": "CtD"}, "provenance": {"source": "Hetionet", "graphVersion": "v1"}}
        candidate = {"status": "accepted", "graphEvidence": {"paths": [path]},
                     "mlPrediction": {"pairs": [{"inferenceStatus": "applied", "predictedSeverity": "Minor",
                                                  "model": {"version": EXPECTED_VERSION}}]}}
        data = {"metadata": {"dataStatus": "real_graph"}, "candidateSets": [candidate]}
        validate_candidates(data)
        path["pathId"] = "fabricated"
        with self.assertRaises(ValueError):
            validate_candidates(data)

    def test_frozen_metadata(self) -> None:
        validate()

    def test_nested_score_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reject_scores({"pairs": [{"confidence": 0.9}]})

    def test_null_compatibility(self) -> None:
        reject_scores({"interactionRisk": None, "synergyScore": None})
        with self.assertRaises(ValueError):
            reject_scores({"synergyScore": 0.1})

    def test_empty_or_fallback_not_success(self) -> None:
        for data in [{}, {"metadata": {"dataStatus": "real_graph"}, "candidateSets": []}]:
            with self.assertRaises(ValueError):
                validate_candidates(data)
