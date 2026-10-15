"""Availability must reflect supported evidence, not successful-looking labels."""
import csv
import json
from pathlib import Path
import shutil
import subprocess

import pytest

import main
from app.services.safety_filter import resolve_rule_identity, evaluate_rule_applicability, check_hard_contraindications
from app.services.set_cover_optimizer import optimize_candidate_sets, greedy_set_cover
from app.services.ddi_feature_builder import PairFeatureBuilder, PairFeatureUnavailableError
from app.services.model_serving import FeatureSchemaError, ModelUnavailableError, ModelInferenceError


@pytest.mark.parametrize("identifier", ["Compound::DB00945", " compound::db00945 ", "DB00945"])
def test_canonical_identity_uses_only_verified_positive_membership(identifier):
    identity = resolve_rule_identity(identifier)
    assert identity["tokens"] == ["nsaid"]
    assert identity["complete"] is False
    assert identity["relationship"] == "PCiC"
    assert evaluate_rule_applicability([identifier])["status"] == "partially_evaluated"


def test_mapping_fact_exists_in_checked_in_graph():
    root = Path(__file__).resolve().parents[2]
    with (root / "data/processed/fragment_edges.csv").open() as stream:
        assert {"source": "Pharmacologic Class::N0000175721", "metaedge": "PCiC", "target": "Compound::DB00945"} in list(csv.DictReader(stream))


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for cross-runtime parity check")
def test_python_javascript_rule_mapping_parity():
    cases = [["Compound::DB00945"], ["DB00945", "warfarin"], ["Compound::DB99999"], ["maoi", "ssri"], []]
    script = "import {evaluateRuleApplicability} from './backend/src/rules/contraindications.js'; console.log(JSON.stringify(JSON.parse(process.argv[1]).map(evaluateRuleApplicability)));"
    actual = subprocess.check_output(["node", "--input-type=module", "-e", script, json.dumps(cases)], cwd=Path(__file__).resolve().parents[2], text=True)
    assert json.loads(actual) == [evaluate_rule_applicability(case) for case in cases]


@pytest.mark.parametrize("identifier", ["Compound::DB00177", "Compound::DB99999", "aspirin", "lisinopril"])
def test_missing_mapping_is_not_a_pass_or_name_guess(identifier):
    result = evaluate_rule_applicability([identifier])
    assert result["status"] == "not_evaluable"
    assert result["clinicallyValidated"] is False
    assert not resolve_rule_identity(identifier)["tokens"]


def test_research_rules_and_final_optimizer_union_use_same_mapping():
    assert check_hard_contraindications(["Compound::DB00945", "warfarin"])["pair"] == ["warfarin", "nsaid"]
    assert evaluate_rule_applicability(["maoi", "ssri"])["status"] == "evaluated"
    candidates = [{"candidateSetId": str(i), "drugs": [drug], "treatedDiseaseIds": [disease], "status": "accepted", "coverage": .5}
                  for i, (drug, disease) in enumerate([("Compound::DB00945", "d1"), ("warfarin", "d2")])]
    result = optimize_candidate_sets(candidates, ["d1", "d2"], {"minimumCoverage": 1})
    assert result["selectedDrugs"] == ["Compound::DB00945"]
    assert result["ruleEvaluation"]["status"] == "partially_evaluated"
    assert greedy_set_cover(["Compound::DB00945", "warfarin"], []) == ["Compound::DB00945"]


@pytest.mark.skipif(not (Path(__file__).resolve().parents[2] / "models/sprint5/random_forest_ddi_pipeline.joblib").is_file(), reason="Frozen deployment artifact is not distributed in source-only CI")
def test_real_partial_candidate_keeps_supported_pair_and_identifies_missing_ids():
    candidate = {"drugs": ["Compound::DB00177", "Compound::DB00187", "Compound::DB00796"], "rank": 7, "graphEvidence": {"paths": []}}
    result = main._apply_pair_predictions(candidate)
    assert result["mlStatus"] == "partial"
    assert len(result["mlPrediction"]["pairs"]) == 1
    failures = result["mlPrediction"]["unavailablePairs"]
    assert len(failures) == 2
    assert all(failure["reasonCode"] == "missing_drug_mapping" for failure in failures)
    assert all(failure["missingDrugIds"] == ["Compound::DB00796"] for failure in failures)
    assert all("predictedSeverity" not in failure for failure in failures)
    assert result["graphEvidence"] == candidate["graphEvidence"] and result["rank"] == 7
    assert all(key not in str(result) for key in ["probability", "confidence", "safetyScore"])


@pytest.mark.parametrize("error,code", [(ModelUnavailableError("missing artifact"), "model_unavailable"),
    (ModelInferenceError("inference failed"), "inference_error"),
    (FeatureSchemaError("invalid feature"), "feature_validation_failure")])
def test_model_and_validation_failures_are_distinct(monkeypatch, error, code):
    def fail(features):
        raise error
    monkeypatch.setattr(main.ddi_model_service, "predict", fail)
    result = main._apply_pair_predictions({"drugs": ["Compound::DB00177", "Compound::DB00187"]})
    assert result["mlStatus"] == "not_applied"
    assert result["mlPrediction"]["pairs"] == []
    assert result["mlPrediction"]["unavailablePairs"][0]["reasonCode"] == code


def test_single_drug_never_loads_features(monkeypatch):
    def fail():
        pytest.fail("single drug must not build pair features")
    monkeypatch.setattr(main, "PairFeatureBuilder", fail)
    assert main._apply_pair_predictions({"drugs": ["Compound::DB00177"]})["mlPrediction"]["reasonCode"] == "not_applicable"


def test_absent_feature_source_is_explicit(tmp_path):
    with pytest.raises(PairFeatureUnavailableError) as caught:
        PairFeatureBuilder(hetionet_mapping_path=tmp_path / "missing.csv")
    assert caught.value.code == "missing_feature_source"
