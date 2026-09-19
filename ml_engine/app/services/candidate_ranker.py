"""Candidate ranking module for the PolyMerge MVP.

Ranking remains intentionally simple: accepted candidates are ordered by
coverage, fewer drugs, confidence, and evidence status.
"""

from __future__ import annotations

from typing import Any


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            candidate.get("status") == "rejected",
            -_score(candidate.get("coverage")),
            int(candidate.get("drugCount", 0)),
            -_score(candidate.get("confidence")),
            -_score(candidate.get("synergyScore")),
        ),
    )
    return [
        {**candidate, "rank": index}
        for index, candidate in enumerate(ranked, start=1)
    ]


def _score(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
