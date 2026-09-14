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
            -float(candidate.get("confidence", 0.0)),
            -float(candidate.get("coverage", 0.0)),
            -float(candidate.get("synergyScore", 0.0)),
            int(candidate.get("drugCount", 0)),
        ),
    )
