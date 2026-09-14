from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_combination_demo_pipeline():
    response = client.post("/predict/combination", json={"diseases": ["hypertension"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["diseases"] == ["hypertension"]
    assert payload["metadata"]["dataStatus"] == "demo"
    assert len(payload["candidates"]) >= 1
