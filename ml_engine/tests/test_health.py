from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_combination_graph_pipeline(monkeypatch):
    def fake_build_graph_candidates(diseases):
        return {
            "queryId": "graph-test",
            "diseases": ["hypertension"],
            "candidates": [
                {
                    "rank": 1,
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

    response = client.post("/predict/combination", json={"diseases": ["hypertension"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["diseases"] == ["hypertension"]
    assert payload["metadata"]["dataStatus"] == "real_graph"
    assert payload["metadata"]["mlStatus"] == "not_applied"
    assert len(payload["candidates"]) >= 1
