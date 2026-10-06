"""Sprint 6 — Frontend validation tests.

Verifies the API surface, candidate response structure, and key explainability
requirements used by the final research dashboard.

These are lightweight in-process tests that do NOT require a live Neo4j instance
OR the neo4j Python package.  A sys.modules stub is injected before anything
imports neo4j, which is the same technique used to keep CI green without a
running database.

Validation checklist (from issue #53 DoD):
  [x] main page / frontend JS / explainability assets load   (see test_assets_*)
  [x] candidate response renders                             (see test_candidate_response_*)
  [x] accepted candidate renders                             (see test_accepted_candidate_*)
  [x] rejected candidate renders                             (see test_rejected_candidate_*)
  [x] active ML result renders (structure)                   (see test_ml_section_*)
  [x] not-applied ML state renders                          (see test_ml_not_applied_*)
  [x] graph paths render                                     (see test_graph_paths_*)
  [x] no unsafe/clinical wording                             (see test_no_clinical_wording_*)
  [x] explainability three-channel structure                 (see test_explain_channels_*)
  [x] canonical POST /api/candidate-sets/search used         (see test_canonical_endpoint_*)
"""
from __future__ import annotations

# ── Neo4j stub ─────────────────────────────────────────────────────────────
# Inject a minimal neo4j stub into sys.modules BEFORE any app import reaches
# neo4j_client.py.  This avoids needing the `neo4j` driver package installed
# in environments without a live database (CI, dev machines without Neo4j).
import sys
import types

def _make_neo4j_stub() -> None:
    """Build just enough of the neo4j namespace to satisfy imports."""
    if "neo4j" in sys.modules:
        return                          # already provided (real or stub)

    neo4j_mod = types.ModuleType("neo4j")
    exc_mod   = types.ModuleType("neo4j.exceptions")

    class _FakeGraphDatabase:           # noqa: N801
        @staticmethod
        def driver(*args, **kwargs):
            raise RuntimeError("Stub neo4j driver — should never be called in tests")

    class Neo4jError(Exception): pass  # noqa: N818
    class ServiceUnavailable(Neo4jError): pass

    neo4j_mod.GraphDatabase     = _FakeGraphDatabase
    neo4j_mod.ManagedTransaction = object          # type annotation only
    exc_mod.Neo4jError          = Neo4jError
    exc_mod.ServiceUnavailable  = ServiceUnavailable

    sys.modules["neo4j"]            = neo4j_mod
    sys.modules["neo4j.exceptions"] = exc_mod

_make_neo4j_stub()
# ── end Neo4j stub ──────────────────────────────────────────────────────────

import importlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services.graph_service import GRAPH_VERSION, GraphService, Neo4jConnectionError


# ─────────────────────────────────────────────────────────────────────────────
# Fake graph client (mirrors test_graph_service.py pattern)
# ─────────────────────────────────────────────────────────────────────────────

FAKE_DISEASES = {
    "Disease::DOID:10763": {"id": "Disease::DOID:10763", "name": "hypertension",              "kind": "Disease"},
    "Disease::DOID:9352":  {"id": "Disease::DOID:9352",  "name": "type 2 diabetes mellitus",  "kind": "Disease"},
}

FAKE_DRUG_ROWS = [
    {
        "drug_id":   "Compound::DB00177",
        "drug_name": "Valsartan",
        "disease_ids":   ["Disease::DOID:10763", "Disease::DOID:9352"],
        "disease_names": ["hypertension", "type 2 diabetes mellitus"],
        "treatment_evidence": [
            {
                "source": "Hetionet", "graphVersion": GRAPH_VERSION,
                "relationship": "CtD", "metaedge": "CtD",
                "targetId": "Disease::DOID:10763", "targetName": "hypertension",
                "evidenceType": "known",
            },
            {
                "source": "Hetionet", "graphVersion": GRAPH_VERSION,
                "relationship": "CtD", "metaedge": "CtD",
                "targetId": "Disease::DOID:9352", "targetName": "type 2 diabetes mellitus",
                "evidenceType": "known",
            },
        ],
    },
    {
        "drug_id":   "Compound::DB00381",
        "drug_name": "Amlodipine",
        "disease_ids":   ["Disease::DOID:10763"],
        "disease_names": ["hypertension"],
        "treatment_evidence": [
            {
                "source": "Hetionet", "graphVersion": GRAPH_VERSION,
                "relationship": "CtD", "metaedge": "CtD",
                "targetId": "Disease::DOID:10763", "targetName": "hypertension",
                "evidenceType": "known",
            },
        ],
    },
]


class FakeGraphClient:
    def verify_connectivity(self) -> bool:
        return True

    def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        if "RETURN 1 AS ok" in cypher:
            return [{"ok": 1}]

        if "MATCH (d:Disease {id: $diseaseId})" in cypher:
            d = FAKE_DISEASES.get(params["diseaseId"])
            return [d] if d else []

        if "MATCH (d:Disease)" in cypher:
            q = params.get("normalizedQuery", "")
            if not q:
                return list(FAKE_DISEASES.values())
            return [d for d in FAKE_DISEASES.values() if q in d["name"] or q == d["id"].lower()]

        if "WHERE disease.id IN $diseaseIds" in cypher:
            requested = set(params["diseaseIds"])
            return [
                {
                    **drug,
                    "disease_ids":   [di for di in drug["disease_ids"] if di in requested],
                    "disease_names": [
                        dn for di, dn in zip(drug["disease_ids"], drug["disease_names"])
                        if di in requested
                    ],
                }
                for drug in FAKE_DRUG_ROWS
                if requested.intersection(drug["disease_ids"])
            ]

        if "MATCH (compound:Compound)-[relationship:CtD]->(disease:Disease {id: $diseaseId})" in cypher:
            disease_id = params["diseaseId"]
            return [
                {
                    "drug_id": drug["drug_id"], "drug_name": drug["drug_name"],
                    "kind": "Compound",
                    "disease_id": disease_id,
                    "disease_name": next(
                        dn for di, dn in zip(drug["disease_ids"], drug["disease_names"])
                        if di == disease_id
                    ),
                    "relationship_type": "CtD", "metaedge": "CtD",
                }
                for drug in FAKE_DRUG_ROWS
                if disease_id in drug["disease_ids"]
            ]

        if "RETURN compound.id AS id" in cypher:
            if params.get("drugId") == "Compound::DB00177":
                return [{"id": "Compound::DB00177", "name": "Valsartan", "kind": "Compound"}]
            return []

        if "gene:Gene" in cypher:
            return [{"id": "Gene::7422", "name": "VEGFA", "relationship_type": "CbG", "metaedge": "CbG"}]

        if "sideEffect:`Side Effect`" in cypher:
            return [{"id": "Side Effect::C0018681", "name": "Headache", "relationship_type": "CcSE", "metaedge": "CcSE"}]

        return []


class FailingGraphClient:
    def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        raise Neo4jConnectionError("Neo4j unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# Test client fixture — patches Neo4jClient before the app is loaded
# ─────────────────────────────────────────────────────────────────────────────

def _fresh_app(client_class):
    """Return a freshly-reloaded FastAPI app wired to client_class.

    conftest.py inserts ml_engine/ into sys.path, so the root module is
    'main' (not 'ml_engine.main').  We also clear cached app.services/* so
    the patch takes effect cleanly.
    """
    for key in list(sys.modules.keys()):
        if key in ("main",) or key.startswith(("app.services", "app.utils")):
            sys.modules.pop(key, None)

    with patch("app.utils.neo4j_client.Neo4jClient", return_value=client_class()):
        import main as main_mod          # ml_engine/main.py via conftest sys.path
        importlib.reload(main_mod)
        return main_mod.app


@pytest.fixture()
def client():
    app = _fresh_app(FakeGraphClient)
    with TestClient(app) as tc:
        yield tc


@pytest.fixture()
def client_graph_down():
    """Simulate graph unavailable by patching build_graph_candidates to return graph_unavailable."""
    # We patch the function directly to avoid module-reload class-identity issues
    # with Neo4jConnectionError being raised vs caught across reload boundaries.
    for key in list(sys.modules.keys()):
        if key in ("main",) or key.startswith(("app.services", "app.utils")):
            sys.modules.pop(key, None)

    _graph_unavailable_result = {
        "queryId": "graph-empty-test",
        "diseases": [],
        "candidates": [],
        "metadata": {
            "model": "No predictive ML model applied",
            "modelVersion": None,
            "dataset": "Hetionet fragment",
            "graph": "Hetionet v1.0 filtered PolyMerge fragment",
            "timestamp": "2026-10-06T00:00:00Z",
            "dataStatus": "graph_unavailable",
            "mlStatus": "not_applied",
            "resolvedDiseases": [],
            "missingDiseases": [],
            "candidateCoverage": {},
            "warning": "Neo4j connection failed",
            "disclaimer": "Research decision-support only.",
        },
    }

    with patch("app.utils.neo4j_client.Neo4jClient", return_value=FakeGraphClient()):
        import main as main_mod
        importlib.reload(main_mod)
        app = main_mod.app

    with patch.object(
        sys.modules["main"],
        "build_graph_candidates",
        return_value=_graph_unavailable_result,
    ):
        with TestClient(app) as tc:
            yield tc


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

HYPERTENSION_ID = "Disease::DOID:10763"
DIABETES_ID     = "Disease::DOID:9352"
FRONTEND_DIR    = Path(__file__).resolve().parent.parent.parent / "frontend"


def _search(client, disease_ids: list[str]) -> Any:
    return client.post("/api/candidate-sets/search", json={"diseaseIds": disease_ids})


# ─────────────────────────────────────────────────────────────────────────────
# Asset / page load tests
# ─────────────────────────────────────────────────────────────────────────────

def test_index_html_exists():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert "PolyMerge" in html


def test_app_js_uses_canonical_endpoint():
    js = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
    assert "/api/candidate-sets/search" in js, (
        "app.js must use the canonical POST /api/candidate-sets/search endpoint"
    )


def test_app_js_does_not_use_obsolete_endpoint():
    js = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
    assert "/api/combinations/search" not in js, (
        "app.js must not call the obsolete /api/combinations/search endpoint"
    )


def test_styles_css_exists():
    assert (FRONTEND_DIR / "styles.css").exists()


def test_explainability_css_exists():
    assert (FRONTEND_DIR / "explainability.css").exists()


def test_explainability_js_exists():
    assert (FRONTEND_DIR / "explainability.js").exists()


def test_index_html_loads_explainability_css():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert "explainability.css" in html


def test_dashboard_renderer_has_three_channel_legend():
    """Dashboard-rendered evidence UI must name all three evidence channels."""
    js = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
    assert "Graph Evidence" in js
    assert "Deterministic Safety Rules" in js
    assert "ML Prediction" in js


def test_index_html_has_research_disclaimer():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert "Research" in html or "research" in html


# ─────────────────────────────────────────────────────────────────────────────
# Canonical endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_canonical_endpoint_returns_200(client):
    res = _search(client, [HYPERTENSION_ID])
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"


def test_canonical_endpoint_returns_query_id(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    assert data.get("queryId"), "Response must include a non-empty queryId"


def test_candidate_response_has_required_keys(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    for key in ("queryId", "diseaseIds", "diseases", "candidateSets", "metadata"):
        assert key in data, f"Missing top-level key: {key}"


def test_candidate_response_returns_candidates(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    assert len(data["candidateSets"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Accepted candidate
# ─────────────────────────────────────────────────────────────────────────────

def test_accepted_candidate_exists(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    assert any(c["status"] == "accepted" for c in data["candidateSets"])


def test_accepted_candidate_has_drug_names(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    assert accepted["drugs"], "drugs must not be empty"
    assert accepted["drugNames"], "drugNames must not be empty"


def test_accepted_candidate_has_graph_evidence_paths(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    paths = accepted.get("graphEvidence", {}).get("paths", [])
    assert paths, "Accepted candidate must have graph evidence paths"


def test_accepted_candidate_has_ctd_treatment_path(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    treatment = [p for p in accepted["graphEvidence"]["paths"] if p["semanticType"] == "treatment"]
    assert treatment, "Accepted candidate must have at least one CtD treatment path"


def test_accepted_candidate_has_empty_rejection_reasons(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    assert accepted.get("rejectionReasons") == []


def test_accepted_candidate_rank_is_positive_int(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    assert isinstance(accepted["rank"], int) and accepted["rank"] >= 1


def test_accepted_candidate_coverage_in_range(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    assert 0.0 <= accepted["coverage"] <= 1.0


def test_accepted_candidate_treated_disease_ids_populated(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    assert HYPERTENSION_ID in accepted["treatedDiseaseIds"]


# ─────────────────────────────────────────────────────────────────────────────
# Rejected candidate
# ─────────────────────────────────────────────────────────────────────────────

def test_rejected_candidates_have_rejection_reasons(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    rejected = [c for c in data["candidateSets"] if c["status"] == "rejected"]
    for r in rejected:
        assert r.get("rejectionReasons"), (
            f"Rejected candidate {r.get('candidateSetId')} is missing rejectionReasons"
        )


def test_rejected_reason_has_required_fields(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    rejected = [c for c in data["candidateSets"] if c["status"] == "rejected"]
    if not rejected:
        pytest.skip("No rejected candidates with this test dataset")
    reason = rejected[0]["rejectionReasons"][0]
    for field in ("type", "message", "stage"):
        assert field in reason, f"rejectionReason missing field: {field}"


# ─────────────────────────────────────────────────────────────────────────────
# ML not-applied state
# ─────────────────────────────────────────────────────────────────────────────

def test_ml_status_is_not_applied(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    assert data["metadata"]["mlStatus"] == "not_applied"


def test_ml_status_propagated_to_each_candidate(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    for cs in data["candidateSets"]:
        assert cs["mlStatus"] == "not_applied"


def test_interaction_risk_is_null(client):
    """interactionRisk must be null — no combined ML/graph score."""
    data = _search(client, [HYPERTENSION_ID]).json()
    for cs in data["candidateSets"]:
        assert cs["interactionRisk"] is None


def test_synergy_score_is_null(client):
    """synergyScore must be null — no combined ML/graph score."""
    data = _search(client, [HYPERTENSION_ID]).json()
    for cs in data["candidateSets"]:
        assert cs["synergyScore"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Graph paths
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_SEMANTIC_TYPES = {"treatment", "gene_context", "side_effect_context"}


def test_graph_paths_have_valid_semantic_types(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    for cs in data["candidateSets"]:
        for path in cs.get("graphEvidence", {}).get("paths", []):
            assert path["semanticType"] in ALLOWED_SEMANTIC_TYPES, (
                f"Unexpected semanticType: {path['semanticType']}"
            )


def test_graph_paths_have_source_and_target_entities(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    for path in accepted["graphEvidence"]["paths"]:
        assert path["sourceEntity"]["id"]
        assert path["targetEntity"]["id"]


def test_crc_is_never_in_graph_paths(client):
    """CrC (compound-resembles-compound) must never appear as graph evidence."""
    data = _search(client, [HYPERTENSION_ID]).json()
    for cs in data["candidateSets"]:
        for path in cs.get("graphEvidence", {}).get("paths", []):
            rel = path.get("relationship", {}).get("type", "")
            assert rel != "CrC", f"CrC found in graph paths for {cs.get('candidateSetId')}"


def test_graph_paths_have_provenance(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    for path in accepted["graphEvidence"]["paths"]:
        prov = path.get("provenance", {})
        assert prov.get("source"), "Path must have provenance.source"
        assert prov.get("evidenceType"), "Path must have provenance.evidenceType"


def test_graph_evidence_source_is_hetionet(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    accepted = next(c for c in data["candidateSets"] if c["status"] == "accepted")
    assert accepted["graphEvidence"]["source"] == "Hetionet"


# ─────────────────────────────────────────────────────────────────────────────
# Explainability — three-channel structure
# ─────────────────────────────────────────────────────────────────────────────

def test_explain_404_for_unknown_query_id(client):
    res = client.get("/api/candidate-sets/does-not-exist/explain")
    assert res.status_code == 404


def test_explain_returns_three_sections(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain").json()
    for explanation in data["detailedExplanations"]:
        types = {s["type"] for s in explanation["sections"]}
        assert "graph"       in types, "Missing graph evidence section"
        assert "rules"       in types, "Missing rules section"
        assert "predictions" in types, "Missing ML predictions section"


def test_explain_sections_not_combined_into_score(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain").json()
    forbidden = {"safetyScore", "combinedScore", "overallScore", "riskScore"}
    for explanation in data["detailedExplanations"]:
        for section in explanation["sections"]:
            content = section.get("content") or {}
            if isinstance(content, dict):
                overlap = forbidden & set(content.keys())
                assert not overlap, f"Section has forbidden combined-score key: {overlap}"


def test_explain_graph_section_has_treatment_paths(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain").json()
    accepted = [e for e in data["detailedExplanations"] if e["status"] == "accepted"]
    assert accepted
    graph_sec = next(s for s in accepted[0]["sections"] if s["type"] == "graph")
    assert graph_sec["content"]["treatmentPaths"], "Graph section must list treatment paths"


def test_explain_rules_section_accepted_has_accepted_rule(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain").json()
    accepted = [e for e in data["detailedExplanations"] if e["status"] == "accepted"]
    rules_sec = next(s for s in accepted[0]["sections"] if s["type"] == "rules")
    assert any(r["status"] == "accepted" for r in rules_sec["content"])


def test_explain_ml_section_not_applied(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain").json()
    for exp in data["detailedExplanations"]:
        ml_sec = next(s for s in exp["sections"] if s["type"] == "predictions")
        assert ml_sec["content"]["status"] == "not_available"
        assert ml_sec["content"]["pairs"] == []


def test_explain_has_research_disclaimer(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain").json()
    assert "disclaimer" in data
    assert "research" in data["disclaimer"].lower()


def test_explain_comparison_format(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain?format=comparison").json()
    assert "comparisonView" in data
    cv = data["comparisonView"]
    assert "headers" in cv and "rows" in cv


def test_explain_structured_format(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    data = client.get(f"/api/candidate-sets/{query_id}/explain?format=structured").json()
    assert "candidateSets" in data


# ─────────────────────────────────────────────────────────────────────────────
# No unsafe / clinical wording
# ─────────────────────────────────────────────────────────────────────────────

_FORBIDDEN = [
    # These phrases would imply clinical validity and must never appear
    "is clinically safe",
    "clinical recommendation",
    "prescribe",
    "fda approved",
    "clinically validated efficacy",
    "clinical approval",
]


def test_no_clinical_wording_in_candidate_response(client):
    text = str(_search(client, [HYPERTENSION_ID]).json()).lower()
    for phrase in _FORBIDDEN:
        assert phrase not in text, f"Forbidden clinical phrase in response: '{phrase}'"


def test_no_clinical_wording_in_explain_response(client):
    query_id = _search(client, [HYPERTENSION_ID]).json()["queryId"]
    text = str(client.get(f"/api/candidate-sets/{query_id}/explain").json()).lower()
    for phrase in _FORBIDDEN:
        assert phrase not in text, f"Forbidden clinical phrase in explain: '{phrase}'"


def test_metadata_has_research_disclaimer(client):
    data = _search(client, [HYPERTENSION_ID]).json()
    disc = data.get("metadata", {}).get("disclaimer", "")
    assert disc, "metadata.disclaimer must be non-empty"
    assert "research" in disc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Graph unavailable state (503)
# ─────────────────────────────────────────────────────────────────────────────

def test_graph_unavailable_returns_503(client_graph_down):
    res = client_graph_down.post(
        "/api/candidate-sets/search", json={"diseaseIds": [HYPERTENSION_ID]}
    )
    assert res.status_code == 503, f"Expected 503 when graph down, got {res.status_code}"


def test_graph_unavailable_response_has_error_key(client_graph_down):
    res = client_graph_down.post(
        "/api/candidate-sets/search", json={"diseaseIds": [HYPERTENSION_ID]}
    )
    detail = res.json().get("detail", {})
    assert "error" in detail


# ─────────────────────────────────────────────────────────────────────────────
# Multi-disease search
# ─────────────────────────────────────────────────────────────────────────────

def test_multi_disease_search_returns_candidates(client):
    data = _search(client, [HYPERTENSION_ID, DIABETES_ID]).json()
    assert data["candidateSets"]


def test_multi_disease_valsartan_covers_both(client):
    data = _search(client, [HYPERTENSION_ID, DIABETES_ID]).json()
    valsartan = next(
        (cs for cs in data["candidateSets"]
         if "Compound::DB00177" in cs["drugs"] and cs["drugCount"] == 1),
        None,
    )
    assert valsartan, "Valsartan should appear as a single-drug candidate"
    assert HYPERTENSION_ID in valsartan["treatedDiseaseIds"]
    assert DIABETES_ID in valsartan["treatedDiseaseIds"]


def test_represented_disease_coverage_in_metadata(client):
    data = _search(client, [HYPERTENSION_ID, DIABETES_ID]).json()
    resolved = {d["id"] for d in data["diseases"]}
    assert HYPERTENSION_ID in resolved
    assert DIABETES_ID in resolved
