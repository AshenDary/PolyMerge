"""Bounded read-only query-plan inspection against the configured local graph."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_engine"))
from dotenv import load_dotenv
from neo4j import Query
from app.services.graph_service import GraphService
from app.utils.neo4j_client import Neo4jClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    client = Neo4jClient()
    seen = {}

    class Inspector:
        def query(self, cypher: str, **params: object) -> list[dict]:
            start = time.perf_counter()
            rows = client.query(cypher, **params)
            elapsed = (time.perf_counter() - start) * 1000
            key = " ".join(cypher.split())
            if key not in seen:
                with client.driver.session() as session:
                    plan = session.run(Query("EXPLAIN " + cypher, timeout=5), params).consume().plan
                    profiled = session.run(Query("PROFILE " + cypher, timeout=5), params)
                    list(profiled)
                    summary = profiled.consume()
                    seen[key] = {"plan": plan, "profile": summary.profile,
                                 "server_available_ms": summary.result_available_after,
                                 "server_consumed_ms": summary.result_consumed_after,
                                 "calls": 0, "rows": 0, "client_ms": 0}
            seen[key]["calls"] += 1
            seen[key]["rows"] += len(rows)
            seen[key]["client_ms"] += elapsed
            return rows

    try:
        result = GraphService(Inspector()).build_candidate_drugs(["Disease::DOID:10763", "Disease::DOID:9352"])
        report = {"compound_count": len(result["candidates"]), "queries": seen,
                  "indexes": client.query("SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state RETURN name, type, labelsOrTypes, properties, state"),
                  "constraints": client.query("SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties")}
        args.output.write_text(json.dumps(report, indent=2, default=str))
    finally:
        client.close()


if __name__ == "__main__":
    main()
