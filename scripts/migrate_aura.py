"""Offline-first, additive migration of the reviewed graph to an approved Aura host."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_engine"))
SOURCE = "Hetionet"
VERSION = "Hetionet v1.0 filtered PolyMerge fragment"


def source_data() -> tuple[list[dict], list[dict], dict]:
    paths = [ROOT / "data/processed/fragment_nodes.csv", ROOT / "data/processed/fragment_edges.csv"]
    tables = []
    for path in paths:
        with path.open(newline="") as stream:
            tables.append(list(csv.DictReader(stream)))
    nodes, edges = tables
    ids = {node["id"] for node in nodes}
    assert len(ids) == len(nodes), "Duplicate source IDs"
    assert all(edge["source"] in ids and edge["target"] in ids for edge in edges)
    assert sum(node["kind"] == "Compound" for node in nodes) == 299
    mapping = json.loads((ROOT / "data/rules/research_rule_mapping.json").read_text())
    assert len(set(mapping["mappings"]) & ids) == 9
    manifest = {"source": SOURCE, "graphVersion": VERSION,
                "nodes": dict(Counter(node["kind"] for node in nodes)),
                "relationships": dict(Counter(edge["metaedge"] for edge in edges)),
                "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    return nodes, edges, manifest


def validate_existing(nodes: list[dict], edges: list[dict], actual_nodes: list[dict], actual_edges: list[dict], *, complete: bool) -> None:
    expected_nodes = {(row["id"], row["name"], row["kind"]) for row in nodes}
    expected_edges = {(row["source"], row["metaedge"], row["target"]) for row in edges}
    existing_nodes = {(row.get("id"), row.get("name"), row.get("kind")) for row in actual_nodes}
    existing_edges = {(row.get("source"), row.get("metaedge"), row.get("target")) for row in actual_edges}
    if len(existing_nodes) != len(actual_nodes) or len(existing_edges) != len(actual_edges):
        raise ValueError("Target has duplicate identities or relationships")
    if not existing_nodes <= expected_nodes or not existing_edges <= expected_edges:
        raise ValueError("Target contains unrelated or conflicting data; refusing mutation")
    if complete and (existing_nodes != expected_nodes or existing_edges != expected_edges):
        raise ValueError("Target graph differs from the reviewed source")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--approved-host")
    args = parser.parse_args()
    nodes, edges, manifest = source_data()
    if not args.apply and not args.verify:
        sys.stdout.write(json.dumps(manifest, indent=2) + "\n")
        return
    uri = os.environ["AURA_NEO4J_URI"]
    parsed = urlsplit(uri)
    if not args.approved_host or parsed.scheme != "neo4j+s" or parsed.hostname != args.approved_host or parsed.username or parsed.password:
        raise ValueError("Explicit approved Aura host and encrypted connection required")
    from app.utils.neo4j_client import Neo4jClient
    client = Neo4jClient(uri=uri, user=os.environ["AURA_NEO4J_USER"], password=os.environ["AURA_NEO4J_PASSWORD"])
    client.database = os.environ.get("AURA_NEO4J_DATABASE", "neo4j")
    def snapshot() -> tuple[list[dict], list[dict]]:
        return (client.query("MATCH (n) RETURN n.id AS id, n.name AS name, n.kind AS kind"),
                client.query("MATCH (s)-[r]->(t) RETURN s.id AS source, type(r) AS metaedge, t.id AS target"))
    try:
        validate_existing(nodes, edges, *snapshot(), complete=args.verify)
        if args.apply:
            client.load_fragment(ROOT / "data/processed/fragment_nodes.csv", ROOT / "data/processed/fragment_edges.csv")
            client.query("MATCH (n) SET n:PolyMergeNode, n.source = $source, n.graphVersion = $version", source=SOURCE, version=VERSION)
            client.query("CREATE CONSTRAINT polymerge_id IF NOT EXISTS FOR (n:PolyMergeNode) REQUIRE n.id IS UNIQUE")
            client.query("MATCH ()-[r]->() SET r.source = $source, r.graphVersion = $version", source=SOURCE, version=VERSION)
        validate_existing(nodes, edges, *snapshot(), complete=True)
        assert client.query("MATCH (n) WHERE n.source <> $source OR n.graphVersion <> $version OR n.source IS NULL OR n.graphVersion IS NULL RETURN count(n) AS count", source=SOURCE, version=VERSION)[0]["count"] == 0
        manifest["verified"] = True
        sys.stdout.write(json.dumps(manifest, indent=2) + "\n")
    finally:
        client.close()


if __name__ == "__main__":
    main()
