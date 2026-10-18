"""Compare inference probes only; never train or read held-out evaluation rows."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import warnings
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_engine"))

import numpy as np
import pandas as pd
import sklearn
import joblib
from sklearn.exceptions import InconsistentVersionWarning
from app.services.ddi_feature_builder import PairFeatureBuilder, PairFeatureUnavailableError
from app.services.model_serving import DDIModelService
from app.data.ddinter_dataset import FEATURE_COLUMNS
from app.models.final_evaluation import sha256_file, validate_pipeline_shape


def probe(fixtures: Path | None = None, experimental_runtime: bool = False) -> dict:
    service = DDIModelService()
    compatibility_warnings = []
    if experimental_runtime:
        # Offline investigation only. The production version guard is never changed.
        metadata = service._read_json(service.metadata_path, "metadata")
        service._validate_metadata(metadata, service._read_json(service.feature_contract_path, "contract"))
        assert sha256_file(service.artifact_path) == metadata["artifact_sha256"]
        assert service.artifact_path.stat().st_size == metadata["artifact_size_bytes"]
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            pipeline = joblib.load(service.artifact_path)
        compatibility_warnings = sorted({str(item.message) for item in recorded})
        for message in compatibility_warnings:
            sys.stderr.write(message + "\n")
        validate_pipeline_shape(pipeline)
    else:
        warnings.simplefilter("error", InconsistentVersionWarning)
        service.load()
        metadata, pipeline = service._metadata, service._pipeline
    builder = PairFeatureBuilder()
    ids = sorted(builder._hetionet_to_ddinter)[:6]
    rows = [builder.build_features(ids[0], other) for other in ids[1:]]
    fixture_pairs = set()
    unavailable = {}
    if fixtures:
        for path in sorted(fixtures.glob("*.json")):
            payload = json.loads(path.read_text())
            for candidate in payload.get("candidateSets", []):
                fixture_pairs.update(tuple(sorted(pair)) for pair in combinations(candidate["drugs"], 2))
        for pair in sorted(fixture_pairs):
            try:
                rows.append(builder.build_features(*pair))
            except PairFeatureUnavailableError as error:
                unavailable["|".join(pair)] = error.code
    rows += [{name: 0 for name in FEATURE_COLUMNS}, {name: None for name in FEATURE_COLUMNS}]
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    assert pipeline is not None
    assert metadata["artifact_sha256"] == "2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d"
    assert len(FEATURE_COLUMNS) == 55
    try:
        assert not any("Tfidf" in type(value).__name__ for value in pipeline.get_params(deep=True).values())
    except AttributeError as error:
        if not experimental_runtime:
            raise
        compatibility_warnings.append(str(error))
        sys.stderr.write("Estimator API incompatibility: " + str(error) + "\n")
    try:
        builder.build_features("Compound::DB00177", "Compound::DB00796")
    except PairFeatureUnavailableError as error:
        unsupported = error.code
    else:
        raise AssertionError("Expected unsupported pair")
    return {"sklearn": sklearn.__version__, "artifactSha256": metadata["artifact_sha256"],
            "featureCount": len(FEATURE_COLUMNS), "classes": pipeline.classes_.tolist(),
            "predictions": pipeline.predict(frame).tolist(), "probabilities": pipeline.predict_proba(frame).tolist(),
            "features": FEATURE_COLUMNS, "fixturePairs": [list(pair) for pair in sorted(fixture_pairs)], "unavailablePairs": unavailable,
            "compatibilityWarnings": compatibility_warnings, "rowCount": len(rows),
            "productionCompatible": not compatibility_warnings and sklearn.__version__ == metadata["scikit_learn_version"],
            "unsupportedPair": unsupported, "peakRssRaw": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "platform": sys.platform}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--experimental-runtime", action="store_true", help="Offline probe; warnings remain a failing compatibility gate")
    args = parser.parse_args()
    actual = probe(args.fixtures, args.experimental_runtime)
    if args.baseline:
        expected = json.loads(args.baseline.read_text())
        for key in ["artifactSha256", "featureCount", "classes", "predictions", "unsupportedPair"]:
            assert actual[key] == expected[key], key
        np.testing.assert_array_equal(actual["probabilities"], expected["probabilities"])
        for key in ["features", "fixturePairs", "unavailablePairs"]:
            if key in expected:
                assert actual[key] == expected[key], key
    args.output.write_text(json.dumps(actual, indent=2) + "\n")
    sys.stdout.write(json.dumps({key: actual[key] for key in ["sklearn", "artifactSha256", "featureCount", "peakRssRaw", "platform"]}) + "\n")
    if not actual["productionCompatible"]:
        sys.stderr.write("Numerical probe completed, but production compatibility is NOT established.\n")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
