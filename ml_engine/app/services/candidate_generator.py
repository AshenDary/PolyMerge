"""Candidate generation module for the PolyMerge MVP.

This module intentionally keeps the implementation deterministic and research-oriented.
It maps selected diseases to candidate drugs and produces a small list of mock
ranked candidates with explicit evidence labeling.
"""

from __future__ import annotations

from typing import Any

from app.services.knowledge_graph import find_treating_drugs


def build_demo_candidates(diseases: list[str]) -> dict[str, Any]:
    disease_map = find_treating_drugs(diseases)

    candidates = []
    for index, disease in enumerate(diseases, start=1):
        candidate_drugs = disease_map.get(disease.lower(), [])
        if not candidate_drugs:
            continue

        candidates.append(
            {
                "rank": index,
                "drugs": candidate_drugs[:2],
                "coverage": 1.0,
                "interactionRisk": 0.12,
                "synergyScore": 0.81,
                "drugCount": min(2, len(candidate_drugs)),
                "evidenceLevel": "medium",
                "confidence": 0.78,
                "dataStatus": "demo",
                "status": "accepted",
                "evidence": [
                    {
                        "source": "Hetionet",
                        "relationship": "treats",
                        "evidenceType": "known",
                        "confidence": None,
                    },
                    {
                        "source": "PolyMerge Demo Pipeline",
                        "relationship": "DDI",
                        "evidenceType": "predicted",
                        "score": 0.12,
                        "modelVersion": "demo-0.1.0",
                    },
                    {
                        "source": "PolyMerge Safety Rules",
                        "evidenceType": "rule",
                        "status": "passed",
                    },
                ],
                "reasons": [
                    "Coverage is computed from treatment relationships represented in the knowledge graph.",
                    "Demo scores are labeled and are not clinical guarantees.",
                ],
            }
        )

    return {
        "queryId": f"demo-{index}",
        "diseases": diseases,
        "candidates": candidates,
        "metadata": {
            "model": "PolyMerge Demo Pipeline",
            "modelVersion": "demo-0.1.0",
            "dataset": "Hetionet fragment",
            "graph": "Neo4j fragment",
            "timestamp": "2026-09-14T00:00:00Z",
            "dataStatus": "demo",
            "disclaimer": "Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.",
        },
    }
