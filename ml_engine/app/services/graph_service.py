"""Application-level access to the Hetionet Neo4j fragment."""

from __future__ import annotations

import re
from typing import Any, Optional, Protocol

from app.utils.neo4j_client import Neo4jClient, Neo4jConnectionError


HETIONET_SOURCE = "Hetionet"
GRAPH_VERSION = "Hetionet v1.0 filtered PolyMerge fragment"
TREATMENT_RELATIONSHIP = "CtD"
TARGET_RELATIONSHIPS = ("CdG", "CuG", "CbG")
SIDE_EFFECT_RELATIONSHIP = "CcSE"


class QueryClient(Protocol):
    def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        ...


class GraphService:
    def __init__(self, client: Optional[QueryClient] = None) -> None:
        self.client = client or Neo4jClient()

    def verify_connection(self) -> bool:
        if hasattr(self.client, "verify_connectivity"):
            return bool(self.client.verify_connectivity())
        self.client.query("RETURN 1 AS ok")
        return True

    def search_diseases(self, query: str = "", limit: int = 25) -> list[dict[str, Any]]:
        normalized_query = _normalize_search_term(query)
        rows = self.client.query(
            """
            MATCH (d:Disease)
            WITH d,
                 toLower(d.id) AS id,
                 toLower(d.name) AS name,
                 toLower($searchQuery) AS rawQuery,
                 $normalizedQuery AS normalizedQuery
            WHERE normalizedQuery = ""
               OR id = rawQuery
               OR name = rawQuery
               OR name = normalizedQuery
               OR name CONTAINS normalizedQuery
            RETURN d.id AS id,
                   d.name AS name,
                   d.kind AS kind
            ORDER BY
              CASE
                WHEN name = normalizedQuery THEN 0
                WHEN name STARTS WITH normalizedQuery THEN 1
                WHEN name CONTAINS normalizedQuery THEN 2
                ELSE 3
              END,
              d.name
            LIMIT $limit
            """,
            searchQuery=str(query).strip(),
            normalizedQuery=normalized_query,
            limit=limit,
        )
        return [_disease_from_row(row) for row in rows]

    def get_disease_by_id(self, disease_id: str) -> Optional[dict[str, Any]]:
        rows = self.client.query(
            """
            MATCH (d:Disease {id: $diseaseId})
            RETURN d.id AS id,
                   d.name AS name,
                   d.kind AS kind
            LIMIT 1
            """,
            diseaseId=disease_id,
        )
        return _disease_from_row(rows[0]) if rows else None

    def get_disease_by_name(self, name: str) -> Optional[dict[str, Any]]:
        matches = self.search_diseases(name, limit=1)
        return matches[0] if matches else None

    def resolve_diseases(self, disease_terms: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        diseases: list[dict[str, Any]] = []
        missing: list[str] = []
        seen_ids: set[str] = set()

        for term in disease_terms:
            disease = self.get_disease_by_id(term) or self.get_disease_by_name(term)
            if disease is None:
                missing.append(term)
                continue
            if disease["id"] not in seen_ids:
                diseases.append(disease)
                seen_ids.add(disease["id"])

        return diseases, missing

    def get_drugs_for_disease(self, disease_id_or_name: str) -> list[dict[str, Any]]:
        disease = self.get_disease_by_id(disease_id_or_name) or self.get_disease_by_name(
            disease_id_or_name
        )
        if disease is None:
            return []

        rows = self.client.query(
            """
            MATCH (compound:Compound)-[relationship:CtD]->(disease:Disease {id: $diseaseId})
            RETURN compound.id AS drug_id,
                   compound.name AS drug_name,
                   compound.kind AS kind,
                   disease.id AS disease_id,
                   disease.name AS disease_name,
                   type(relationship) AS relationship_type,
                   relationship.metaedge AS metaedge
            ORDER BY compound.name
            """,
            diseaseId=disease["id"],
        )
        return [_drug_treatment_from_row(row) for row in rows]

    def get_disease_drug_relationships(self, disease_ids: list[str]) -> list[dict[str, Any]]:
        if not disease_ids:
            return []

        rows = self.client.query(
            """
            MATCH (compound:Compound)-[relationship:CtD]->(disease:Disease)
            WHERE disease.id IN $diseaseIds
            RETURN compound.id AS drug_id,
                   compound.name AS drug_name,
                   collect(DISTINCT disease.id) AS disease_ids,
                   collect(DISTINCT disease.name) AS disease_names,
                   collect(DISTINCT {
                     source: "Hetionet",
                     graphVersion: $graphVersion,
                     entityId: compound.id,
                     relationship: type(relationship),
                     metaedge: relationship.metaedge,
                     targetId: disease.id,
                     targetName: disease.name,
                     evidenceType: "known"
                   }) AS treatment_evidence
            ORDER BY size(collect(DISTINCT disease.id)) DESC, compound.name
            """,
            diseaseIds=disease_ids,
            graphVersion=GRAPH_VERSION,
        )
        return rows

    def get_drug_by_id(self, drug_id: str) -> Optional[dict[str, Any]]:
        rows = self.client.query(
            """
            MATCH (compound:Compound {id: $drugId})
            RETURN compound.id AS id,
                   compound.name AS name,
                   compound.kind AS kind
            LIMIT 1
            """,
            drugId=drug_id,
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row["id"],
            "name": row["name"],
            "kind": row.get("kind", "Compound"),
            "source": HETIONET_SOURCE,
            "graphVersion": GRAPH_VERSION,
        }

    def get_drug_targets(self, drug_id: str, limit: int = 25) -> list[dict[str, Any]]:
        rows = self.client.query(
            """
            MATCH (compound:Compound {id: $drugId})-[relationship]->(gene:Gene)
            WHERE type(relationship) IN $relationshipTypes
            RETURN gene.id AS id,
                   gene.name AS name,
                   type(relationship) AS relationship_type,
                   relationship.metaedge AS metaedge
            ORDER BY gene.name
            LIMIT $limit
            """,
            drugId=drug_id,
            relationshipTypes=list(TARGET_RELATIONSHIPS),
            limit=limit,
        )
        return [_related_entity_from_row(row, "Gene") for row in rows]

    def get_drug_side_effects(self, drug_id: str, limit: int = 25) -> list[dict[str, Any]]:
        rows = self.client.query(
            """
            MATCH (compound:Compound {id: $drugId})-[relationship:CcSE]->(sideEffect:`Side Effect`)
            RETURN sideEffect.id AS id,
                   sideEffect.name AS name,
                   type(relationship) AS relationship_type,
                   relationship.metaedge AS metaedge
            ORDER BY sideEffect.name
            LIMIT $limit
            """,
            drugId=drug_id,
            limit=limit,
        )
        return [_related_entity_from_row(row, "Side Effect") for row in rows]

    def get_drug_relationships(self, drug_id: str) -> dict[str, Any]:
        return {
            "drug": self.get_drug_by_id(drug_id),
            "targets": self.get_drug_targets(drug_id),
            "sideEffects": self.get_drug_side_effects(drug_id),
        }

    def build_candidate_drugs(self, disease_terms: list[str]) -> dict[str, Any]:
        diseases, missing_diseases = self.resolve_diseases(disease_terms)
        target_disease_ids = [disease["id"] for disease in diseases]
        relationships = self.get_disease_drug_relationships(target_disease_ids)
        denominator = max(1, len(target_disease_ids))

        candidates = []
        for row in relationships:
            drug_id = row["drug_id"]
            disease_ids = sorted(row.get("disease_ids", []))
            treatment_evidence = row.get("treatment_evidence", [])
            targets = self.get_drug_targets(drug_id, limit=5)
            side_effects = self.get_drug_side_effects(drug_id, limit=5)
            coverage = len(disease_ids) / denominator

            candidates.append(
                {
                    "drugId": drug_id,
                    "drugName": row["drug_name"],
                    "drugs": [drug_id],
                    "drugNames": [row["drug_name"]],
                    "treats": sorted(row.get("disease_names", [])),
                    "treatedDiseaseIds": disease_ids,
                    "coverage": coverage,
                    "coverageCount": len(disease_ids),
                    "targetDiseaseCount": len(target_disease_ids),
                    "drugCount": 1,
                    "interactionRisk": None,
                    "synergyScore": None,
                    "evidenceLevel": "graph",
                    "confidence": coverage,
                    "dataStatus": "real_graph",
                    "status": "accepted",
                    "evidence": [
                        *treatment_evidence,
                        *[_entity_evidence(drug_id, target) for target in targets],
                        *[_entity_evidence(drug_id, side_effect) for side_effect in side_effects],
                    ],
                    "targets": targets,
                    "sideEffects": side_effects,
                    "reasons": [
                        "Candidate was retrieved from represented knowledge-graph treatment relationships.",
                        "Coverage is knowledge-graph treatment coverage, not a clinical efficacy claim.",
                    ],
                }
            )

        return {
            "requestedDiseases": disease_terms,
            "resolvedDiseases": diseases,
            "missingDiseases": missing_diseases,
            "candidateCoverage": {
                candidate["drugId"]: set(candidate["treatedDiseaseIds"]) for candidate in candidates
            },
            "candidates": candidates,
        }


def _normalize_search_term(value: str) -> str:
    normalized = re.sub(r"[-_]+", " ", str(value).strip().lower())
    return re.sub(r"\s+", " ", normalized)


def _disease_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": row.get("kind", "Disease"),
        "source": HETIONET_SOURCE,
        "graphVersion": GRAPH_VERSION,
    }


def _drug_treatment_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "drug_id": row["drug_id"],
        "drug_name": row["drug_name"],
        "kind": row.get("kind", "Compound"),
        "disease_id": row["disease_id"],
        "disease_name": row["disease_name"],
        "evidence": {
            "source": HETIONET_SOURCE,
            "graphVersion": GRAPH_VERSION,
            "entityId": row["drug_id"],
            "relationship": row["relationship_type"],
            "metaedge": row["metaedge"],
            "targetId": row["disease_id"],
            "targetName": row["disease_name"],
            "evidenceType": "known",
        },
    }


def _related_entity_from_row(row: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": kind,
        "source": HETIONET_SOURCE,
        "graphVersion": GRAPH_VERSION,
        "relationship": row["relationship_type"],
        "metaedge": row["metaedge"],
        "evidenceType": "known",
    }


def _entity_evidence(drug_id: str, entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": entity["source"],
        "graphVersion": entity["graphVersion"],
        "entityId": drug_id,
        "relationship": entity["relationship"],
        "metaedge": entity["metaedge"],
        "targetId": entity["id"],
        "targetName": entity["name"],
        "targetKind": entity["kind"],
        "evidenceType": entity["evidenceType"],
    }


__all__ = [
    "GRAPH_VERSION",
    "HETIONET_SOURCE",
    "Neo4jConnectionError",
    "GraphService",
    "SIDE_EFFECT_RELATIONSHIP",
    "TARGET_RELATIONSHIPS",
    "TREATMENT_RELATIONSHIP",
]
