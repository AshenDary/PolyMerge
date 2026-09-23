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
    build_cold_start_split,
    build_hetionet_mapping,
    build_supervised_dataset,
    canonicalize_pairs,
    load_ddinter_sources,
    split_dataset,
    _pair_graph_features,
    _pair_molecular_features,
)
from app.data.preprocessing import build_preprocessing_pipeline, get_feature_columns, split_features_target
from app.data.pubchem_enrichment import classify_pubchem_result, enrich_pubchem_mapping, rdkit_descriptors


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
    pubchem = pd.DataFrame([
        {"ddinter_id": "DDInter1", "pubchem_cid": 1, "mapping_status": "exact_unique", "smiles": "CCO"},
        {"ddinter_id": "DDInter2", "pubchem_cid": 2, "mapping_status": "exact_unique", "smiles": "CC"},
        {"ddinter_id": "DDInter3", "pubchem_cid": pd.NA, "mapping_status": "unmapped", "smiles": pd.NA},
    ])
    first, unknown = build_supervised_dataset(deduplicated, mapping, edges, pubchem)
    second, _ = build_supervised_dataset(deduplicated, mapping, edges, pubchem)

    pd.testing.assert_frame_equal(first, second)
    assert set(first[TARGET_COLUMN]) == {"Major"}
    assert len(unknown) == 1
    assert "ctd_label" not in first.columns
    assert first.iloc[0]["bound_gene_intersection_count"] == 1
    assert first.iloc[0]["graph_resemblance_neighbor_count_mean"] == 1
    assert first.iloc[0]["both_structures_available"] == 1
    assert build_graph_feature_lookup(edges)["Compound::1"]["resemblance"] == {"Compound::2"}


def test_pubchem_cache_is_reused_and_ambiguous_or_unresolved_names_stay_unaccepted(tmp_path: Path):
    drugs = pd.DataFrame([{"ddinter_id": "DDInter1", "ddinter_name": "Aspirin"}])
    cache_path = tmp_path / "cache.jsonl"
    mapping_path = tmp_path / "mapping.csv"
    calls = []

    def fetcher(name: str):
        calls.append(name)
        return {"http_status": 200, "properties": [{
            "CID": 2244, "Title": "Aspirin", "SMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "ConnectivitySMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "InChI": "InChI=1S/C9H8O4", "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
        }]}

    first = enrich_pubchem_mapping(drugs, "2026-09-22", cache_path, mapping_path, fetcher, 0)
    second = enrich_pubchem_mapping(
        drugs, "2026-09-22", cache_path, mapping_path,
        lambda name: (_ for _ in ()).throw(AssertionError("cache miss")), 0,
    )
    pd.testing.assert_frame_equal(first, second)
    assert calls == ["Aspirin"]
    assert first.iloc[0]["mapping_status"] == "exact_unique"

    ambiguous = classify_pubchem_result("D2", "Brand Name", {"properties": [{
        "CID": 1, "Title": "Different Compound", "SMILES": "CC", "InChI": "x", "InChIKey": "y",
    }]}, "2026-09-22")
    unresolved = classify_pubchem_result("D3", "Missing", {"http_status": 404, "properties": []}, "2026-09-22")
    assert ambiguous["mapping_status"] == "ambiguous"
    assert unresolved["mapping_status"] == "unmapped"


def test_invalid_structures_are_rejected_and_rdkit_descriptors_are_deterministic():
    invalid = classify_pubchem_result("D1", "Broken", {"properties": [{
        "CID": 1, "Title": "Broken", "SMILES": "not-smiles", "InChI": "x", "InChIKey": "y",
    }]}, "2026-09-22")
    first = rdkit_descriptors("CCO")
    second = rdkit_descriptors("CCO")

    assert invalid["mapping_status"] == "rejected"
    assert invalid["structure_status"] == "rdkit_parse_failed"
    assert first == second
    assert first["molecular_weight"] > 0


def test_pair_features_are_symmetric_and_unmapped_is_not_known_zero():
    edges = pd.DataFrame([
        {"source": "Compound::1", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::2", "metaedge": "CbG", "target": "Gene::1"},
    ])
    lookup = build_graph_feature_lookup(edges)
    forward = _pair_graph_features("Compound::1", "Compound::2", lookup)
    reverse = _pair_graph_features("Compound::2", "Compound::1", lookup)
    molecular_forward = _pair_molecular_features("CCO", "CC")
    molecular_reverse = _pair_molecular_features("CC", "CCO")
    unmapped = _pair_graph_features("Compound::1", pd.NA, lookup)

    assert forward == reverse
    assert molecular_forward == molecular_reverse
    assert forward["side_effect_intersection_count"] == 0
    assert pd.isna(unmapped["side_effect_intersection_count"])
    assert unmapped["hetionet_available_count"] == 1


def test_secondary_split_holds_every_selected_drug_out_of_training():
    rows = []
    drugs = [f"D{index}" for index in range(30)]
    for index in range(120):
        row = {column: 0 for column in FEATURE_COLUMNS}
        row.update({column: "metadata" for column in METADATA_COLUMNS})
        row["drug_a_ddinter_id"] = drugs[index % len(drugs)]
        row["drug_b_ddinter_id"] = drugs[(index * 7 + 1) % len(drugs)]
        row["pair_id"] = f"P{index}"
        row[TARGET_COLUMN] = ALLOWED_LABELS[index % 3]
        rows.append(row)
    train, test, holdout = build_cold_start_split(pd.DataFrame(rows))
    train_drugs = set(train["drug_a_ddinter_id"]) | set(train["drug_b_ddinter_id"])

    assert holdout.isdisjoint(train_drugs)
    assert test.apply(
        lambda row: row["drug_a_ddinter_id"] in holdout or row["drug_b_ddinter_id"] in holdout,
        axis=1,
    ).all()


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
