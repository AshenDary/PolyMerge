from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.data.ddinter_dataset import (
    ALLOWED_LABELS,
    EDGES_PATH,
    FEATURE_COLUMNS,
    MANIFEST_PATH,
    METADATA_COLUMNS,
    NODES_PATH,
    REQUIRED_SOURCE_COLUMNS,
    TARGET_COLUMN,
    audit_and_deduplicate_pairs,
    build_graph_feature_lookup,
    build_hetionet_mapping,
    build_supervised_dataset,
    canonicalize_pairs,
    load_ddinter_sources,
    split_dataset,
)
from app.data.preprocessing import build_preprocessing_pipeline, get_feature_columns, split_features_target


def _source_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"DDInterID_A": "DDInter2", "Drug_A": "Drug B", "DDInterID_B": "DDInter1", "Drug_B": "Drug A", "Level": "Major", "source_file": "A.csv", "atc_category": "A"},
        {"DDInterID_A": "DDInter1", "Drug_A": "Drug A", "DDInterID_B": "DDInter2", "Drug_B": "Drug B", "Level": "Major", "source_file": "B.csv", "atc_category": "B"},
        {"DDInterID_A": "DDInter1", "Drug_A": "Drug A", "DDInterID_B": "DDInter3", "Drug_B": "Drug C", "Level": "Unknown", "source_file": "A.csv", "atc_category": "A"},
    ])


def test_official_manifest_and_downloaded_source_schema_are_valid():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    valid, malformed, profile = load_ddinter_sources()

    assert manifest["dataset"] == "DDInter 2.0"
    assert manifest["license"] == "CC BY-NC-SA 4.0"
    assert len(manifest["files"]) == 8
    assert REQUIRED_SOURCE_COLUMNS.issubset(valid.columns)
    assert set(valid["Level"]) == {*ALLOWED_LABELS, "Unknown"}
    assert profile["raw_rows"] == len(valid) + len(malformed)


def test_source_schema_validation_rejects_missing_columns(tmp_path: Path):
    source = tmp_path / "bad.csv"
    source.write_text("DDInterID_A,Drug_A\nDDInter1,Drug A\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    import hashlib
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest.write_text(json.dumps({
        "dataset": "DDInter 2.0", "download_page": "https://example.invalid",
        "license": "CC BY-NC-SA 4.0", "retrieved_at": "2026-09-22",
        "files": {source.name: digest},
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required column"):
        load_ddinter_sources(tmp_path, manifest)


def test_canonical_pair_identity_is_deterministic_and_reverse_duplicates_are_detected():
    rows = _source_rows()
    canonical = canonicalize_pairs(rows)
    deduplicated, conflicts, audit = audit_and_deduplicate_pairs(rows)

    assert canonical.iloc[0]["pair_id"] == "DDInter1|DDInter2"
    assert canonical.iloc[0]["Drug_A"] == "Drug A"
    assert canonical.iloc[1]["pair_id"] == canonical.iloc[0]["pair_id"]
    assert audit["reverse_duplicate_pair_count"] == 1
    assert audit["duplicate_pair_rows"] == 1
    assert len(deduplicated) == 2
    assert conflicts.empty


def test_conflicting_known_labels_are_quarantined_without_resolution():
    rows = _source_rows().iloc[:2].copy()
    rows.loc[1, "Level"] = "Minor"
    deduplicated, conflicts, audit = audit_and_deduplicate_pairs(rows)

    assert deduplicated.empty
    assert len(conflicts) == 2
    assert audit["conflicting_label_pair_count"] == 1


def test_exact_mapping_is_explicit_and_ambiguous_mapping_is_not_accepted():
    drugs = pd.DataFrame([
        {"ddinter_id": "DDInter1", "ddinter_name": " Drug A "},
        {"ddinter_id": "DDInter2", "ddinter_name": "Shared"},
        {"ddinter_id": "DDInter3", "ddinter_name": "Missing"},
    ])
    nodes = pd.DataFrame([
        {"id": "Compound::1", "name": "drug a", "kind": "Compound"},
        {"id": "Compound::2", "name": "Shared", "kind": "Compound"},
        {"id": "Compound::3", "name": "shared", "kind": "Compound"},
    ])
    mapping = build_hetionet_mapping(drugs, nodes).set_index("ddinter_id")

    assert mapping.loc["DDInter1", "mapping_status"] == "exact_name"
    assert mapping.loc["DDInter1", "hetionet_compound_id"] == "Compound::1"
    assert mapping.loc["DDInter2", "mapping_status"] == "ambiguous"
    assert pd.isna(mapping.loc["DDInter2", "hetionet_compound_id"])
    assert mapping.loc["DDInter3", "mapping_status"] == "unmapped"


def test_target_uses_only_known_ddinter_labels_and_graph_features_are_deterministic():
    deduplicated, _, _ = audit_and_deduplicate_pairs(_source_rows())
    nodes = pd.DataFrame([
        {"id": "Compound::1", "name": "Drug A", "kind": "Compound"},
        {"id": "Compound::2", "name": "Drug B", "kind": "Compound"},
        {"id": "Gene::1", "name": "Gene", "kind": "Gene"},
    ])
    edges = pd.DataFrame([
        {"source": "Compound::1", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::2", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::1", "metaedge": "CrC", "target": "Compound::2"},
    ])
    drugs = pd.DataFrame([
        {"ddinter_id": "DDInter1", "ddinter_name": "Drug A"},
        {"ddinter_id": "DDInter2", "ddinter_name": "Drug B"},
        {"ddinter_id": "DDInter3", "ddinter_name": "Drug C"},
    ])
    mapping = build_hetionet_mapping(drugs, nodes)
    first, unknown = build_supervised_dataset(deduplicated, mapping, edges)
    second, _ = build_supervised_dataset(deduplicated, mapping, edges)

    pd.testing.assert_frame_equal(first, second)
    assert set(first[TARGET_COLUMN]) == {"Major"}
    assert len(unknown) == 1
    assert "ctd_label" not in first.columns
    assert first.iloc[0]["shared_bound_gene_count"] == 1
    assert first.iloc[0]["drug_a_resemblance_neighbor_count"] == 1
    assert build_graph_feature_lookup(edges)["Compound::1"]["resemblance"] == {"Compound::2"}


def test_split_is_deterministic_stratified_and_has_no_pair_overlap():
    rows = []
    for label in ALLOWED_LABELS:
        for index in range(20):
            row = {column: 0 for column in FEATURE_COLUMNS}
            row.update({column: "metadata" for column in METADATA_COLUMNS})
            row["pair_id"] = f"{label}|{index}"
            row[TARGET_COLUMN] = label
            rows.append(row)
    dataset = pd.DataFrame(rows)
    train, test = split_dataset(dataset)
    train_again, test_again = split_dataset(dataset)

    pd.testing.assert_frame_equal(train, train_again)
    pd.testing.assert_frame_equal(test, test_again)
    assert set(train["pair_id"]).isdisjoint(test["pair_id"])
    assert train[TARGET_COLUMN].value_counts().to_dict() == {label: 16 for label in ALLOWED_LABELS}
    assert test[TARGET_COLUMN].value_counts().to_dict() == {label: 4 for label in ALLOWED_LABELS}


def test_preprocessor_excludes_target_and_metadata_and_transforms_test_data():
    train = pd.read_csv(Path(__file__).parents[2] / "data" / "processed" / "sprint3" / "train.csv")
    test = pd.read_csv(Path(__file__).parents[2] / "data" / "processed" / "sprint3" / "test.csv")
    train_sample = pd.concat([
        train.loc[train["pair_mapping_coverage"] == "both_mapped"].head(200),
        train.loc[train["pair_mapping_coverage"] == "neither_mapped"].head(200),
    ])
    test_sample = test.head(100)
    x_train, y_train = split_features_target(train_sample)
    x_test, _ = split_features_target(test_sample)
    preprocessor = build_preprocessing_pipeline(train_sample)
    transformed_train = preprocessor.fit_transform(x_train, y_train)
    transformed_test = preprocessor.transform(x_test)

    assert get_feature_columns(train_sample) == FEATURE_COLUMNS
    assert TARGET_COLUMN not in x_train
    assert not set(METADATA_COLUMNS) & set(x_train)
    assert transformed_train.shape[0] == len(train_sample)
    assert transformed_test.shape[0] == len(test_sample)
