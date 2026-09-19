"""PolyMerge ML Engine -- FastAPI service.

This service intentionally keeps the current MVP lightweight while exposing the
research-oriented pipeline shape the repository will evolve toward.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class CombinationResponse(BaseModel):
    queryId: str
    diseases: list[str]
    candidates: list[dict[str, Any]]
    metadata: dict[str, Any]


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


@app.post("/predict/combination")
async def predict_combination(payload: CombinationRequest) -> CombinationResponse:
    """Return research candidates from represented knowledge-graph relationships.

    Predictive ML/DDI/synergy scores are not applied in this phase. The response
    distinguishes real graph evidence from future model fields.
    """
    diseases = payload.diseases

    optimization_config = payload.optimizationConfig.model_dump(exclude_none=True)
    result = build_graph_candidates(diseases, config=optimization_config)

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

    return CombinationResponse(**result)
