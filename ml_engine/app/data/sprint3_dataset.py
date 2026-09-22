"""Sprint 3 dataset construction from the available Hetionet fragment.

The preferred DDI task is intentionally not implemented here because this
repository does not currently contain a legitimate DDI label dataset. This
module builds the documented fallback: represented CtD relationship
classification for drug-disease pairs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.model_selection import train_test_split


REPO_ROOT = Path(__file__).resolve().parents[3]
NODES_PATH = REPO_ROOT / "data" / "processed" / "fragment_nodes.csv"
EDGES_PATH = REPO_ROOT / "data" / "processed" / "fragment_edges.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "sprint3"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "sprint3"
RANDOM_STATE = 42
TEST_SIZE = 0.2
NEGATIVE_RATIO = 2
TARGET_COLUMN = "ctd_label"

NODE_COLUMNS = {"id", "name", "kind"}
EDGE_COLUMNS = {"source", "metaedge", "target"}
FEATURE_COLUMNS = [
    "compound_other_ctd_disease_count",
    "compound_cpD_disease_count",
    "compound_bound_gene_count",
    "compound_upregulated_gene_count",
    "compound_downregulated_gene_count",
    "compound_side_effect_count",
    "compound_pharmacologic_class_count",
    "compound_resemblance_neighbor_count",
    "compound_graph_degree",
    "disease_other_ctd_compound_count",
    "disease_cpD_compound_count",
    "disease_graph_degree",
    "has_compound_palliates_disease_edge",
]
METADATA_COLUMNS = [
    "row_id",
    "compound_id",
    "compound_name",
    "disease_id",
    "disease_name",
    "label_source",
    "label_semantics",
]


@dataclass(frozen=True)
class DatasetBuildResult:
    dataset_path: Path
    train_path: Path
    test_path: Path
    profile_path: Path
    row_count: int
    train_count: int
    test_count: int


def build_and_write_sprint3_dataset(
    nodes_path: Path = NODES_PATH,
    edges_path: Path = EDGES_PATH,
    output_dir: Path = OUTPUT_DIR,
    interim_dir: Path = INTERIM_DIR,
) -> DatasetBuildResult:
    """Build deterministic Sprint 3 CSV outputs from the graph fragment."""
    nodes, edges, validation = load_fragment_tables(nodes_path, edges_path)
    dataset = build_ctd_fallback_dataset(nodes, edges)
    train, test = split_dataset(dataset)

    output_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = output_dir / "ml_dataset.csv"
    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"
    profile_path = interim_dir / "dataset_profile.json"

    dataset.to_csv(dataset_path, index=False)
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)

    profile = dataset_profile(dataset, train, test) | {"validation": validation}
    profile_path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")

    return DatasetBuildResult(
        dataset_path=dataset_path,
        train_path=train_path,
        test_path=test_path,
        profile_path=profile_path,
        row_count=len(dataset),
        train_count=len(train),
        test_count=len(test),
    )


def load_fragment_tables(nodes_path: Path, edges_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Load, validate, normalize, and de-duplicate graph fragment tables."""
    nodes = pd.read_csv(nodes_path, dtype=str).fillna("")
    edges = pd.read_csv(edges_path, dtype=str).fillna("")

    _require_columns(nodes, NODE_COLUMNS, nodes_path)
    _require_columns(edges, EDGE_COLUMNS, edges_path)

    for column in NODE_COLUMNS:
        nodes[column] = nodes[column].astype(str).str.strip()
    for column in EDGE_COLUMNS:
        edges[column] = edges[column].astype(str).str.strip()

    malformed_nodes = int((nodes[list(NODE_COLUMNS)] == "").any(axis=1).sum())
    malformed_edges = int((edges[list(EDGE_COLUMNS)] == "").any(axis=1).sum())
    if malformed_nodes or malformed_edges:
        raise ValueError(
            "Malformed graph fragment rows found: "
            f"{malformed_nodes} node rows, {malformed_edges} edge rows"
        )

    duplicate_nodes = int(nodes.duplicated(subset=["id"]).sum())
    duplicate_edges = int(edges.duplicated(subset=["source", "metaedge", "target"]).sum())
    nodes = nodes.drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
    edges = edges.drop_duplicates(subset=["source", "metaedge", "target"], keep="first").reset_index(drop=True)

    validation = {
        "node_rows": int(len(nodes)),
        "edge_rows": int(len(edges)),
        "malformed_node_rows": malformed_nodes,
        "malformed_edge_rows": malformed_edges,
        "duplicate_node_rows_removed": duplicate_nodes,
        "duplicate_edge_rows_removed": duplicate_edges,
    }
    return nodes, edges, validation


def build_ctd_fallback_dataset(nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """Create the fallback supervised table for represented CtD classification."""
    compounds = _nodes_of_kind(nodes, "Compound")
    diseases = _nodes_of_kind(nodes, "Disease")
    names = dict(zip(nodes["id"], nodes["name"]))

    ctd_pairs = _pairs(edges, "CtD")
    non_ctd_pairs = [
        (compound_id, disease_id)
        for compound_id in compounds
        for disease_id in diseases
        if (compound_id, disease_id) not in ctd_pairs
    ]
    negative_count = min(len(non_ctd_pairs), len(ctd_pairs) * NEGATIVE_RATIO)
    negatives = (
        pd.DataFrame(non_ctd_pairs, columns=["compound_id", "disease_id"])
        .sample(n=negative_count, random_state=RANDOM_STATE, replace=False)
        .itertuples(index=False, name=None)
    )
    rows = [
        _row_for_pair(compound_id, disease_id, 1, names, edges, ctd_pairs)
        for compound_id, disease_id in sorted(ctd_pairs)
    ]
    rows.extend(
        _row_for_pair(compound_id, disease_id, 0, names, edges, ctd_pairs)
        for compound_id, disease_id in sorted(negatives)
    )

    dataset = pd.DataFrame(rows)
    dataset = dataset.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)
    ordered_columns = METADATA_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]
    return dataset[ordered_columns]


def split_dataset(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create the course-compatible 80/20 stratified row split."""
    train, test = train_test_split(
        dataset,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=dataset[TARGET_COLUMN],
    )
    return (
        train.sort_values("row_id").reset_index(drop=True),
        test.sort_values("row_id").reset_index(drop=True),
    )


def dataset_profile(dataset: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame) -> dict[str, object]:
    return {
        "task": "fallback_drug_disease_ctd_relationship_classification",
        "unit_of_analysis": "one row = one Compound x Disease pair",
        "target_column": TARGET_COLUMN,
        "positive_label": "1 means the Hetionet fragment contains a represented Compound-[:CtD]->Disease edge",
        "negative_label": "0 means the sampled pair lacks represented CtD in this fragment; it is not clinical evidence of no treatment relationship",
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "negative_ratio": NEGATIVE_RATIO,
        "dataset_rows": int(len(dataset)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "target_distribution": _target_counts(dataset),
        "train_target_distribution": _target_counts(train),
        "test_target_distribution": _target_counts(test),
        "feature_columns": FEATURE_COLUMNS,
        "metadata_columns": METADATA_COLUMNS,
    }


def _row_for_pair(
    compound_id: str,
    disease_id: str,
    label: int,
    names: dict[str, str],
    edges: pd.DataFrame,
    ctd_pairs: set[tuple[str, str]],
) -> dict[str, object]:
    edge_sets = _edge_sets(edges)
    compound_incident = edges[(edges["source"] == compound_id) | (edges["target"] == compound_id)]
    disease_incident = edges[(edges["source"] == disease_id) | (edges["target"] == disease_id)]

    compound_ctd = {target for source, target in edge_sets["CtD"] if source == compound_id}
    disease_ctd = {source for source, target in edge_sets["CtD"] if target == disease_id}
    compound_cpd = {target for source, target in edge_sets["CpD"] if source == compound_id}
    disease_cpd = {source for source, target in edge_sets["CpD"] if target == disease_id}
    bound_genes = {target for source, target in edge_sets["CbG"] if source == compound_id}
    up_genes = {target for source, target in edge_sets["CuG"] if source == compound_id}
    down_genes = {target for source, target in edge_sets["CdG"] if source == compound_id}
    side_effects = {target for source, target in edge_sets["CcSE"] if source == compound_id}
    pharmacologic_classes = {
        source if target == compound_id else target
        for source, target in edge_sets["PCiC"]
        if source == compound_id or target == compound_id
    }
    resemblance_neighbors = {
        target if source == compound_id else source
        for source, target in edge_sets["CrC"]
        if source == compound_id or target == compound_id
    }

    pair_is_ctd = int((compound_id, disease_id) in ctd_pairs)
    return {
        "row_id": f"{compound_id}|{disease_id}",
        "compound_id": compound_id,
        "compound_name": names.get(compound_id, ""),
        "disease_id": disease_id,
        "disease_name": names.get(disease_id, ""),
        "label_source": "Hetionet v1.0 filtered PolyMerge fragment",
        "label_semantics": "represented_CtD_edge" if label == 1 else "sampled_no_represented_CtD_edge",
        "compound_other_ctd_disease_count": max(len(compound_ctd) - pair_is_ctd, 0),
        "compound_cpD_disease_count": len(compound_cpd),
        "compound_bound_gene_count": len(bound_genes),
        "compound_upregulated_gene_count": len(up_genes),
        "compound_downregulated_gene_count": len(down_genes),
        "compound_side_effect_count": len(side_effects),
        "compound_pharmacologic_class_count": len(pharmacologic_classes),
        "compound_resemblance_neighbor_count": len(resemblance_neighbors),
        "compound_graph_degree": int(len(compound_incident)),
        "disease_other_ctd_compound_count": max(len(disease_ctd) - pair_is_ctd, 0),
        "disease_cpD_compound_count": len(disease_cpd),
        "disease_graph_degree": int(len(disease_incident)),
        "has_compound_palliates_disease_edge": int(disease_id in compound_cpd),
        TARGET_COLUMN: label,
    }


def _edge_sets(edges: pd.DataFrame) -> dict[str, set[tuple[str, str]]]:
    return {
        metaedge: _pairs(edges, metaedge)
        for metaedge in ("CtD", "CpD", "CbG", "CuG", "CdG", "CcSE", "CrC", "PCiC")
    }


def _pairs(edges: pd.DataFrame, metaedge: str) -> set[tuple[str, str]]:
    rows = edges.loc[edges["metaedge"] == metaedge, ["source", "target"]]
    return set(rows.itertuples(index=False, name=None))


def _nodes_of_kind(nodes: pd.DataFrame, kind: str) -> list[str]:
    return sorted(nodes.loc[nodes["kind"] == kind, "id"].tolist())


def _target_counts(frame: pd.DataFrame) -> dict[str, int]:
    return {str(key): int(value) for key, value in frame[TARGET_COLUMN].value_counts().sort_index().items()}


def _require_columns(frame: pd.DataFrame, required: Iterable[str], path: Path) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing required column(s): {', '.join(missing)}")
