"""Neo4j helpers for loading and querying PolyMerge graph fragments."""

from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Optional, Union
from urllib.parse import urlsplit

from dotenv import load_dotenv
from neo4j import GraphDatabase, ManagedTransaction, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable


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
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        missing = [
            name
            for name, value in {
                "NEO4J_URI": self.uri,
                "NEO4J_USER": self.user,
                "NEO4J_PASSWORD": self.password,
            }.items()
            if not value
        ]
        if missing:
            raise Neo4jConnectionError(
                f"Missing Neo4j environment variable(s): {', '.join(missing)}"
            )

        if os.getenv("POLYMERGE_REQUIRE_NEO4J_TLS") == "true":
            parsed = urlsplit(self.uri)
            if parsed.scheme != "neo4j+s" or not parsed.hostname or parsed.username or parsed.password:
                raise Neo4jConnectionError("Cloud graph requires a certificate-verified neo4j+s URI")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            connection_timeout=5,
            max_transaction_retry_time=5,
            max_connection_pool_size=10,
            connection_acquisition_timeout=5,
            max_connection_lifetime=300,
        )

    def close(self) -> None:
        self.driver.close()

    def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(Query(cypher, timeout=30), **params)
                return [record.data() for record in result]
        except (Neo4jError, ServiceUnavailable) as error:
            raise Neo4jConnectionError("Neo4j query failed") from error

    def verify_connectivity(self) -> bool:
        try:
            self.driver.verify_connectivity()
        except (Neo4jError, ServiceUnavailable) as error:
            raise Neo4jConnectionError("Neo4j connectivity check failed") from error
        return True

    def load_fragment(self, nodes_csv: Union[Path, str], edges_csv: Union[Path, str]) -> dict[str, Any]:
        nodes_by_kind = _group_csv_rows_by_column(Path(nodes_csv), "kind")
        edges_by_metaedge = _group_csv_rows_by_column(Path(edges_csv), "metaedge")

        with self.driver.session(database=self.database) as session:
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


class Neo4jConnectionError(RuntimeError):
    """Raised when the Neo4j dependency is unavailable or misconfigured."""


_client: Neo4jClient | None = None
_client_lock = Lock()


def get_neo4j_client() -> Neo4jClient:
    """Share the thread-safe driver; each query still owns its own session."""
    global _client
    with _client_lock:
        if _client is None:
            _client = Neo4jClient()
        return _client


def close_neo4j_client() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None
