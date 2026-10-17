"""Deterministic safety filtering for PolyMerge.

The safety layer runs independently from model scoring and can reject a
candidate even when the model predicts low risk.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Optional


RULE_MAPPING = json.loads((Path(__file__).resolve().parents[3] / "data/rules/research_rule_mapping.json").read_text())
ABSOLUTE_CONTRAINDICATION_PAIRS = RULE_MAPPING["pairs"]
TOKENS = {token for pair in ABSOLUTE_CONTRAINDICATION_PAIRS for token in pair}


def normalize_rule_id(drug: str) -> str:
    value = str(drug).strip()
    if re.fullmatch(r"(?:compound::)?DB\d{5}", value, re.IGNORECASE):
        return "Compound::" + value.split("::")[-1].upper()
    return value.lower()


def resolve_rule_identity(drug: str) -> dict[str, Any]:
    identifier = normalize_rule_id(drug)
    mapping = RULE_MAPPING["mappings"].get(identifier)
    if mapping:
        return {"drugId": identifier, **mapping}
    # Literal categories support legacy fixtures; absent graph membership is unknown.
    return {"drugId": identifier, "tokens": [identifier] if identifier in TOKENS else [],
            "complete": identifier in TOKENS, "source": "legacy_literal" if identifier in TOKENS else None}


def evaluate_rule_applicability(drug_set: list[str]) -> dict[str, Any]:
    identities = [resolve_rule_identity(drug) for drug in drug_set]
    for identity in identities:
        identity["categoryEvidence"] = {token: "verified_member" if token in identity["tokens"] else "unknown"
                                        for token in sorted(TOKENS)}
    tokens = {token for identity in identities for token in identity["tokens"]}
    # Closed-world literals exist only for historical fixtures, never canonical compounds.
    complete = bool(identities) and all(identity["source"] == "legacy_literal" for identity in identities)
    rules = []
    for first, second in ABSOLUTE_CONTRAINDICATION_PAIRS:
        triggered = first in tokens and second in tokens
        status = "evaluated" if triggered or complete else "partially_evaluated" if tokens & {first, second} else "not_evaluable"
        rules.append({"pair": [first, second], "status": status, "triggered": triggered})
    status = "evaluated" if all(rule["status"] == "evaluated" for rule in rules) else "partially_evaluated" if any(rule["status"] != "not_evaluable" for rule in rules) else "not_evaluable"
    return {"status": status, "mappingVersion": RULE_MAPPING["version"],
            "scope": RULE_MAPPING["scope"], "clinicallyValidated": False,
            "source": RULE_MAPPING["ruleSource"], "rules": rules, "identities": identities,
            "unmappedDrugIds": [identity["drugId"] for identity in identities if not identity["tokens"]]}


def check_hard_contraindications(drug_set: list[str]) -> Optional[dict[str, object]]:
    normalized = {token for drug in drug_set for token in resolve_rule_identity(drug)["tokens"]}

    for first, second in ABSOLUTE_CONTRAINDICATION_PAIRS:
        if first in normalized and second in normalized:
            return {
                "type": "hard_contraindication",
                "pair": [first, second],
                "message": f"Configured research exclusion: {first} + {second}",
            }

    return None
