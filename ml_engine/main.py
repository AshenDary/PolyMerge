from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(
    title="PolyMerge ML Engine",
    description="GNN-backed formulation screening service for PolyMerge.",
    version="0.1.0",
)


class FormulationRequest(BaseModel):
    diseases: list[str] = Field(..., min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "polymerge-ml-engine",
    }


@app.post("/predict")
async def predict_formulation(request: FormulationRequest) -> dict[str, Any]:
    return {
        "diseases": request.diseases,
        "constraints": request.constraints,
        "candidate_formulations": [],
        "message": "Model inference is not implemented yet.",
    }
