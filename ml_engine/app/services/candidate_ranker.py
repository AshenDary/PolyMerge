"""Candidate ranking module for the PolyMerge MVP.

Ranking remains intentionally simple: candidates are ordered by confidence,
coverage, synergy, and fewer drugs, while still preserving explicit evidence status.
"""

from __future__ import annotations

from typing import Any


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        candidates,
        key=lambda candidate: (
            -_score(candidate.get("confidence")),
            -_score(candidate.get("coverage")),
            -_score(candidate.get("synergyScore")),
            int(candidate.get("drugCount", 0)),
        ),
    )


def _score(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
