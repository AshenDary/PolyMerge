from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "frozen_probe", Path(__file__).resolve().parents[1] / "verify_frozen_runtime.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class FrozenProbeChecks(unittest.TestCase):
    def payload(self) -> dict:
        return {
            "artifactSha256": "trusted", "featureCount": 55, "classes": ["Minor"],
            "predictions": ["Minor"], "probabilities": [[1.0]], "unsupportedPair": "missing",
            "features": ["feature"], "fixturePairs": [["a", "b"]], "unavailablePairs": {},
            "productionCompatible": True, "sklearn": "1.4.0", "peakRssRaw": 1, "platform": "test",
        }

    def run_probe(self, actual: dict, expected: dict) -> dict:
        with TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            output = Path(directory) / "output.json"
            baseline.write_text(json.dumps(expected))
            with patch.object(probe, "probe", return_value=actual), patch(
                "sys.argv", ["probe", "--baseline", str(baseline), "--output", str(output)]
            ):
                probe.main()
            return json.loads(output.read_text())

    def test_exact_parity_survives_json_roundtrip(self) -> None:
        payload = self.payload()
        self.assertEqual(self.run_probe(payload, payload)["fixturePairs"], [["a", "b"]])

    def test_probability_drift_fails(self) -> None:
        actual = self.payload()
        actual["probabilities"] = [[0.999999999]]
        with self.assertRaises(AssertionError):
            self.run_probe(actual, self.payload())

    def test_numerical_parity_never_waives_incompatible_runtime(self) -> None:
        actual = self.payload()
        actual["productionCompatible"] = False
        with self.assertRaises(SystemExit) as raised:
            self.run_probe(actual, self.payload())
        self.assertEqual(raised.exception.code, 2)
