"""PolyMerge ML Engine -- FastAPI service.

This service intentionally keeps the current MVP lightweight while exposing the
research-oriented pipeline shape the repository will evolve toward.
"""
from __future__ import annotations

import os
import threading
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
async def diseases(q: str = ""):
    """Return diseases from the knowledge graph, optionally filtered by query string."""
    from app.services.graph_service import GraphService
    results = GraphService().search_diseases(q)
    return {"diseases": results}


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


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 6 canonical API — used by the final frontend demo
# ─────────────────────────────────────────────────────────────────────────────

# Lightweight in-memory store so the /explain endpoint can look up a previous
# query by its queryId.  Intentionally bounded to 256 entries (LRU-style pop).
_query_store: dict[str, dict[str, Any]] = {}
_query_store_lock = threading.Lock()
_QUERY_STORE_MAX = 256


def _store_result(query_id: str, result: dict[str, Any]) -> None:
    with _query_store_lock:
        if len(_query_store) >= _QUERY_STORE_MAX:
            oldest_key = next(iter(_query_store))
            _query_store.pop(oldest_key, None)
        _query_store[query_id] = result


def _load_result(query_id: str) -> dict[str, Any] | None:
    with _query_store_lock:
        return _query_store.get(query_id)


@app.post("/api/candidate-sets/search")
async def candidate_sets_search(payload: CandidateSetRequest) -> CandidateSetResponse:
    """Canonical Sprint-6 endpoint consumed by the final frontend.

    POST /api/candidate-sets/search
    {
        "diseaseIds": ["Disease::DOID:10763"],
        "candidateSetConfig": {},      // optional
        "optimizationConfig": {}       // optional
    }

    Returns graph-derived multi-drug research candidate sets.  ML DDI/synergy
    prediction is not applied in the current build (mlStatus = "not_applied").
    """
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

    response_data = _candidate_set_response(result)
    _store_result(response_data["queryId"], response_data)
    return CandidateSetResponse(**response_data)


@app.get("/api/candidate-sets/{query_id}/explain")
async def candidate_sets_explain(
    query_id: str,
    format: str = "detailed",
) -> dict[str, Any]:
    """Return a three-channel explainability payload for a previous search.

    GET /api/candidate-sets/{queryId}/explain?format=detailed|comparison|structured

    Three evidence channels are always kept structurally separate:
      - graphEvidence  (blue) — Hetionet knowledge-graph paths
      - rules          (green/red) — deterministic safety rule results
      - predictions    (purple) — ML DDI severity (not_applied in this build)

    No combined safety score is ever produced.
    """
    stored = _load_result(query_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Query '{query_id}' not found. Re-run the search first."},
        )

    candidate_sets: list[dict[str, Any]] = stored.get("candidateSets", [])
    metadata: dict[str, Any] = stored.get("metadata", {})

    # Build detailed explanations
    detailed_explanations = [
        _build_explanation(cs, metadata) for cs in candidate_sets
    ]

    if format == "comparison":
        comparison_view = _build_comparison_view(candidate_sets)
        return {
            "queryId": query_id,
            "diseaseIds": stored.get("diseaseIds", []),
            "format": "comparison",
            "comparisonView": comparison_view,
            "metadata": metadata,
            "disclaimer": _RESEARCH_DISCLAIMER,
            "limitations": _LIMITATIONS,
        }

    if format == "structured":
        return {
            "queryId": query_id,
            "format": "structured",
            "candidateSets": candidate_sets,
            "metadata": metadata,
        }

    # Default: detailed
    return {
        "queryId": query_id,
        "diseaseIds": stored.get("diseaseIds", []),
        "format": "detailed",
        "detailedExplanations": detailed_explanations,
        "metadata": {
            **metadata,
            "candidateCount": len(candidate_sets),
            "acceptedCount": len([c for c in candidate_sets if c.get("status") == "accepted"]),
            "rejectedCount": len([c for c in candidate_sets if c.get("status") == "rejected"]),
        },
        "disclaimer": _RESEARCH_DISCLAIMER,
        "limitations": _LIMITATIONS,
    }


_RESEARCH_DISCLAIMER = (
    "Research decision-support only. "
    "Graph evidence, deterministic rules, and ML predictions are separate evidence channels "
    "that must not be combined into a single 'safety score'. "
    "All evidence requires expert review and appropriate clinical/regulatory validation."
)

_LIMITATIONS = [
    "Graph coverage measures representation in the knowledge graph, not clinical efficacy.",
    "Deterministic rules are hard-coded safety checks, not comprehensive drug interaction databases.",
    "ML predictions are statistical estimates from research models, not clinical validation.",
    "All evidence channels require expert review and appropriate clinical/regulatory validation.",
]


def _build_explanation(cs: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Build a structured three-channel explanation for a single candidate set."""
    is_rejected = cs.get("status") == "rejected"
    graph_ev = cs.get("graphEvidence", {})
    rejection_reasons = cs.get("rejectionReasons", [])
    ml_status = cs.get("mlStatus", metadata.get("mlStatus", "not_applied"))

    # Graph evidence section
    graph_section: dict[str, Any] = {
        "title": "Graph Evidence",
        "type": "graph",
        "icon": "database",
        "color": "blue",
        "content": {
            "summary": {
                "coverage": f"{cs.get('coverage', 0) * 100:.0f}%",
                "treatedCount": len(cs.get("treatedDiseaseIds", [])),
                "uncoveredCount": len(cs.get("uncoveredDiseaseIds", [])),
                "dataStatus": cs.get("dataStatus", "real_graph"),
            },
            "treatmentPaths": [
                p for p in graph_ev.get("paths", []) if p.get("semanticType") == "treatment"
            ],
            "geneContextPaths": [
                p for p in graph_ev.get("paths", []) if p.get("semanticType") == "gene_context"
            ],
            "sideEffectPaths": [
                p for p in graph_ev.get("paths", []) if p.get("semanticType") == "side_effect_context"
            ],
            "allPaths": graph_ev.get("paths", []),
            "provenance": {
                "source": graph_ev.get("source", "Hetionet"),
                "version": graph_ev.get("graphVersion", metadata.get("graph", "")),
                "timestamp": metadata.get("timestamp", ""),
            },
        },
        "disclaimer": (
            "Based on knowledge-graph relationships. "
            "Coverage measures representation, not clinical efficacy."
        ),
    }

    # Deterministic rules section
    if is_rejected and rejection_reasons:
        rules_content = [
            {
                "ruleId": f"rule-{i}",
                "type": r.get("type", "hard_contraindication"),
                "status": "rejected",
                "message": r.get("message", "Safety rule violation"),
                "affectedDrugs": r.get("pair") or r.get("affectedDrugs") or [],
                "source": "PolyMerge Safety Rules",
                "stage": r.get("stage", "pre_optimization"),
            }
            for i, r in enumerate(rejection_reasons)
        ]
    else:
        rules_content = [
            {
                "ruleId": "rule-accepted",
                "type": "accepted",
                "status": "accepted",
                "message": "No contraindications detected",
                "affectedDrugs": [],
                "source": "PolyMerge Safety Rules",
                "stage": "pre_optimization",
            }
        ]

    rules_section: dict[str, Any] = {
        "title": "Safety Rules",
        "type": "rules",
        "icon": "shield",
        "color": "red" if is_rejected else "green",
        "content": rules_content,
        "disclaimer": (
            "Hard-coded safety checks only. "
            "Not a comprehensive drug interaction database. "
            "Rejection is deterministic — not influenced by ML predictions."
        ),
    }

    # ML predictions section
    if ml_status == "applied" and cs.get("predictions"):
        ml_content: dict[str, Any] = {
            "status": "applied",
            "pairs": cs["predictions"],
        }
    else:
        ml_content = {
            "status": "not_available",
            "message": (
                "ML DDI predictions unavailable — service unreachable."
                if ml_status == "unavailable"
                else "ML DDI predictions not applied in this build (graph-only mode)."
            ),
            "pairs": [],
        }

    ml_section: dict[str, Any] = {
        "title": "ML Prediction",
        "type": "predictions",
        "icon": "cpu",
        "color": "purple",
        "content": ml_content,
        "disclaimer": (
            "Statistical estimates from research models — not clinical validation. "
            "Do not use predicted severity as a clinical safety determination."
        ),
    }

    return {
        "candidateId": cs.get("candidateSetId", ""),
        "rank": cs.get("rank", 0),
        "drugs": cs.get("drugNames") or cs.get("drugs") or [],
        "drugIds": cs.get("drugs") or [],
        "status": cs.get("status", "accepted"),
        "sections": [graph_section, rules_section, ml_section],
        "presentation": {
            "statusColor": "red" if is_rejected else "green",
            "coverageBadge": {
                "text": f"{cs.get('coverage', 0) * 100:.0f}% KG Coverage",
                "color": "green" if cs.get("coverage", 0) >= 0.8 else "yellow",
            },
            "mlStatus": ml_status,
            "disclaimer": "Research use only. Not clinical guidance.",
        },
        "overallDisclaimer": (
            "Research decision-support only. All evidence channels require expert review."
        ),
    }


def _build_comparison_view(candidate_sets: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a tabular comparison view across all candidates."""
    headers = ["Rank", "Drugs", "KG Coverage", "Status", "Rules", "ML"]
    rows = []
    for cs in candidate_sets:
        is_rejected = cs.get("status") == "rejected"
        drug_names = " + ".join(cs.get("drugNames") or cs.get("drugs") or [])
        rows.append({
            "rank": cs.get("rank", 0),
            "drugs": drug_names,
            "coverage": f"{cs.get('coverage', 0) * 100:.0f}%",
            "status": cs.get("status", "accepted"),
            "rulesStatus": "✗ Rejected" if is_rejected else "✓ Accepted",
            "mlStatus": cs.get("mlStatus", "not_applied"),
            "visualStyle": "error" if is_rejected else "success",
        })
    return {"headers": headers, "rows": rows}
