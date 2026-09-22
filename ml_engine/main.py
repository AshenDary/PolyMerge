"""PolyMerge ML Engine -- FastAPI service.

This service intentionally keeps the current MVP lightweight while exposing the
research-oriented pipeline shape the repository will evolve toward.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.candidate_generator import build_graph_candidates
from app.services.candidate_ranker import rank_candidates
from app.services.knowledge_graph import get_available_diseases, get_drug_metadata
from app.services.set_cover_optimizer import optimize_candidate_sets

# Single shared .env lives at the repo root, not inside ml_engine/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="PolyMerge ML Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    mlStatus: Literal["not_applied"]
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
    mlStatus: Literal["not_applied"]
    graph: Optional[str] = None
    dataset: Optional[str] = None
    model: str
    modelVersion: None = None
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


@app.get("/api/diseases")
async def diseases():
    return {"diseases": get_available_diseases()}


@app.get("/api/drugs/{drug_id}")
async def drug_by_id(drug_id: str):
    drug = get_drug_metadata(drug_id)
    if drug is None:
        return {"error": "Drug not found"}
    return drug


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
    ml_status = metadata.get("mlStatus", "not_applied")

    candidate_sets = []
    for candidate in result.get("candidates", []):
        treated_ids = candidate.get("treatedDiseaseIds", [])
        candidate_sets.append({
            **candidate,
            "uncoveredDiseaseIds": candidate.get(
                "uncoveredDiseaseIds",
                [disease_id for disease_id in target_disease_ids if disease_id not in treated_ids],
            ),
            "rejectionReasons": candidate.get("rejectionReasons", []),
            "dataStatus": candidate.get("dataStatus", metadata["dataStatus"]),
            "mlStatus": candidate.get("mlStatus", ml_status),
            "interactionRisk": None,
            "synergyScore": None,
        })

    return {
        "queryId": result["queryId"],
        "diseaseIds": target_disease_ids,
        "diseases": resolved_diseases,
        "candidateSets": candidate_sets,
        "metadata": metadata,
    }


@app.post("/predict/candidate-sets", response_model=CandidateSetResponse)
async def predict_candidate_sets(payload: CandidateSetRequest) -> CandidateSetResponse:
    """Return graph-derived multi-drug research candidate sets."""
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
                "warning": result["metadata"].get("warning"),
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
    result = _run_candidate_set_pipeline(
        payload.diseases,
        optimization_config,
        optimization_config,
    )

    return CombinationResponse(**result)
