"""Read-only readiness checks; real candidate inference requires explicit opt-in."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from urllib.request import Request, urlopen

from check_release_metadata import EXPECTED_SHA, EXPECTED_VERSION

LOG = logging.getLogger("polymerge.smoke")
FORBIDDEN = {"confidence", "probability", "probabilities", "safetyScore", "combinedSafetyScore"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def reject_scores(value: object) -> None:
    if isinstance(value, dict):
        require(not FORBIDDEN.intersection(value), "Unsupported score field returned")
        for key, item in value.items():
            if key in {"interactionRisk", "synergyScore"}:
                require(item is None, "Legacy score must be null")
            reject_scores(item)
    elif isinstance(value, list):
        for item in value:
            reject_scores(item)


def validate_candidates(data: dict) -> None:
    require(data.get("metadata", {}).get("dataStatus") == "real_graph", "Not real graph data")
    candidates = data.get("candidateSets", [])
    require(bool(candidates), "No candidates returned")
    applied = 0
    for candidate in candidates:
        reject_scores(candidate)
        require(candidate.get("status") in {"accepted", "rejected"}, "Missing rule status")
        paths = candidate.get("graphEvidence", {}).get("paths", [])
        require(bool(paths), "Missing graph paths")
        ids = [path.get("pathId") for path in paths]
        require(all(ids) and len(ids) == len(set(ids)), "Invalid path identity")
        for path in paths:
            provenance = path.get("provenance", {})
            require(provenance.get("source") == "Hetionet", "Missing graph provenance")
            require(bool(provenance.get("graphVersion")), "Missing graph version")
            relationship = path.get("relationship", {})
            kind = relationship.get("type") if isinstance(relationship, dict) else relationship
            require(kind in {"CtD", "CbG", "CuG", "CdG", "CcSE"}, "Unsupported evidence relationship")
            identity = json.dumps([provenance["source"], path["sourceEntity"]["id"], kind,
                                   path["targetEntity"]["id"], provenance["graphVersion"]],
                                  ensure_ascii=True, separators=(",", ":"))
            expected = "graph-path:" + hashlib.sha256(identity.encode()).hexdigest()[:24]
            require(path["pathId"] == expected, "Nondeterministic path identity")
        for pair in candidate.get("mlPrediction", {}).get("pairs", []):
            if pair.get("inferenceStatus") == "applied":
                require(pair.get("predictedSeverity") in {"Major", "Moderate", "Minor"}, "Invalid severity")
                require(pair.get("model", {}).get("version") == EXPECTED_VERSION, "Wrong pair model")
                applied += 1
    require(applied > 0, "No applied pair inference; staging not ready for ML demo")


def request(base: str, path: str, body: dict | None = None) -> bytes:
    started = time.monotonic()
    req = Request(base.rstrip("/") + path, data=json.dumps(body).encode() if body else None,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=180 if body else 15) as response:
        require(response.status == 200, "Expected HTTP 200")
        result = response.read()
    LOG.info("PASS %s %.3fs", path, time.monotonic() - started)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--ml", required=True, help="Private URL; run from deployment network")
    parser.add_argument("--streamlit", required=True)
    parser.add_argument("--query", action="store_true", help="Run one real two-disease inference")
    args = parser.parse_args()
    require(b"PolyMerge" in request(args.frontend, "/"), "Frontend HTML missing")
    for path in ["/frontend/app.js", "/frontend/explainability.js", "/frontend/styles.css",
                 "/frontend/explainability.css"]:
        require(bool(request(args.frontend, path)), "Empty static asset")
    for figure in ["severity_distribution", "pair_structure_coverage", "hetionet_mapping_coverage", "feature_missingness"]:
        require(b"<svg" in request(args.frontend, f"/docs/figures/sprint3/{figure}.svg"), "Invalid EDA asset")
    for base, path in [(args.frontend, "/health"), (args.frontend, "/health/dependencies"), (args.ml, "/health")]:
        require(json.loads(request(base, path)).get("status") == "ok", "Health not ready")
    model = json.loads(request(args.ml, "/health/model"))
    require(model.get("inferenceStatus") == "ready", "Model not ready")
    require(model.get("modelVersion") == EXPECTED_VERSION and model.get("artifactSha256") == EXPECTED_SHA, "Model identity mismatch")
    catalog = json.loads(request(args.frontend, "/api/diseases"))
    require(bool(catalog.get("diseases")), "Empty catalog")
    require(bool(json.loads(request(args.frontend, "/api/model-comparison"))), "No model comparison")
    require(bool(request(args.streamlit, "/")), "Empty Streamlit page")
    require(request(args.streamlit, "/_stcore/health").strip() == b"ok", "Streamlit unhealthy")
    if args.query:
        data = json.loads(request(args.frontend, "/api/candidate-sets/search", {
            "diseaseIds": ["Disease::DOID:10763", "Disease::DOID:9352"]}))
        validate_candidates(data)
    LOG.warning("Browser iframe, responsiveness, console and keyboard acceptance still require browser testing")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
