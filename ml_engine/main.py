"""PolyMerge ML Engine -- FastAPI service.

This service intentionally keeps the current MVP lightweight while exposing the
research-oriented pipeline shape the repository will evolve toward.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from itertools import combinations
from pathlib import Path
from typing import Any, Callable, Literal, Optional
from threading import BoundedSemaphore
import anyio
from starlette.concurrency import run_in_threadpool

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.candidate_generator import build_graph_candidates, CandidateBudgetExceeded
from app.services.ddi_feature_builder import PairFeatureBuilder, PairFeatureUnavailableError
from app.services.candidate_ranker import rank_candidates
from app.services.knowledge_graph import get_available_diseases, get_drug_metadata
from app.services.model_serving import (
    FeatureSchemaError,
    ModelUnavailableError,
    ddi_model_service,
)
from app.services.set_cover_optimizer import optimize_candidate_sets

# Single shared .env lives at the repo root, not inside ml_engine/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Warm the singleton model once; absence degrades inference, not liveness."""
    try:
        ddi_model_service.load()
    except ModelUnavailableError:
        pass
    yield


app = FastAPI(title="PolyMerge ML Engine", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
_analysis_slot = BoundedSemaphore(1)


async def _bounded_analysis(function: Callable[..., Any], *args: Any) -> Any:
    if not _analysis_slot.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Analysis busy; try again shortly.", headers={"Retry-After": "2"})

    def execute() -> Any:
        try:
            return function(*args)
        finally:
            _analysis_slot.release()

    # Hold admission until work actually ends, including when a client disconnects.
    with anyio.CancelScope(shield=True):
        return await run_in_threadpool(execute)

@app.middleware("http")
async def private_request_guard(request: Request, call_next: Callable[..., Any]) -> Any:
    # This service is server-to-server only, with no browser CORS surface.
    if request.headers.get("origin"):
        return JSONResponse(status_code=403, content={"error": "Browser access is not permitted"})
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 32768:
            return JSONResponse(status_code=413, content={"error": "Request body too large"})
    request._body = bytes(body)
    try:
        return await call_next(request)
    except Exception:
        return JSONResponse(status_code=503, content={"error": "Analysis is temporarily unavailable. Please try again."})


class OptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maxDrugCount: Optional[int] = Field(default=None, ge=0, le=50)
    minimumCoverage: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class CandidateSetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maxDrugCount: Optional[int] = Field(default=None, ge=1, le=10)
    maxCandidateSets: Optional[int] = Field(default=None, ge=1, le=500)


class CombinationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diseases: list[str] = Field(min_length=1, max_length=10)
    optimizationConfig: OptimizationConfig = Field(default_factory=OptimizationConfig)

    @field_validator("diseases")
    @classmethod
    def validate_diseases(cls, diseases: list[str]) -> list[str]:
        normalized = [disease.strip() for disease in diseases]
        if any(not disease for disease in normalized):
            raise ValueError("disease names and IDs must not be blank")
        return list(dict.fromkeys(normalized))


class CandidateSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diseaseIds: list[str] = Field(min_length=1, max_length=10)
    candidateSetConfig: CandidateSetConfig = Field(default_factory=CandidateSetConfig)
    optimizationConfig: OptimizationConfig = Field(default_factory=OptimizationConfig)

    @field_validator("diseaseIds")
    @classmethod
    def validate_disease_ids(cls, disease_ids: list[str]) -> list[str]:
        normalized = [disease_id.strip() for disease_id in disease_ids]
        if any(not disease_id for disease_id in normalized):
            raise ValueError("disease IDs must not be blank")
        return list(dict.fromkeys(normalized))


class DDISeverityRequest(BaseModel):
    """The reviewed 55-feature pair contract for frozen-model inference."""

    model_config = ConfigDict(extra="forbid")

    features: dict[str, Any]


class CombinationResponse(BaseModel):
    queryId: str
    diseases: list[str]
    candidates: list[dict[str, Any]]
    metadata: dict[str, Any]


class DiseaseReference(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str


class CandidateSetResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidateSetId: str
    rank: int = Field(ge=1)
    drugs: list[str] = Field(min_length=1)
    drugNames: list[str]
    treatedDiseaseIds: list[str]
    uncoveredDiseaseIds: list[str]
    coverage: float = Field(ge=0.0, le=1.0)
    drugCount: int = Field(ge=1)
    status: Literal["accepted", "rejected"]
    rejectionReasons: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    dataStatus: Literal["real_graph"]
    mlStatus: Literal["applied", "partial", "not_applied"]
    mlPrediction: dict[str, Any] = Field(default_factory=dict)
    interactionRisk: None = None
    synergyScore: None = None

    @field_validator("drugs")
    @classmethod
    def validate_drug_ids(cls, drug_ids: list[str]) -> list[str]:
        normalized = [drug_id.strip() for drug_id in drug_ids]
        if any(not drug_id for drug_id in normalized):
            raise ValueError("candidate drug IDs must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("candidate drug IDs must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_candidate_set_consistency(self):
        if self.drugCount != len(self.drugs) or len(self.drugNames) != len(self.drugs):
            raise ValueError("drugCount, drugs, and drugNames must describe the same set")
        if self.status == "rejected" and not self.rejectionReasons:
            raise ValueError("rejected candidate sets require rejectionReasons")
        return self


class CandidateSetMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    dataStatus: Literal["real_graph"]
    mlStatus: Literal["applied", "not_applied"]
    graph: Optional[str] = None
    dataset: Optional[str] = None
    model: str
    modelVersion: Optional[str] = None
    resolvedDiseases: list[DiseaseReference]
    missingDiseases: list[str]


class CandidateSetResponse(BaseModel):
    queryId: str
    diseaseIds: list[str]
    diseases: list[DiseaseReference]
    candidateSets: list[CandidateSetResult]
    metadata: CandidateSetMetadata


@app.get("/health")
async def health():
    """Liveness check consumed by the Fastify backend and docker-compose."""
    return {"status": "ok", "service": "polymerge-ml-engine"}


@app.get("/health/model")
async def model_health():
    """Report model readiness independently from service liveness."""
    status = ddi_model_service.status()
    return JSONResponse(
        status_code=200 if status["inferenceStatus"] == "ready" else 503,
        content=status,
    )


@app.get("/ready")
async def readiness() -> JSONResponse:
    try:
        ddi_model_service.load()
        catalog = await run_in_threadpool(get_available_diseases)
        if not catalog:
            raise RuntimeError("Graph catalog unavailable")
        return JSONResponse({"status": "ready"})
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)


@app.get("/api/diseases")
async def diseases():
    return {"diseases": get_available_diseases()}


@app.get("/api/drugs/{drug_id}")
async def drug_by_id(drug_id: str):
    drug = get_drug_metadata(drug_id)
    if drug is None:
        return {"error": "Drug not found"}
    return drug


@app.post("/predict/ddi-severity")
async def predict_ddi_severity(payload: DDISeverityRequest):
    """Run only the frozen DDI classifier; graph and hard rules remain separate."""
    try:
        return ddi_model_service.predict(payload.features)
    except FeatureSchemaError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Invalid DDI feature schema",
                "message": str(error),
                "mlStatus": "not_applied",
            },
        ) from error
    except ModelUnavailableError as error:
        return JSONResponse(
            status_code=503,
            content=ddi_model_service.unavailable_response(),
        )


def _run_candidate_set_pipeline(
    disease_ids: list[str],
    candidate_set_config: dict[str, Any],
    optimization_config: dict[str, Any],
) -> dict[str, Any]:
    generation_config = {**optimization_config, **candidate_set_config}
    result = build_graph_candidates(disease_ids, config=generation_config)
    result["candidates"] = rank_candidates(result["candidates"])

    target_disease_ids = [
        disease["id"] for disease in result["metadata"].get("resolvedDiseases", [])
    ]
    optimization = optimize_candidate_sets(
        result["candidates"],
        target_disease_ids,
        config=optimization_config,
    )
    result["metadata"]["optimization"] = optimization
    result["metadata"]["selectedCandidateSetIds"] = optimization["selectedCandidateSetIds"]
    result["metadata"]["selectedCandidateSets"] = optimization["selectedCandidateSets"]
    result["metadata"]["selectedDrugs"] = optimization["selectedDrugs"]
    result["metadata"]["selectedDrugCount"] = optimization["selectedDrugCount"]
    result["metadata"]["coveredDiseaseIds"] = optimization["coveredDiseaseIds"]
    result["metadata"]["uncoveredDiseaseIds"] = optimization["uncoveredDiseaseIds"]
    result["metadata"]["coverage"] = optimization["coverage"]
    result["metadata"]["rejectedCandidateSetIds"] = optimization["rejectedCandidateSetIds"]
    return result


def _candidate_set_response(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result["metadata"]
    resolved_diseases = metadata.get("resolvedDiseases", [])
    target_disease_ids = [disease["id"] for disease in resolved_diseases]

    candidate_sets = []
    prediction_context: dict[str, Any] = {"builder": None, "pairs": {}}
    any_applied = False
    for candidate in result.get("candidates", []):
        treated_ids = candidate.get("treatedDiseaseIds", [])
        candidate_with_prediction = _apply_pair_predictions(candidate, prediction_context)
        any_applied = any_applied or candidate_with_prediction.get("mlStatus") in ("applied", "partial")
        candidate_sets.append({
            **candidate_with_prediction,
            "uncoveredDiseaseIds": candidate.get(
                "uncoveredDiseaseIds",
                [disease_id for disease_id in target_disease_ids if disease_id not in treated_ids],
            ),
            "rejectionReasons": candidate.get("rejectionReasons", []),
            "dataStatus": candidate.get("dataStatus", metadata["dataStatus"]),
            "interactionRisk": None,
            "synergyScore": None,
        })
    if any_applied:
        metadata = {
            **metadata,
            "mlStatus": "applied",
            "model": "RandomForestClassifier",
            "modelVersion": next(
                (
                    pair["model"]["version"]
                    for candidate in candidate_sets
                    for pair in candidate.get("mlPrediction", {}).get("pairs", [])
                    if pair.get("model", {}).get("version")
                ),
                metadata.get("modelVersion"),
            ),
        }

    return {
        "queryId": result["queryId"],
        "diseaseIds": target_disease_ids,
        "diseases": resolved_diseases,
        "candidateSets": candidate_sets,
        "metadata": metadata,
    }


def _apply_pair_predictions(candidate: dict[str, Any], context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    drugs = sorted(candidate.get("drugs", []))
    if len(drugs) < 2:
        return {
            **candidate,
            "mlStatus": "not_applied",
            "mlPrediction": {
                "status": "not_applied",
                "pairs": [],
                "reason": "At least two drugs are required for pair-level DDI inference.",
                "reasonCode": "not_applicable",
                "unavailablePairs": [],
            },
        }

    # Both successful and unsupported outcomes belong only to this request snapshot.
    context = context if context is not None else {"builder": None, "pairs": {}}
    predicted_pairs, unavailable_pairs = [], []
    failures = context.setdefault("failures", {})
    for drug_a, drug_b in combinations(drugs, 2):
        key = (drug_a, drug_b)
        try:
            if key in failures:
                unavailable_pairs.append(failures[key])
                continue
            if context["builder"] is None:
                context["builder"] = PairFeatureBuilder()
            builder = context["builder"]
            if key not in context["pairs"]:
                features = builder.build_features(drug_a, drug_b)
                context["pairs"][key] = ddi_model_service.predict(features)
            prediction = context["pairs"][key]
            predicted_pairs.append({
                "drugPair": [drug_a, drug_b],
                "predictedSeverity": prediction["predictedClass"],
                "model": prediction["model"],
                "inferenceStatus": prediction["inferenceStatus"],
            })
        except (PairFeatureUnavailableError, FeatureSchemaError, ModelUnavailableError) as error:
            code = error.code if isinstance(error, PairFeatureUnavailableError) else "feature_validation_failure" if isinstance(error, FeatureSchemaError) else getattr(error, "code", "model_unavailable")
            reason = str(error) if isinstance(error, PairFeatureUnavailableError) else "Pair prediction is temporarily unavailable."
            failure = {"drugPair": [drug_a, drug_b], "reasonCode": code, "reason": reason,
                       "missingDrugIds": getattr(error, "missing_drug_ids", [])}
            failures[key] = failure
            unavailable_pairs.append(failure)

    status = "partial" if predicted_pairs and unavailable_pairs else "applied" if predicted_pairs else "not_applied"
    return {
        **candidate,
        "mlStatus": status,
        "mlPrediction": {
            "status": status,
            "pairs": predicted_pairs,
            "unavailablePairs": unavailable_pairs,
            **({"reason": unavailable_pairs[0]["reason"], "reasonCode": unavailable_pairs[0]["reasonCode"]} if unavailable_pairs else {}),
        },
    }


@app.post("/predict/candidate-sets", response_model=CandidateSetResponse)
async def predict_candidate_sets(payload: CandidateSetRequest) -> CandidateSetResponse:
    """Return graph-derived multi-drug research candidate sets."""
    try:
        return await _bounded_analysis(_execute_candidate_sets, payload)
    except CandidateBudgetExceeded as error:
        raise HTTPException(status_code=422, detail="Analysis work limit exceeded; select fewer diseases or drugs") from error


def _execute_candidate_sets(payload: CandidateSetRequest) -> CandidateSetResponse:
    result = _run_candidate_set_pipeline(
        payload.diseaseIds,
        payload.candidateSetConfig.model_dump(exclude_none=True),
        payload.optimizationConfig.model_dump(exclude_none=True),
    )
    if result["metadata"].get("dataStatus") == "graph_unavailable":
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Graph service unavailable",
                "warning": "Graph analysis is temporarily unavailable.",
            },
        )
    missing_disease_ids = result["metadata"].get("missingDiseases", [])
    if missing_disease_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Unknown disease IDs",
                "unknownDiseaseIds": missing_disease_ids,
            },
        )
    return CandidateSetResponse(**_candidate_set_response(result))


@app.post("/predict/combination")
async def predict_combination(payload: CombinationRequest) -> CombinationResponse:
    """Return research candidates from represented knowledge-graph relationships.

    Predictive ML/DDI/synergy scores are not applied in this phase. The response
    distinguishes real graph evidence from future model fields.
    """
    optimization_config = payload.optimizationConfig.model_dump(exclude_none=True)
    result = await _bounded_analysis(_run_candidate_set_pipeline,
        payload.diseases,
        optimization_config,
        optimization_config,
    )

    return CombinationResponse(**result)
