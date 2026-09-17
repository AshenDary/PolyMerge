"""Baseline greedy set-cover optimizer for graph-derived research candidates."""

from __future__ import annotations

from typing import Any

from app.services.safety_filter import check_hard_contraindications


DEFAULT_OPTIMIZATION_CONFIG = {
    "maxDrugCount": 5,
    "minimumCoverage": 0.8,
}


def optimize_set_cover(
    candidate_drugs: list[str],
    diseases: list[str],
    coverage_by_drug: dict[str, set[str] | list[str]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a research candidate set from a graph-derived coverage matrix."""
    effective_config = _optimization_config(config)
    target_diseases = list(dict.fromkeys(diseases))
    coverage_matrix = _coverage_matrix(candidate_drugs, target_diseases, coverage_by_drug)
    selected_drugs = greedy_set_cover(
        candidate_drugs,
        target_diseases,
        config=effective_config,
        coverage_by_drug=coverage_matrix,
    )
    covered_diseases = sorted(
        set().union(*(set(coverage_matrix[drug]) for drug in selected_drugs))
        if selected_drugs
        else set()
    )

    return {
        "selectedDrugs": selected_drugs,
        "selectedDrugCount": len(selected_drugs),
        "coveredDiseaseIds": covered_diseases,
        "uncoveredDiseaseIds": [
            disease for disease in target_diseases if disease not in covered_diseases
        ],
        "coverage": len(covered_diseases) / len(target_diseases) if target_diseases else 0.0,
        "targetDiseaseCount": len(target_diseases),
        "coverageMatrix": coverage_matrix,
        "config": effective_config,
        "dataStatus": "real_graph",
        "disclaimer": "Coverage is knowledge-graph treatment coverage, not a clinical efficacy claim.",
    }


def greedy_set_cover(
    candidate_drugs: list[str],
    diseases: list[str],
    config: dict[str, Any] | None = None,
    coverage_by_drug: dict[str, set[str] | list[str]] | None = None,
) -> list[str]:
    config = _optimization_config(config)
    max_drugs = config["maxDrugCount"]
    minimum_coverage = config["minimumCoverage"]

    if not candidate_drugs:
        return []

    if coverage_by_drug is None:
        return _legacy_selection(candidate_drugs, max_drugs)

    target_diseases = set(diseases)
    selected: list[str] = []
    covered: set[str] = set()
    remaining = list(dict.fromkeys(candidate_drugs))

    while remaining and len(selected) < max_drugs:
        best_drug = max(
            remaining,
            key=lambda drug: len(
                (set(coverage_by_drug.get(drug, [])) & target_diseases) - covered
            ),
        )
        newly_covered = (set(coverage_by_drug.get(best_drug, [])) & target_diseases) - covered
        if not newly_covered:
            break

        violation = check_hard_contraindications([*selected, best_drug])
        remaining.remove(best_drug)
        if violation is not None:
            continue

        selected.append(best_drug)
        covered.update(newly_covered)
        if target_diseases and len(covered & target_diseases) / len(target_diseases) >= minimum_coverage:
            break

    return selected


def _optimization_config(config: dict[str, Any] | None) -> dict[str, Any]:
    supplied = config or {}
    max_drugs = max(0, int(supplied.get("maxDrugCount", DEFAULT_OPTIMIZATION_CONFIG["maxDrugCount"])))
    minimum_coverage = min(
        1.0,
        max(0.0, float(supplied.get("minimumCoverage", DEFAULT_OPTIMIZATION_CONFIG["minimumCoverage"]))),
    )
    return {"maxDrugCount": max_drugs, "minimumCoverage": minimum_coverage}


def _coverage_matrix(
    candidate_drugs: list[str],
    diseases: list[str],
    coverage_by_drug: dict[str, set[str] | list[str]],
) -> dict[str, list[str]]:
    target_diseases = set(diseases)
    return {
        drug: sorted(set(coverage_by_drug.get(drug, [])) & target_diseases)
        for drug in dict.fromkeys(candidate_drugs)
    }


def _legacy_selection(
    candidate_drugs: list[str],
    max_drugs: int,
) -> list[str]:
    filtered_candidates = [
        drug for drug in candidate_drugs[:max_drugs] if check_hard_contraindications([drug]) is None
    ]
    selected = filtered_candidates[: min(len(filtered_candidates), max_drugs)]
    return selected
