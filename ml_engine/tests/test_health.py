from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_combination_stub():
    response = client.post("/predict/combination", json={"diseases": ["hypertension"]})
    assert response.status_code == 200
    assert response.json() == {"drugSet": [], "scores": {}}
