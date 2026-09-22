from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.data.preprocessing import build_preprocessing_pipeline, get_feature_columns, split_features_target
from app.data.sprint3_dataset import (
    EDGES_PATH,
    FEATURE_COLUMNS,
    NODES_PATH,
    TARGET_COLUMN,
    build_ctd_fallback_dataset,
    load_fragment_tables,
    split_dataset,
)


def test_fragment_loader_validates_required_columns_and_deduplicates(tmp_path: Path):
    nodes_path = tmp_path / "nodes.csv"
    edges_path = tmp_path / "edges.csv"
    nodes_path.write_text(
        "id,name,kind\nCompound::A,Drug A,Compound\nCompound::A,Drug A,Compound\nDisease::D,Disease,Disease\n",
        encoding="utf-8",
    )
    edges_path.write_text(
        "source,metaedge,target\nCompound::A,CtD,Disease::D\nCompound::A,CtD,Disease::D\n",
        encoding="utf-8",
    )

    nodes, edges, validation = load_fragment_tables(nodes_path, edges_path)

    assert len(nodes) == 2
    assert len(edges) == 1
    assert validation["duplicate_node_rows_removed"] == 1
    assert validation["duplicate_edge_rows_removed"] == 1


def test_sprint3_dataset_has_required_columns_valid_target_and_no_duplicate_pairs():
    nodes, edges, _ = load_fragment_tables(NODES_PATH, EDGES_PATH)
    dataset = build_ctd_fallback_dataset(nodes, edges)

    assert set(FEATURE_COLUMNS).issubset(dataset.columns)
    assert TARGET_COLUMN in dataset.columns
    assert set(dataset[TARGET_COLUMN]) == {0, 1}
    assert dataset.duplicated(subset=["compound_id", "disease_id"]).sum() == 0
    assert dataset[TARGET_COLUMN].value_counts().to_dict() == {0: 284, 1: 142}


def test_graph_feature_generation_is_deterministic_and_row_leakage_safe():
    nodes = pd.DataFrame(
        [
            {"id": "Compound::A", "name": "Drug A", "kind": "Compound"},
            {"id": "Compound::B", "name": "Drug B", "kind": "Compound"},
            {"id": "Disease::D1", "name": "Disease 1", "kind": "Disease"},
            {"id": "Disease::D2", "name": "Disease 2", "kind": "Disease"},
            {"id": "Gene::G", "name": "Gene", "kind": "Gene"},
            {"id": "Side Effect::S", "name": "Effect", "kind": "Side Effect"},
            {"id": "Pharmacologic Class::P", "name": "Class", "kind": "Pharmacologic Class"},
        ]
    )
    edges = pd.DataFrame(
        [
            {"source": "Compound::A", "metaedge": "CtD", "target": "Disease::D1"},
            {"source": "Compound::A", "metaedge": "CbG", "target": "Gene::G"},
            {"source": "Compound::A", "metaedge": "CcSE", "target": "Side Effect::S"},
            {"source": "Pharmacologic Class::P", "metaedge": "PCiC", "target": "Compound::A"},
            {"source": "Compound::A", "metaedge": "CrC", "target": "Compound::B"},
        ]
    )

    first = build_ctd_fallback_dataset(nodes, edges)
    second = build_ctd_fallback_dataset(nodes, edges)
    positive = first.loc[first[TARGET_COLUMN] == 1].iloc[0]

    pd.testing.assert_frame_equal(first, second)
    assert positive["compound_other_ctd_disease_count"] == 0
    assert positive["disease_other_ctd_compound_count"] == 0
    assert positive["compound_bound_gene_count"] == 1
    assert positive["compound_side_effect_count"] == 1
    assert positive["compound_pharmacologic_class_count"] == 1
    assert positive["compound_resemblance_neighbor_count"] == 1


def test_train_test_split_is_deterministic_stratified_and_non_overlapping():
    nodes, edges, _ = load_fragment_tables(NODES_PATH, EDGES_PATH)
    dataset = build_ctd_fallback_dataset(nodes, edges)

    train, test = split_dataset(dataset)
    train_again, test_again = split_dataset(dataset)

    pd.testing.assert_frame_equal(train, train_again)
    pd.testing.assert_frame_equal(test, test_again)
    assert set(train["row_id"]).isdisjoint(set(test["row_id"]))
    assert len(train) == 340
    assert len(test) == 86
    assert train[TARGET_COLUMN].value_counts().to_dict() == {0: 227, 1: 113}
    assert test[TARGET_COLUMN].value_counts().to_dict() == {0: 57, 1: 29}


def test_preprocessing_excludes_target_and_metadata_from_features():
    nodes, edges, _ = load_fragment_tables(NODES_PATH, EDGES_PATH)
    dataset = build_ctd_fallback_dataset(nodes, edges)
    train, _ = split_dataset(dataset)

    feature_columns = get_feature_columns(train)
    x_train, y_train = split_features_target(train)
    preprocessor = build_preprocessing_pipeline(train)
    transformed = preprocessor.fit_transform(x_train, y_train)

    assert TARGET_COLUMN not in feature_columns
    assert "compound_id" not in feature_columns
    assert "disease_id" not in feature_columns
    assert list(x_train.columns) == FEATURE_COLUMNS
    assert transformed.shape[0] == len(train)
