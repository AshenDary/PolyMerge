"""Filter a small Hetionet fragment for the PolyMerge target disease cluster."""

from __future__ import annotations

import csv
import gzip
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

NODES_TSV = RAW_DIR / "hetionet-v1.0-nodes.tsv"
EDGES_GZ = RAW_DIR / "hetionet-v1.0-edges.sif.gz"
FRAGMENT_NODES_CSV = PROCESSED_DIR / "fragment_nodes.csv"
FRAGMENT_EDGES_CSV = PROCESSED_DIR / "fragment_edges.csv"

TARGET_DISEASE_IDS = {
    "Disease::DOID:10763",  # hypertension
    "Disease::DOID:9352",  # type 2 diabetes mellitus
    "Disease::DOID:3393",  # coronary artery disease
}


def load_nodes(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter="\t")
        return {row["id"]: row for row in reader}


def iter_edges(path: Path) -> csv.DictReader:
    with gzip.open(path, mode="rt", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter="\t")
        yield from reader


def find_treating_compounds(edges_path: Path) -> set[str]:
    compounds: set[str] = set()
    for row in iter_edges(edges_path):
        if row["metaedge"] == "CtD" and row["target"] in TARGET_DISEASE_IDS:
            compounds.add(row["source"])
    return compounds


def write_fragment(
    nodes: dict[str, dict[str, str]],
    compounds: set[str],
    edges_path: Path,
    nodes_csv: Path,
    edges_csv: Path,
) -> tuple[Counter[str], Counter[str], int, int]:
    node_ids: set[str] = set(TARGET_DISEASE_IDS) | set(compounds)
    edge_counts: Counter[str] = Counter()
    total_edges = 0

    edges_csv.parent.mkdir(parents=True, exist_ok=True)
    with edges_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["source", "metaedge", "target"])
        writer.writeheader()

        for row in iter_edges(edges_path):
            if row["source"] not in compounds and row["target"] not in compounds:
                continue

            writer.writerow(row)
            node_ids.add(row["source"])
            node_ids.add(row["target"])
            edge_counts[row["metaedge"]] += 1
            total_edges += 1

    node_counts: Counter[str] = Counter()
    with nodes_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "name", "kind"])
        writer.writeheader()

        for node_id in sorted(node_ids):
            node = nodes.get(node_id)
            if node is None:
                continue

            writer.writerow(
                {
                    "id": node["id"],
                    "name": node["name"],
                    "kind": node["kind"],
                }
            )
            node_counts[node["kind"]] += 1

    # Hetionet has no compound-compound DDI edge type. CrC is chemical
    # resemblance, so this fragment contains zero DDI labels by design; DDI
    # labels come from TWOSIDES in a later sprint, not from this file.
    ddi_label_edges = 0

    return node_counts, edge_counts, sum(node_counts.values()), total_edges + ddi_label_edges


def print_counter(title: str, counter: Counter[str]) -> None:
    print(title)
    for key, value in sorted(counter.items()):
        print(f"  {key}: {value}")


def main() -> None:
    nodes = load_nodes(NODES_TSV)
    compounds = find_treating_compounds(EDGES_GZ)
    node_counts, edge_counts, total_nodes, total_edges = write_fragment(
        nodes=nodes,
        compounds=compounds,
        edges_path=EDGES_GZ,
        nodes_csv=FRAGMENT_NODES_CSV,
        edges_csv=FRAGMENT_EDGES_CSV,
    )

    print(f"Raw node rows: {len(nodes)}")
    print(f"Treating compounds for target diseases: {len(compounds)}")
    print(f"Fragment node rows: {total_nodes}")
    print_counter("Fragment node count by kind:", node_counts)
    print(f"Fragment edge rows: {total_edges}")
    print_counter("Fragment edge count by metaedge:", edge_counts)
    print("DDI label edges in Hetionet fragment: 0")


if __name__ == "__main__":
    main()
