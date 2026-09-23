from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.data.ddinter_dataset import (
    ALLOWED_LABELS,
    FEATURE_COLUMNS,
    GRAPH_FEATURE_COLUMNS,
    METADATA_COLUMNS,
    MOLECULAR_FEATURE_COLUMNS,
    TARGET_COLUMN,
    _pair_graph_features,
    _pair_molecular_features,
    build_graph_feature_lookup,
)
from app.data.preprocessing import build_preprocessing_pipeline, split_features_target


REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "sprint3"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "sprint3"
CONTRACT_PATH = REPO_ROOT / "data" / "interim" / "sprint4" / "feature_contract.json"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_sprint4_contract import validate_contract  # noqa: E402


@pytest.fixture(scope="module")
def frames() -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(PROCESSED_DIR / name, low_memory=False)
        for name in (
            "train.csv",
            "test.csv",
            "ddinter_severity_dataset.csv",
            "secondary_cold_start_train.csv",
            "secondary_cold_start_test.csv",
        )
    }


def test_primary_rows_targets_and_canonical_pair_union(frames: dict[str, pd.DataFrame]):
    train = frames["train.csv"]
    test = frames["test.csv"]
    complete = frames["ddinter_severity_dataset.csv"]

    assert (len(train), len(test), len(complete)) == (104337, 26085, 130422)
    assert len(train) + len(test) == len(complete)
    assert set(train[TARGET_COLUMN]) == set(ALLOWED_LABELS)
    assert set(test[TARGET_COLUMN]) == set(ALLOWED_LABELS)
    assert not train[TARGET_COLUMN].isna().any()
    assert not test[TARGET_COLUMN].isna().any()
    assert not train["pair_id"].duplicated().any()
    assert not test["pair_id"].duplicated().any()
    assert set(train["pair_id"]).isdisjoint(test["pair_id"])
    assert set(train["pair_id"]) | set(test["pair_id"]) == set(complete["pair_id"])


def test_exact_feature_manifest_and_leakage_exclusions(frames: dict[str, pd.DataFrame]):
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    train = frames["train.csv"]
    x_train, _ = split_features_target(train)

    assert contract["feature_count"] == len(FEATURE_COLUMNS) == 55
    assert contract["features"] == FEATURE_COLUMNS
    assert list(x_train.columns) == FEATURE_COLUMNS
    assert TARGET_COLUMN not in x_train
    assert not set(METADATA_COLUMNS) & set(x_train.columns)
    assert not set(contract["excluded_columns"]) & set(x_train.columns)


def test_pair_features_are_symmetric_and_crc_is_resemblance_only():
    edges = pd.DataFrame([
        {"source": "Compound::1", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::2", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::1", "metaedge": "CrC", "target": "Compound::2"},
    ])
    lookup = build_graph_feature_lookup(edges)

    assert _pair_graph_features("Compound::1", "Compound::2", lookup) == _pair_graph_features(
        "Compound::2", "Compound::1", lookup
    )
    assert _pair_molecular_features("CCO", "CC") == _pair_molecular_features("CC", "CCO")
    assert TARGET_COLUMN == "ddi_severity"
    assert "graph_resemblance_neighbor_count_mean" in FEATURE_COLUMNS
    assert not any("crc" in feature.casefold() for feature in FEATURE_COLUMNS)


def test_missing_measurements_remain_distinct_from_known_zero(frames: dict[str, pd.DataFrame]):
    complete = frames["ddinter_severity_dataset.csv"]
    graph_measurements = GRAPH_FEATURE_COLUMNS[2:]
    molecular_measurements = MOLECULAR_FEATURE_COLUMNS[2:]
    unavailable_graph = complete["both_hetionet_available"].eq(0)
    available_graph = complete["both_hetionet_available"].eq(1)
    unavailable_structure = complete["both_structures_available"].eq(0)

    assert complete.loc[unavailable_graph, graph_measurements].isna().all().all()
    assert complete.loc[available_graph, "side_effect_intersection_count"].eq(0).any()
    assert complete.loc[unavailable_structure, molecular_measurements].isna().all().all()
    assert complete[[
        "hetionet_available_count",
        "both_hetionet_available",
        "structure_available_count",
        "both_structures_available",
    ]].notna().all().all()


def test_preprocessing_fits_train_and_transforms_test(frames: dict[str, pd.DataFrame]):
    train = frames["train.csv"]
    test = frames["test.csv"]
    x_train, y_train = split_features_target(train)
    x_test, _ = split_features_target(test)
    preprocessor = build_preprocessing_pipeline(train)

    transformed_train = preprocessor.fit_transform(x_train, y_train)
    transformed_test = preprocessor.transform(x_test)

    assert transformed_train.shape == (104337, 55)
    assert transformed_test.shape == (26085, 55)
    assert np.isfinite(transformed_train).all()
    assert np.isfinite(transformed_test).all()


def test_secondary_split_has_one_or_more_unseen_drugs(frames: dict[str, pd.DataFrame]):
    train = frames["secondary_cold_start_train.csv"]
    test = frames["secondary_cold_start_test.csv"]
    holdout = set(
        pd.read_csv(INTERIM_DIR / "secondary_cold_start_holdout_drugs.csv")[
            "held_out_ddinter_id"
        ]
    )
    train_drugs = set(train["drug_a_ddinter_id"]) | set(train["drug_b_ddinter_id"])
    test_drugs = set(test["drug_a_ddinter_id"]) | set(test["drug_b_ddinter_id"])

    assert (len(train), len(test), len(holdout)) == (105979, 24443, 190)
    assert holdout.isdisjoint(train_drugs)
    assert (
        test["drug_a_ddinter_id"].isin(holdout) | test["drug_b_ddinter_id"].isin(holdout)
    ).all()
    assert train_drugs & test_drugs


def test_reusable_validator_reports_no_contract_failures():
    report, errors = validate_contract()

    assert errors == []
    assert report["feature_count"] == 55
    assert report["cross_split_pairs"] == 0
    assert report["preprocessing_smoke_test"] == "PASS"
    assert report["secondary_status"] == "PASS"
