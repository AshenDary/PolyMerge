"""PolyMerge ML Engine -- FastAPI service.

This service intentionally keeps the current MVP lightweight while exposing the
research-oriented pipeline shape the repository will evolve toward.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.services.candidate_generator import build_demo_candidates
from app.services.candidate_ranker import rank_candidates
from app.services.knowledge_graph import get_available_diseases, get_drug_metadata
from app.services.set_cover_optimizer import greedy_set_cover
from app.services.safety_filter import check_hard_contraindications

# Single shared .env lives at the repo root, not inside ml_engine/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="PolyMerge ML Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CombinationRequest(BaseModel):
    diseases: list[str]


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


@app.post("/predict/combination", response_model=CombinationResponse)
async def predict_combination(payload: CombinationRequest) -> CombinationResponse:
    """MVP endpoint returning demo research candidate data.

    The results are explicitly labeled as mock/demo data until a real model is
    introduced. The response still follows the requested research-oriented
    structure needed by the backend and UI.
    """
    diseases = [str(disease).strip() for disease in payload.diseases if str(disease).strip()]

    if not diseases:
        return CombinationResponse(
            queryId="demo-empty",
            diseases=[],
            candidates=[],
            metadata={
                "dataStatus": "demo",
                "model": "PolyMerge Demo Pipeline",
                "modelVersion": "demo-0.1.0",
            },
        )

    result = build_demo_candidates(diseases)

    for candidate in result["candidates"]:
        violation = check_hard_contraindications(candidate["drugs"])
        if violation:
            candidate["status"] = "rejected"
            candidate["reason"] = {
                "type": "hard_contraindication",
                "message": violation["message"],
                "pair": violation["pair"],
            }
            candidate["reasons"] = [
                "Candidate contains a prohibited interaction according to the configured safety rule.",
                "The hard safety rule blocks this candidate regardless of model score.",
            ]

    result["candidates"] = rank_candidates(result["candidates"])

    selected_drugs = [drug for candidate in result["candidates"] for drug in candidate["drugs"]]
    result["metadata"]["selectedDrugs"] = greedy_set_cover(selected_drugs, diseases)

    return CombinationResponse(**result)
