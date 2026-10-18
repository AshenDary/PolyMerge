"""Exact-output contracts, not machine-dependent latency assertions."""
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
import random
from threading import Event

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from app.services.candidate_generator import generate_candidate_sets, _candidate_set_from_combo, _unique_candidates
from app.services.set_cover_optimizer import optimize_candidate_sets
from app.services.ddi_feature_builder import PairFeatureUnavailableError
from app.services.ddi_feature_builder import PairFeatureBuilder


def test_heap_matches_exhaustive_reference_including_evidence_and_optimizer():
    rng = random.Random(42)
    targets = ["d1", "d2", "d3"]
    for iteration in range(20):
        drugs = [{"drugId": name, "treatedDiseaseIds": [d for d in targets if rng.choice([True, False])],
                  "graphEvidence": {"paths": [{"pathId": name, "sourceEntity": {"id": name}}]}}
                 for name in ["maoi", "ssri", "warfarin", "nsaid", "other", "other"]]
        unique = _unique_candidates(drugs)
        exhaustive = [_candidate_set_from_combo(combo, targets)
                      for size in range(1, 4) for combo in combinations(unique, size)]
        exhaustive.sort(key=lambda c: (c["status"] == "rejected", -len(c["treatedDiseaseIds"]), c["drugCount"], c["candidateSetId"]))
        k = [1, 5, 10, 100][iteration % 4]
        expected = [{**c, "rank": i} for i, c in enumerate(exhaustive[:k], 1)]
        actual = generate_candidate_sets(drugs, targets, max_candidate_sets=k)
        assert actual == expected
        assert optimize_candidate_sets(actual, targets) == optimize_candidate_sets(expected, targets)


def test_pair_snapshot_reused_only_within_request(monkeypatch):
    calls = {"builders": 0, "features": 0, "predictions": 0}

    class Builder:
        def __init__(self):
            calls["builders"] += 1

        def build_features(self, a, b):
            calls["features"] += 1
            if "unsupported" in (a, b):
                raise PairFeatureUnavailableError("unsupported fixture")
            return {"pair": (a, b)}

    def predict(features):
        calls["predictions"] += 1
        return {"predictedClass": "Moderate", "model": {"version": "fixture"}, "inferenceStatus": "applied"}

    monkeypatch.setattr(main, "PairFeatureBuilder", Builder)
    monkeypatch.setattr(main.ddi_model_service, "predict", predict)
    context = {"builder": None, "pairs": {}}
    forward = main._apply_pair_predictions({"drugs": ["a", "b"]}, context)
    reverse = main._apply_pair_predictions({"drugs": ["b", "a"]}, context)
    assert forward["mlPrediction"] == reverse["mlPrediction"]
    assert calls == {"builders": 1, "features": 1, "predictions": 1}
    failed = main._apply_pair_predictions({"drugs": ["a", "b", "unsupported"]}, context)
    assert failed["mlStatus"] == "partial"
    assert failed["mlPrediction"]["pairs"] == forward["mlPrediction"]["pairs"]
    assert len(failed["mlPrediction"]["unavailablePairs"]) == 2
    # A new graph/model/mapping request never inherits an old snapshot or prediction.
    main._apply_pair_predictions({"drugs": ["a", "b"]}, {"builder": None, "pairs": {}})
    assert calls["builders"] == 2 and calls["predictions"] == 2


def test_reused_real_feature_snapshot_equals_independent_builders():
    snapshot = PairFeatureBuilder()
    independent = PairFeatureBuilder()
    for pair in [("Compound::DB00177", "Compound::DB00187"),
                 ("Compound::DB00187", "Compound::DB00177")]:
        assert snapshot.build_features(*pair) == independent.build_features(*pair)


def test_bounded_analysis_leaves_health_responsive_and_releases_slot(monkeypatch):
    started, release = Event(), Event()

    def work(payload):
        started.set()
        assert release.wait(5)
        raise HTTPException(status_code=422, detail="fixture completed")

    monkeypatch.setattr(main, "_execute_candidate_sets", work)
    client = TestClient(main.app)
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(client.post, "/predict/candidate-sets", json={"diseaseIds": ["d"]})
        try:
            assert started.wait(5)
            assert client.get("/health").status_code == 200
            busy = client.post("/predict/candidate-sets", json={"diseaseIds": ["d"]})
            assert busy.status_code == 503 and busy.headers["Retry-After"] == "2"
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == 422
    assert client.post("/predict/candidate-sets", json={"diseaseIds": ["d"]}).status_code == 422
