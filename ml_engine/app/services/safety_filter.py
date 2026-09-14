"""Deterministic safety filtering for PolyMerge.

The safety layer runs independently from model scoring and can reject a
candidate even when the model predicts low risk.
"""

from __future__ import annotations


ABSOLUTE_CONTRAINDICATION_PAIRS = [
    ("maoi", "ssri"),
    ("warfarin", "nsaid"),
    ("ace_inhibitor", "potassium_sparing_diuretic"),
]


def check_hard_contraindications(drug_set: list[str]) -> dict[str, object] | None:
    normalized = [str(drug).strip().lower() for drug in drug_set]

    for first, second in ABSOLUTE_CONTRAINDICATION_PAIRS:
        if first in normalized and second in normalized:
            return {
                "type": "hard_contraindication",
                "pair": [first, second],
                "message": f"Absolute contraindication: {first} + {second}",
            }

    return None
