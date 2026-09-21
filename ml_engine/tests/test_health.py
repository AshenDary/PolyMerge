from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_combination_rejects_empty_disease_list():
    response = client.post("/predict/combination", json={"diseases": []})
    assert response.status_code == 422


def test_predict_combination_rejects_blank_disease_name():
    response = client.post("/predict/combination", json={"diseases": ["   "]})
    assert response.status_code == 422


def test_predict_combination_rejects_invalid_optimization_config():
    response = client.post(
        "/predict/combination",
        json={
            "diseases": ["hypertension"],
            "optimizationConfig": {"minimumCoverage": 1.5},
        },
    )
    assert response.status_code == 422


def test_predict_combination_graph_pipeline(monkeypatch):
    def fake_build_graph_candidates(diseases, config=None):
        return {
            "queryId": "graph-test",
            "diseases": ["hypertension"],
            "candidates": [
                {
                    "rank": 1,
                    "candidateSetId": "candidate-set:Compound::DB00177",
                    "drugId": "Compound::DB00177",
                    "drugName": "Valsartan",
                    "drugs": ["Compound::DB00177"],
                    "drugNames": ["Valsartan"],
                    "treats": ["hypertension"],
                    "treatedDiseaseIds": ["Disease::DOID:10763"],
                    "coverage": 1.0,
                    "coverageCount": 1,
                    "targetDiseaseCount": 1,
                    "drugCount": 1,
                    "interactionRisk": None,
                    "synergyScore": None,
                    "evidenceLevel": "graph",
                    "confidence": 1.0,
                    "dataStatus": "real_graph",
                    "status": "accepted",
                    "evidence": [],
                    "reasons": [],
                }
            ],
            "metadata": {
                "dataStatus": "real_graph",
                "mlStatus": "not_applied",
                "model": "No predictive ML model applied",
                "modelVersion": None,
                "resolvedDiseases": [
                    {"id": "Disease::DOID:10763", "name": "hypertension"}
                ],
                "missingDiseases": [],
                "candidateCoverage": {
                    "Compound::DB00177": ["Disease::DOID:10763"]
                },
            },
        }

    import main

    monkeypatch.setattr(main, "build_graph_candidates", fake_build_graph_candidates)

    response = client.post(
        "/predict/combination",
        json={"diseases": ["hypertension"], "optimizationConfig": {"maxDrugCount": 1}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["diseases"] == ["hypertension"]
    assert payload["metadata"]["dataStatus"] == "real_graph"
    assert payload["metadata"]["mlStatus"] == "not_applied"
    assert payload["metadata"]["selectedDrugs"] == ["Compound::DB00177"]
    assert payload["metadata"]["selectedDrugCount"] == 1
    assert payload["metadata"]["coverage"] == 1.0
    assert payload["metadata"]["coveredDiseaseIds"] == ["Disease::DOID:10763"]
    assert payload["metadata"]["optimization"]["selectedDrugCount"] == 1
    assert payload["metadata"]["selectedCandidateSetIds"] == [
        "candidate-set:Compound::DB00177"
    ]
    assert len(payload["candidates"]) >= 1


def test_predict_candidate_sets_returns_structured_contract(monkeypatch):
    captured = {}

    def fake_build_graph_candidates(diseases, config=None):
        captured["diseases"] = diseases
        captured["config"] = config
        return {
            "queryId": "candidate-set-test",
            "diseases": ["hypertension", "type 2 diabetes mellitus"],
            "candidates": [
                {
                    "rank": 1,
                    "candidateSetId": "candidate-set:drug-a+drug-b",
                    "drugId": "candidate-set:drug-a+drug-b",
                    "drugName": "Drug A + Drug B",
                    "drugs": ["drug-a", "drug-b"],
                    "drugNames": ["Drug A", "Drug B"],
                    "treatedDiseaseIds": ["disease-1", "disease-2"],
                    "uncoveredDiseaseIds": [],
                    "coverage": 1.0,
                    "drugCount": 2,
                    "status": "accepted",
                    "rejectionReasons": [],
                    "evidence": [{"source": "Hetionet", "relationship": "CtD"}],
                    "dataStatus": "real_graph",
                    "interactionRisk": None,
                    "synergyScore": None,
                }
            ],
            "metadata": {
                "dataStatus": "real_graph",
                "mlStatus": "not_applied",
                "model": "No predictive ML model applied",
                "modelVersion": None,
                "graph": "Hetionet v1.0 filtered PolyMerge fragment",
                "resolvedDiseases": [
                    {"id": "disease-1", "name": "hypertension"},
                    {"id": "disease-2", "name": "type 2 diabetes mellitus"},
                ],
                "missingDiseases": [],
            },
        }

    import main

    monkeypatch.setattr(main, "build_graph_candidates", fake_build_graph_candidates)
    response = client.post(
        "/predict/candidate-sets",
        json={
            "diseaseIds": ["disease-1", "disease-2"],
            "candidateSetConfig": {"maxDrugCount": 3, "maxCandidateSets": 25},
            "optimizationConfig": {"maxDrugCount": 3, "minimumCoverage": 1.0},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured == {
        "diseases": ["disease-1", "disease-2"],
        "config": {"maxDrugCount": 3, "minimumCoverage": 1.0, "maxCandidateSets": 25},
    }
    assert payload["diseaseIds"] == ["disease-1", "disease-2"]
    assert payload["diseases"][0]["id"] == "disease-1"
    assert payload["candidateSets"][0]["candidateSetId"] == "candidate-set:drug-a+drug-b"
    assert payload["candidateSets"][0]["drugs"] == ["drug-a", "drug-b"]
    assert payload["candidateSets"][0]["coverage"] == 1.0
    assert payload["candidateSets"][0]["status"] == "accepted"
    assert payload["candidateSets"][0]["evidence"][0]["source"] == "Hetionet"
    assert payload["candidateSets"][0]["dataStatus"] == "real_graph"
    assert payload["candidateSets"][0]["mlStatus"] == "not_applied"
    assert payload["candidateSets"][0]["interactionRisk"] is None
    assert payload["candidateSets"][0]["synergyScore"] is None


def test_predict_candidate_sets_rejects_unknown_disease_ids(monkeypatch):
    def fake_build_graph_candidates(diseases, config=None):
        return {
            "queryId": "unknown-disease-test",
            "diseases": [],
            "candidates": [],
            "metadata": {
                "dataStatus": "real_graph",
                "mlStatus": "not_applied",
                "model": "No predictive ML model applied",
                "modelVersion": None,
                "resolvedDiseases": [],
                "missingDiseases": diseases,
            },
        }

    import main

    monkeypatch.setattr(main, "build_graph_candidates", fake_build_graph_candidates)
    response = client.post(
        "/predict/candidate-sets",
        json={"diseaseIds": ["Disease::DOID:DOES-NOT-EXIST"]},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["unknownDiseaseIds"] == [
        "Disease::DOID:DOES-NOT-EXIST"
    ]


def test_predict_candidate_sets_reports_graph_outage_as_service_unavailable(monkeypatch):
    def fake_build_graph_candidates(diseases, config=None):
        return {
            "queryId": "graph-unavailable-test",
            "diseases": [],
            "candidates": [],
            "metadata": {
                "dataStatus": "graph_unavailable",
                "mlStatus": "not_applied",
                "model": "No predictive ML model applied",
                "modelVersion": None,
                "resolvedDiseases": [],
                "missingDiseases": diseases,
                "warning": "Neo4j query failed",
            },
        }

    import main

    monkeypatch.setattr(main, "build_graph_candidates", fake_build_graph_candidates)
    response = client.post(
        "/predict/candidate-sets",
        json={"diseaseIds": ["Disease::DOID:10763"]},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "Graph service unavailable"


def test_predict_candidate_sets_rejects_invalid_generation_config():
    response = client.post(
        "/predict/candidate-sets",
        json={
            "diseaseIds": ["Disease::DOID:10763"],
            "candidateSetConfig": {"maxCandidateSets": 0},
        },
    )
    assert response.status_code == 422
