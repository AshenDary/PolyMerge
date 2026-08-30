"""Small Neo4j helper for loading and querying PolyMerge graph fragments."""

from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j import ManagedTransaction


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9 _-]*$")


def _quote_cypher_identifier(identifier: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"Unsafe Cypher identifier: {identifier}")
    return f"`{identifier.replace('`', '``')}`"


def _batched(items: list[dict[str, str]], size: int = 500) -> Iterable[list[dict[str, str]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


class Neo4jClient:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            connection_timeout=5,
            max_transaction_retry_time=5,
        )

    def close(self) -> None:
        self.driver.close()

    def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            result = session.run(cypher, **params)
            return [record.data() for record in result]

    def load_fragment(self, nodes_csv: Path | str, edges_csv: Path | str) -> dict[str, Any]:
        nodes_by_kind = _group_csv_rows_by_column(Path(nodes_csv), "kind")
        edges_by_metaedge = _group_csv_rows_by_column(Path(edges_csv), "metaedge")

        with self.driver.session() as session:
            for kind, rows in sorted(nodes_by_kind.items()):
                label = _quote_cypher_identifier(kind)
                for batch in _batched(rows):
                    session.execute_write(self._merge_nodes, label, batch)

            for metaedge, rows in sorted(edges_by_metaedge.items()):
                relationship_type = _quote_cypher_identifier(metaedge)
                for batch in _batched(rows):
                    session.execute_write(self._merge_relationships, relationship_type, batch)

        return {
            "nodes": {kind: len(rows) for kind, rows in sorted(nodes_by_kind.items())},
            "edges": {
                metaedge: len(rows) for metaedge, rows in sorted(edges_by_metaedge.items())
            },
            "total_nodes": sum(len(rows) for rows in nodes_by_kind.values()),
            "total_edges": sum(len(rows) for rows in edges_by_metaedge.values()),
        }

    @staticmethod
    def _merge_nodes(
        tx: ManagedTransaction,
        label: str,
        rows: list[dict[str, str]],
    ) -> None:
        tx.run(
            f"""
            UNWIND $rows AS row
            MERGE (n {{id: row.id}})
            SET n:{label},
                n.name = row.name,
                n.kind = row.kind
            """,
            rows=rows,
        )

    @staticmethod
    def _merge_relationships(
        tx: ManagedTransaction,
        relationship_type: str,
        rows: list[dict[str, str]],
    ) -> None:
        tx.run(
            f"""
            UNWIND $rows AS row
            MATCH (source {{id: row.source}})
            MATCH (target {{id: row.target}})
            MERGE (source)-[relationship:{relationship_type}]->(target)
            SET relationship.metaedge = row.metaedge
            """,
            rows=rows,
        )


def _group_csv_rows_by_column(path: Path, column: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            grouped[row[column]].append(row)
    return dict(grouped)
