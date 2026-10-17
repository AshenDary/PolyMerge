from __future__ import annotations

from fastapi.testclient import TestClient
import main


def test_private_service_rejects_browser_origins() -> None:
    response = TestClient(main.app).get("/api/diseases", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


def test_private_service_rejects_large_bodies_and_invalid_payloads() -> None:
    client = TestClient(main.app)
    assert client.post("/predict/candidate-sets", json={"data": "a" * 40000}).status_code == 413
    assert client.post("/predict/candidate-sets", json={"diseaseIds": [], "unexpected": True}).status_code == 422
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_private_service_redacts_unhandled_errors(monkeypatch) -> None:
    def unavailable() -> None:
        raise RuntimeError("neo4j://admin:secret@private-host/model.joblib")
    monkeypatch.setattr(main, "get_available_diseases", unavailable)
    response = TestClient(main.app).get("/api/diseases")
    assert response.status_code == 503
    assert "secret" not in response.text
    assert "private-host" not in response.text


def test_model_status_never_exposes_paths(tmp_path) -> None:
    from app.services.model_serving import DDIModelService
    service = DDIModelService(artifact_path=tmp_path / "secret.joblib")
    assert service.status()["reason"] == "Frozen model unavailable"
    assert "secret" not in str(service.unavailable_response())


def test_combinatorial_work_is_rejected_before_enumeration() -> None:
    import pytest
    from app.services.candidate_generator import generate_candidate_sets, CandidateBudgetExceeded
    candidates = [{"drugId": str(index)} for index in range(100)]
    with pytest.raises(CandidateBudgetExceeded):
        generate_candidate_sets(candidates, ["d1"], max_drug_count=10)


def test_model_runtime_version_mismatch_fails_closed(monkeypatch) -> None:
    import pytest
    from app.services import model_serving
    monkeypatch.setattr(model_serving.sklearn, "__version__", "incompatible")
    with pytest.raises(model_serving.ModelUnavailableError, match="Runtime scikit-learn"):
        model_serving.DDIModelService().load()
