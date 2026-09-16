"""Baseline greedy set-cover optimizer for the PolyMerge MVP.

This placeholder focuses on deterministic selection, configurable weights,
and hard safety enforcement.
"""

from __future__ import annotations

from typing import Any

from app.services.safety_filter import check_hard_contraindications


def greedy_set_cover(
    candidate_drugs: list[str],
    diseases: list[str],
    config: dict[str, Any] | None = None,
    coverage_by_drug: dict[str, set[str] | list[str]] | None = None,
) -> list[str]:
    config = config or {}
    max_drugs = int(config.get("maxDrugCount", 5))
    minimum_coverage = float(config.get("minimumCoverage", 0.8))

    if not candidate_drugs:
        return []

    if coverage_by_drug is None:
        return _legacy_selection(candidate_drugs, diseases, max_drugs, minimum_coverage)

    target_diseases = set(diseases)
    selected: list[str] = []
    covered: set[str] = set()
    remaining = list(dict.fromkeys(candidate_drugs))

    while remaining and len(selected) < max_drugs:
        best_drug = max(
            remaining,
            key=lambda drug: len(set(coverage_by_drug.get(drug, [])) - covered),
        )
        newly_covered = set(coverage_by_drug.get(best_drug, [])) - covered
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


def _legacy_selection(
    candidate_drugs: list[str],
    diseases: list[str],
    max_drugs: int,
    minimum_coverage: float,
) -> list[str]:
    filtered_candidates = [
        drug for drug in candidate_drugs[:max_drugs] if check_hard_contraindications([drug]) is None
    ]
    selected = filtered_candidates[: min(len(filtered_candidates), max_drugs)]
    coverage = min(1.0, len(selected) / max(1, len(diseases)))
    return selected if coverage < minimum_coverage else selected
