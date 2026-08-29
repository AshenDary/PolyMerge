"""PolyMerge ML Engine -- FastAPI service.

Decoupled from the Fastify backend; the two communicate only via HTTP/JSON.
Never import heavy PyTorch code paths into Node.js -- this process owns all
GNN inference and combinatorial search.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    drugSet: list[str]
    scores: dict[str, float] = {}


@app.get("/health")
async def health():
    """Liveness check consumed by the Fastify backend and docker-compose."""
    return {"status": "ok", "service": "polymerge-ml-engine"}


@app.post("/predict/combination", response_model=CombinationResponse)
async def predict_combination(payload: CombinationRequest) -> CombinationResponse:
    """Stub endpoint -- replace with GNN scoring + set-cover search (Sprint 2-3).

    Returns an empty candidate set for now so the backend's contract is
    testable end-to-end before the real model exists, matching the Sprint 1
    goal in ROADMAP.md: "end-to-end connectivity without AI".
    """
    return CombinationResponse(drugSet=[], scores={})
