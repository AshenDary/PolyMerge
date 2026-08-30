"""Load the filtered PolyMerge Hetionet fragment into Neo4j."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "ml_engine"))

from app.utils.neo4j_client import Neo4jClient  # noqa: E402


NODES_CSV = REPO_ROOT / "data" / "processed" / "fragment_nodes.csv"
EDGES_CSV = REPO_ROOT / "data" / "processed" / "fragment_edges.csv"


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(title)
    for key, value in sorted(counts.items()):
        print(f"  {key}: {value}")


def main() -> None:
    client = Neo4jClient()
    try:
        summary = client.load_fragment(NODES_CSV, EDGES_CSV)
    finally:
        client.close()

    print(f"Loaded nodes: {summary['total_nodes']}")
    print_counts("Loaded node count by kind:", summary["nodes"])
    print(f"Loaded edges: {summary['total_edges']}")
    print_counts("Loaded edge count by metaedge:", summary["edges"])


if __name__ == "__main__":
    main()
