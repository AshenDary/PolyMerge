"""Candidate generation from represented knowledge-graph relationships."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.graph_service import GRAPH_VERSION, GraphService, Neo4jConnectionError


def build_graph_candidates(
    diseases: list[str],
    graph_service: GraphService | None = None,
) -> dict[str, Any]:
    service = graph_service or GraphService()

    try:
        graph_result = service.build_candidate_drugs(diseases)
    except Neo4jConnectionError as error:
        return _empty_result(
            diseases=diseases,
            data_status="graph_unavailable",
            warning=str(error),
        )

    candidates = [
        {**candidate, "rank": index}
        for index, candidate in enumerate(graph_result["candidates"], start=1)
    ]

    return {
        "queryId": f"graph-{int(datetime.now(timezone.utc).timestamp())}",
        "diseases": [disease["name"] for disease in graph_result["resolvedDiseases"]],
        "candidates": candidates,
        "metadata": {
            "model": "No predictive ML model applied",
            "modelVersion": None,
            "dataset": "Hetionet fragment",
            "graph": GRAPH_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataStatus": "real_graph",
            "mlStatus": "not_applied",
            "resolvedDiseases": graph_result["resolvedDiseases"],
            "missingDiseases": graph_result["missingDiseases"],
            "candidateCoverage": {
                drug_id: sorted(disease_ids)
                for drug_id, disease_ids in graph_result["candidateCoverage"].items()
            },
            "disclaimer": "Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.",
        },
    }


def build_demo_candidates(diseases: list[str]) -> dict[str, Any]:
    """Backward-compatible name for the now graph-backed candidate builder."""
    return build_graph_candidates(diseases)


def _empty_result(
    diseases: list[str],
    data_status: str,
    warning: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "model": "No predictive ML model applied",
        "modelVersion": None,
        "dataset": "Hetionet fragment",
        "graph": GRAPH_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataStatus": data_status,
        "mlStatus": "not_applied",
        "resolvedDiseases": [],
        "missingDiseases": diseases,
        "candidateCoverage": {},
        "disclaimer": "Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.",
    }
    if warning:
        metadata["warning"] = warning

    return {
        "queryId": f"graph-empty-{int(datetime.now(timezone.utc).timestamp())}",
        "diseases": [],
        "candidates": [],
        "metadata": metadata,
    }
