from __future__ import annotations

import pytest

from app.services.graph_service import GRAPH_VERSION, GraphService, Neo4jConnectionError


DISEASES = {
    "Disease::DOID:10763": {
        "id": "Disease::DOID:10763",
        "name": "hypertension",
        "kind": "Disease",
    },
    "Disease::DOID:9352": {
        "id": "Disease::DOID:9352",
        "name": "type 2 diabetes mellitus",
        "kind": "Disease",
    },
}

DRUG_ROWS = [
    {
        "drug_id": "Compound::DB00177",
        "drug_name": "Valsartan",
        "disease_ids": ["Disease::DOID:10763", "Disease::DOID:9352"],
        "disease_names": ["hypertension", "type 2 diabetes mellitus"],
        "treatment_evidence": [
            {
                "source": "Hetionet",
                "graphVersion": GRAPH_VERSION,
                "relationship": "CtD",
                "metaedge": "CtD",
                "targetId": "Disease::DOID:10763",
                "targetName": "hypertension",
                "evidenceType": "known",
            },
            {
                "source": "Hetionet",
                "graphVersion": GRAPH_VERSION,
                "relationship": "CtD",
                "metaedge": "CtD",
                "targetId": "Disease::DOID:9352",
                "targetName": "type 2 diabetes mellitus",
                "evidenceType": "known",
            },
        ],
    },
    {
        "drug_id": "Compound::DB00381",
        "drug_name": "Amlodipine",
        "disease_ids": ["Disease::DOID:10763"],
        "disease_names": ["hypertension"],
        "treatment_evidence": [
            {
                "source": "Hetionet",
                "graphVersion": GRAPH_VERSION,
                "relationship": "CtD",
                "metaedge": "CtD",
                "targetId": "Disease::DOID:10763",
                "targetName": "hypertension",
                "evidenceType": "known",
            }
        ],
    },
]


class FakeGraphClient:
    def verify_connectivity(self) -> bool:
        return True

    def query(self, cypher: str, **params):
        if "RETURN 1 AS ok" in cypher:
            return [{"ok": 1}]

        if "MATCH (d:Disease {id: $diseaseId})" in cypher:
            disease = DISEASES.get(params["diseaseId"])
            return [disease] if disease else []

        if "MATCH (d:Disease)" in cypher:
            query = params.get("normalizedQuery", "")
            if query == "":
                return list(DISEASES.values())
            return [
                disease
                for disease in DISEASES.values()
                if query in disease["name"] or query == disease["id"].lower()
            ]

        if "MATCH (compound:Compound)-[relationship:CtD]->(disease:Disease {id: $diseaseId})" in cypher:
            disease_id = params["diseaseId"]
            rows = []
            for drug in DRUG_ROWS:
                for disease_row_id, disease_name in zip(
                    drug["disease_ids"], drug["disease_names"]
                ):
                    if disease_row_id == disease_id:
                        rows.append(
                            {
                                "drug_id": drug["drug_id"],
                                "drug_name": drug["drug_name"],
                                "kind": "Compound",
                                "disease_id": disease_row_id,
                                "disease_name": disease_name,
                                "relationship_type": "CtD",
                                "metaedge": "CtD",
                            }
                        )
            return rows

        if "WHERE disease.id IN $diseaseIds" in cypher:
            requested = set(params["diseaseIds"])
            return [
                {
                    **drug,
                    "disease_ids": [
                        disease_id
                        for disease_id in drug["disease_ids"]
                        if disease_id in requested
                    ],
                    "disease_names": [
                        disease_name
                        for disease_id, disease_name in zip(
                            drug["disease_ids"], drug["disease_names"]
                        )
                        if disease_id in requested
                    ],
                }
                for drug in DRUG_ROWS
                if requested.intersection(drug["disease_ids"])
            ]

        if "RETURN compound.id AS id" in cypher:
            if params["drugId"] == "Compound::DB00177":
                return [
                    {
                        "id": "Compound::DB00177",
                        "name": "Valsartan",
                        "kind": "Compound",
                    }
                ]
            return []

        if "gene:Gene" in cypher:
            return [
                {
                    "id": "Gene::7422",
                    "name": "VEGFA",
                    "relationship_type": "CbG",
                    "metaedge": "CbG",
                }
            ]

        if "sideEffect:`Side Effect`" in cypher:
            return [
                {
                    "id": "Side Effect::C0018681",
                    "name": "Headache",
                    "relationship_type": "CcSE",
                    "metaedge": "CcSE",
                }
            ]

        return []


class FailingGraphClient:
    def query(self, cypher: str, **params):
        raise Neo4jConnectionError("Neo4j query failed")


def test_neo4j_connection_check():
    assert GraphService(FakeGraphClient()).verify_connection() is True


def test_disease_search_returns_graph_record():
    result = GraphService(FakeGraphClient()).search_diseases("hypertension")
    assert result[0]["id"] == "Disease::DOID:10763"
    assert result[0]["source"] == "Hetionet"


def test_disease_not_found_returns_none():
    assert GraphService(FakeGraphClient()).get_disease_by_name("not represented") is None


def test_drug_retrieval_for_disease():
    drugs = GraphService(FakeGraphClient()).get_drugs_for_disease("hypertension")
    assert {drug["drug_name"] for drug in drugs} == {"Valsartan", "Amlodipine"}


def test_disease_drug_relationship_includes_ctd_evidence():
    drugs = GraphService(FakeGraphClient()).get_drugs_for_disease("hypertension")
    assert drugs[0]["evidence"]["relationship"] == "CtD"
    assert drugs[0]["evidence"]["source"] == "Hetionet"


def test_multiple_disease_candidate_retrieval():
    result = GraphService(FakeGraphClient()).build_candidate_drugs(
        ["hypertension", "type-2-diabetes"]
    )
    assert result["missingDiseases"] == []
    assert len(result["candidates"]) == 2


def test_coverage_calculation_uses_represented_diseases():
    result = GraphService(FakeGraphClient()).build_candidate_drugs(
        ["hypertension", "type-2-diabetes"]
    )
    valsartan = next(
        candidate
        for candidate in result["candidates"]
        if candidate["drugId"] == "Compound::DB00177"
    )
    amlodipine = next(
        candidate
        for candidate in result["candidates"]
        if candidate["drugId"] == "Compound::DB00381"
    )
    assert valsartan["coverage"] == 1.0
    assert amlodipine["coverage"] == 0.5


def test_each_covered_disease_has_matching_ctd_evidence():
    result = GraphService(FakeGraphClient()).build_candidate_drugs(
        ["hypertension", "type-2-diabetes"]
    )

    for candidate in result["candidates"]:
        for disease_id in candidate["treatedDiseaseIds"]:
            matching_evidence = [
                evidence
                for evidence in candidate["evidence"]
                if evidence.get("relationship") == "CtD"
                and evidence.get("targetId") == disease_id
            ]

            assert matching_evidence, (
                f"{candidate['drugId']} covers {disease_id} without matching CtD evidence"
            )
            assert all(
                evidence["source"] == "Hetionet"
                and evidence["graphVersion"] == GRAPH_VERSION
                and evidence["metaedge"] == "CtD"
                and evidence["targetName"]
                and evidence["evidenceType"] == "known"
                for evidence in matching_evidence
            )


def test_drug_evidence_includes_targets_and_side_effects():
    relationships = GraphService(FakeGraphClient()).get_drug_relationships("Compound::DB00177")
    assert relationships["targets"][0]["relationship"] == "CbG"
    assert relationships["sideEffects"][0]["relationship"] == "CcSE"


def test_empty_candidate_result_for_unrepresented_disease():
    result = GraphService(FakeGraphClient()).build_candidate_drugs(["not represented"])
    assert result["resolvedDiseases"] == []
    assert result["missingDiseases"] == ["not represented"]
    assert result["candidates"] == []


def test_neo4j_connection_failure_is_explicit():
    with pytest.raises(Neo4jConnectionError):
        GraphService(FailingGraphClient()).search_diseases("hypertension")
