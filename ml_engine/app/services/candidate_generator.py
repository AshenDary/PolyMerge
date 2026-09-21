"""Candidate generation from represented knowledge-graph relationships."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Optional

from app.services.graph_service import GRAPH_VERSION, GraphService, Neo4jConnectionError
from app.services.safety_filter import check_hard_contraindications


DEFAULT_CANDIDATE_SET_CONFIG = {
    "maxDrugCount": 3,
    "maxCandidateSets": 100,
}


def build_graph_candidates(
    diseases: list[str],
    graph_service: Optional[GraphService] = None,
    config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    service = graph_service or GraphService()
    candidate_set_config = _candidate_set_config(config)

    try:
        graph_result = service.build_candidate_drugs(diseases)
    except Neo4jConnectionError as error:
        return _empty_result(
            diseases=diseases,
            data_status="graph_unavailable",
            warning=str(error),
        )

    candidates = generate_candidate_sets(
        graph_result["candidates"],
        target_disease_ids=[disease["id"] for disease in graph_result["resolvedDiseases"]],
        max_drug_count=candidate_set_config["maxDrugCount"],
        max_candidate_sets=candidate_set_config["maxCandidateSets"],
    )

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
            "candidateSetGeneration": {
                "maxDrugCount": candidate_set_config["maxDrugCount"],
                "maxCandidateSets": candidate_set_config["maxCandidateSets"],
                "acceptedCount": len(
                    [candidate for candidate in candidates if candidate["status"] == "accepted"]
                ),
                "rejectedCount": len(
                    [candidate for candidate in candidates if candidate["status"] == "rejected"]
                ),
            },
            "coverageDefinition": "Drug-to-disease matrix from represented CtD relationships; not clinical efficacy.",
            "disclaimer": "Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.",
        },
    }


def generate_candidate_sets(
    single_drug_candidates: list[dict[str, Any]],
    target_disease_ids: list[str],
    max_drug_count: int = DEFAULT_CANDIDATE_SET_CONFIG["maxDrugCount"],
    max_candidate_sets: int = DEFAULT_CANDIDATE_SET_CONFIG["maxCandidateSets"],
) -> list[dict[str, Any]]:
    """Generate hard-filtered research candidate sets from graph-derived drugs."""
    target_diseases = list(dict.fromkeys(target_disease_ids))
    target_disease_set = set(target_diseases)
    unique_candidates = _unique_candidates(single_drug_candidates)
    max_size = min(max(1, int(max_drug_count)), len(unique_candidates))
    generated: list[dict[str, Any]] = []

    for size in range(1, max_size + 1):
        for combo in combinations(unique_candidates, size):
            generated.append(_candidate_set_from_combo(combo, target_diseases))

    generated.sort(
        key=lambda candidate: (
            candidate["status"] == "rejected",
            -len(set(candidate["treatedDiseaseIds"]) & target_disease_set),
            candidate["drugCount"],
            candidate["candidateSetId"],
        )
    )

    return [
        {**candidate, "rank": index}
        for index, candidate in enumerate(generated[:max_candidate_sets], start=1)
    ]


def build_demo_candidates(
    diseases: list[str],
    config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Backward-compatible name for the now graph-backed candidate builder."""
    return build_graph_candidates(diseases, config=config)


def _candidate_set_config(config: Optional[dict[str, Any]]) -> dict[str, int]:
    supplied = config or {}
    max_drug_count = max(
        1,
        int(supplied.get("maxDrugCount", DEFAULT_CANDIDATE_SET_CONFIG["maxDrugCount"])),
    )
    max_candidate_sets = max(
        1,
        int(supplied.get("maxCandidateSets", DEFAULT_CANDIDATE_SET_CONFIG["maxCandidateSets"])),
    )
    return {"maxDrugCount": max_drug_count, "maxCandidateSets": max_candidate_sets}


def _unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        drug_id = candidate.get("drugId")
        if not drug_id or drug_id in seen:
            continue
        seen.add(drug_id)
        unique.append(candidate)
    return unique


def _candidate_set_from_combo(
    combo: tuple[dict[str, Any], ...],
    target_disease_ids: list[str],
) -> dict[str, Any]:
    drug_ids = [candidate["drugId"] for candidate in combo]
    drug_names = [candidate.get("drugName", candidate["drugId"]) for candidate in combo]
    treated_disease_ids = sorted(
        set().union(*(set(candidate.get("treatedDiseaseIds", [])) for candidate in combo))
        & set(target_disease_ids)
    )
    treats = sorted(set().union(*(set(candidate.get("treats", [])) for candidate in combo)))
    evidence = [
        evidence_item
        for candidate in combo
        for evidence_item in candidate.get("evidence", [])
    ]
    targets = [target for candidate in combo for target in candidate.get("targets", [])]
    side_effects = [
        side_effect for candidate in combo for side_effect in candidate.get("sideEffects", [])
    ]
    violation = check_hard_contraindications(drug_ids)
    uncovered = [
        disease_id for disease_id in target_disease_ids if disease_id not in treated_disease_ids
    ]
    coverage = len(treated_disease_ids) / len(target_disease_ids) if target_disease_ids else 0.0
    candidate_set_id = "candidate-set:" + "+".join(drug_ids)

    candidate_set = {
        "candidateSetId": candidate_set_id,
        "drugId": drug_ids[0] if len(drug_ids) == 1 else candidate_set_id,
        "drugName": drug_names[0] if len(drug_names) == 1 else " + ".join(drug_names),
        "drugs": drug_ids,
        "drugNames": drug_names,
        "treats": treats,
        "treatedDiseaseIds": treated_disease_ids,
        "uncoveredDiseaseIds": uncovered,
        "coverage": coverage,
        "coverageCount": len(treated_disease_ids),
        "targetDiseaseCount": len(target_disease_ids),
        "drugCount": len(drug_ids),
        "interactionRisk": None,
        "synergyScore": None,
        "evidenceLevel": "graph",
        "confidence": coverage,
        "dataStatus": "real_graph",
        "status": "accepted",
        "evidence": evidence,
        "targets": targets,
        "sideEffects": side_effects,
        "reasons": [
            "Candidate set was generated from represented knowledge-graph treatment relationships.",
            "Coverage is knowledge-graph treatment coverage, not a clinical efficacy claim.",
        ],
        "comparison": {
            "coveredDiseaseIds": treated_disease_ids,
            "uncoveredDiseaseIds": uncovered,
            "coverageCount": len(treated_disease_ids),
            "targetDiseaseCount": len(target_disease_ids),
            "drugCount": len(drug_ids),
            "drugs": [
                {
                    "drugId": candidate["drugId"],
                    "drugName": candidate.get("drugName", candidate["drugId"]),
                    "coveredDiseaseIds": sorted(
                        set(candidate.get("treatedDiseaseIds", [])) & set(target_disease_ids)
                    ),
                    "evidenceCount": len(candidate.get("evidence", [])),
                }
                for candidate in combo
            ],
        },
    }

    if violation is not None:
        candidate_set["status"] = "rejected"
        candidate_set["reason"] = {
            "type": violation["type"],
            "message": violation["message"],
            "pair": violation["pair"],
        }
        candidate_set["rejectionReasons"] = [
            {
                "type": violation["type"],
                "message": violation["message"],
                "pair": violation["pair"],
                "stage": "pre_optimization",
            }
        ]
        candidate_set["reasons"] = [
            "Candidate set contains a prohibited interaction according to the configured safety rule.",
            "The hard safety rule blocks this candidate set before optimization.",
        ]

    return candidate_set


def _empty_result(
    diseases: list[str],
    data_status: str,
    warning: Optional[str] = None,
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
        "coverageDefinition": "Drug-to-disease matrix from represented CtD relationships; not clinical efficacy.",
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
