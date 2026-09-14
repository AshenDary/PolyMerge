"""Knowledge-graph data access placeholders for the PolyMerge MVP.

This module intentionally exposes a small, deterministic catalog so the
backend can validate the research workflow before any real Neo4j-backed
retrieval or GNN model is implemented.
"""

from __future__ import annotations

DISEASES = [
    {"id": "hypertension", "name": "Hypertension", "kind": "Disease"},
    {"id": "type-2-diabetes", "name": "Type 2 Diabetes", "kind": "Disease"},
    {"id": "coronary-artery-disease", "name": "Coronary Artery Disease", "kind": "Disease"},
]

DRUGS = {
    "lisinopril": {
        "id": "lisinopril",
        "name": "Lisinopril",
        "kind": "Drug",
        "dosageForms": ["tablet"],
        "availableStrengths": ["5 mg", "10 mg", "20 mg"],
        "source": "Hetionet fragment",
        "relationships": [
            {"type": "treats", "target": "hypertension", "source": "Hetionet", "evidenceType": "known"}
        ],
    },
    "amlodipine": {
        "id": "amlodipine",
        "name": "Amlodipine",
        "kind": "Drug",
        "dosageForms": ["tablet"],
        "availableStrengths": ["5 mg", "10 mg"],
        "source": "Hetionet fragment",
        "relationships": [
            {"type": "treats", "target": "hypertension", "source": "Hetionet", "evidenceType": "known"}
        ],
    },
    "metformin": {
        "id": "metformin",
        "name": "Metformin",
        "kind": "Drug",
        "dosageForms": ["tablet"],
        "availableStrengths": ["500 mg", "850 mg", "1000 mg"],
        "source": "Hetionet fragment",
        "relationships": [
            {"type": "treats", "target": "type-2-diabetes", "source": "Hetionet", "evidenceType": "known"}
        ],
    },
    "empagliflozin": {
        "id": "empagliflozin",
        "name": "Empagliflozin",
        "kind": "Drug",
        "dosageForms": ["tablet"],
        "availableStrengths": ["10 mg", "25 mg"],
        "source": "Hetionet fragment",
        "relationships": [
            {"type": "treats", "target": "type-2-diabetes", "source": "Hetionet", "evidenceType": "known"}
        ],
    },
    "aspirin": {
        "id": "aspirin",
        "name": "Aspirin",
        "kind": "Drug",
        "dosageForms": ["tablet"],
        "availableStrengths": ["81 mg", "325 mg"],
        "source": "Hetionet fragment",
        "relationships": [
            {"type": "treats", "target": "coronary-artery-disease", "source": "Hetionet", "evidenceType": "known"}
        ],
    },
    "atorvastatin": {
        "id": "atorvastatin",
        "name": "Atorvastatin",
        "kind": "Drug",
        "dosageForms": ["tablet"],
        "availableStrengths": ["10 mg", "20 mg", "40 mg"],
        "source": "Hetionet fragment",
        "relationships": [
            {"type": "treats", "target": "coronary-artery-disease", "source": "Hetionet", "evidenceType": "known"}
        ],
    },
    "maoi": {
        "id": "maoi",
        "name": "MAOI",
        "kind": "Drug",
        "dosageForms": ["reference"],
        "availableStrengths": ["reference only"],
        "source": "PolyMerge Safety Rules",
        "relationships": [],
    },
    "ssri": {
        "id": "ssri",
        "name": "SSRI",
        "kind": "Drug",
        "dosageForms": ["reference"],
        "availableStrengths": ["reference only"],
        "source": "PolyMerge Safety Rules",
        "relationships": [],
    },
}


def get_available_diseases() -> list[dict[str, str]]:
    return [dict(disease) for disease in DISEASES]


def get_drug_metadata(drug_id: str) -> dict[str, object] | None:
    drug = DRUGS.get(drug_id)
    if drug is None:
        return None
    return dict(drug)


def find_treating_drugs(diseases: list[str]) -> dict[str, list[str]]:
    disease_to_drugs: dict[str, list[str]] = {}
    for disease in diseases:
        disease_key = disease.lower()
        disease_to_drugs[disease_key] = []
        for drug_id, metadata in DRUGS.items():
            if any(
                relationship.get("target") == disease_key and relationship.get("type") == "treats"
                for relationship in metadata.get("relationships", [])
            ):
                disease_to_drugs[disease_key].append(drug_id)
    return disease_to_drugs
