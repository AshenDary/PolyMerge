"""Compare inference probes only; never train or read held-out evaluation rows."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_engine"))

import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning
from app.services.ddi_feature_builder import PairFeatureBuilder, PairFeatureUnavailableError
from app.services.model_serving import DDIModelService
from app.data.ddinter_dataset import FEATURE_COLUMNS


def probe() -> dict:
    warnings.simplefilter("error", InconsistentVersionWarning)
    service = DDIModelService()
    service.load()
    builder = PairFeatureBuilder()
    ids = sorted(builder._hetionet_to_ddinter)[:6]
    rows = [builder.build_features(ids[0], other) for other in ids[1:]]
    rows += [{name: 0 for name in FEATURE_COLUMNS}, {name: None for name in FEATURE_COLUMNS}]
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    pipeline = service._pipeline
    assert pipeline is not None
    assert service._metadata["artifact_sha256"] == "2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d"
    assert len(FEATURE_COLUMNS) == 55
    assert not any("Tfidf" in type(value).__name__ for value in pipeline.get_params(deep=True).values())
    try:
        builder.build_features("Compound::DB00177", "Compound::DB00796")
    except PairFeatureUnavailableError as error:
        unsupported = error.code
    else:
        raise AssertionError("Expected unsupported pair")
    return {"sklearn": sklearn.__version__, "artifactSha256": service._metadata["artifact_sha256"],
            "featureCount": len(FEATURE_COLUMNS), "classes": pipeline.classes_.tolist(),
            "predictions": pipeline.predict(frame).tolist(), "probabilities": pipeline.predict_proba(frame).tolist(),
            "unsupportedPair": unsupported, "peakRssRaw": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "platform": sys.platform}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    actual = probe()
    if args.baseline:
        expected = json.loads(args.baseline.read_text())
        for key in ["artifactSha256", "featureCount", "classes", "predictions", "unsupportedPair"]:
            assert actual[key] == expected[key], key
        np.testing.assert_array_equal(actual["probabilities"], expected["probabilities"])
    args.output.write_text(json.dumps(actual, indent=2) + "\n")
    sys.stdout.write(json.dumps({key: actual[key] for key in ["sklearn", "artifactSha256", "featureCount", "peakRssRaw", "platform"]}) + "\n")


if __name__ == "__main__":
    main()
