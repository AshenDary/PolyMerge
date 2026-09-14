"""Baseline greedy set-cover optimizer for the PolyMerge MVP.

This placeholder focuses on deterministic selection, configurable weights,
and hard safety enforcement.
"""

from __future__ import annotations

from typing import Any

from app.services.safety_filter import check_hard_contraindications


def greedy_set_cover(candidate_drugs: list[str], diseases: list[str], config: dict[str, Any] | None = None) -> list[str]:
    config = config or {}
    max_drugs = int(config.get("maxDrugCount", 5))
    minimum_coverage = float(config.get("minimumCoverage", 0.8))

    if not candidate_drugs:
        return []

    filtered_candidates = []
    for drug in candidate_drugs[:max_drugs]:
        violation = check_hard_contraindications([drug])
        if violation is None:
            filtered_candidates.append(drug)

    if not filtered_candidates:
        return []

    selected = filtered_candidates[: min(len(filtered_candidates), max_drugs)]

    coverage = min(1.0, len(selected) / max(1, len(diseases)))
    if coverage < minimum_coverage:
        return selected

    return selected
