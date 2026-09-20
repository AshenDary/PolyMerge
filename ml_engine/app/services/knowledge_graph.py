"""Compatibility wrappers around the real Neo4j graph service."""

from __future__ import annotations

from typing import Any, Optional

from app.services.graph_service import GraphService


def get_available_diseases() -> list[dict[str, Any]]:
    return GraphService().search_diseases("")


def search_diseases(query: str) -> list[dict[str, Any]]:
    return GraphService().search_diseases(query)


def get_drug_metadata(drug_id: str) -> Optional[dict[str, Any]]:
    relationships = GraphService().get_drug_relationships(drug_id)
    drug = relationships["drug"]
    if drug is None:
        return None
    return {
        **drug,
        "relationships": {
            "targets": relationships["targets"],
            "sideEffects": relationships["sideEffects"],
        },
    }


def find_treating_drugs(diseases: list[str]) -> dict[str, list[str]]:
    graph_result = GraphService().build_candidate_drugs(diseases)
    disease_to_drugs: dict[str, list[str]] = {
        disease["id"]: [] for disease in graph_result["resolvedDiseases"]
    }
    for candidate in graph_result["candidates"]:
        for disease_id in candidate["treatedDiseaseIds"]:
            disease_to_drugs.setdefault(disease_id, []).append(candidate["drugId"])
    return disease_to_drugs
