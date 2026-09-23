"""Validate the Sprint 4 feature contract without training a model."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
ML_ENGINE_ROOT = REPO_ROOT / "ml_engine"
if str(ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ENGINE_ROOT))

from app.data.ddinter_dataset import (  # noqa: E402
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
from app.data.preprocessing import (  # noqa: E402
    build_preprocessing_pipeline,
    get_feature_columns,
    split_features_target,
)


PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "sprint3"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "sprint3"
CONTRACT_PATH = REPO_ROOT / "data" / "interim" / "sprint4" / "feature_contract.json"
DDINTER_MANIFEST_PATH = REPO_ROOT / "data" / "original" / "ddinter" / "source_manifest.json"
PUBCHEM_MANIFEST_PATH = REPO_ROOT / "data" / "original" / "pubchem" / "source_manifest.json"
DATA_DICTIONARY_PATH = REPO_ROOT / "docs" / "data-dictionary.md"


def _counts(frame: pd.DataFrame) -> dict[str, int]:
    return {
        str(label): int(count)
        for label, count in frame[TARGET_COLUMN].value_counts().sort_index().items()
    }


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, low_memory=False)


def _validate_symmetry(errors: list[str]) -> None:
    edges = pd.DataFrame([
        {"source": "Compound::1", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::2", "metaedge": "CbG", "target": "Gene::1"},
        {"source": "Compound::1", "metaedge": "CrC", "target": "Compound::2"},
    ])
    lookup = build_graph_feature_lookup(edges)
    graph_forward = _pair_graph_features("Compound::1", "Compound::2", lookup)
    graph_reverse = _pair_graph_features("Compound::2", "Compound::1", lookup)
    molecular_forward = _pair_molecular_features("CCO", "CC")
    molecular_reverse = _pair_molecular_features("CC", "CCO")
    _require(graph_forward == graph_reverse, "Graph pair features are order-dependent", errors)
    _require(
        molecular_forward == molecular_reverse,
        "Molecular pair features are order-dependent",
        errors,
    )
    _require(
        not any(name.startswith(("drug_a_", "drug_b_")) for name in FEATURE_COLUMNS),
        "Order-specific drug-side columns appear in the feature contract",
        errors,
    )


def _validate_missingness(frame: pd.DataFrame, errors: list[str]) -> None:
    graph_measurements = GRAPH_FEATURE_COLUMNS[2:]
    molecular_measurements = MOLECULAR_FEATURE_COLUMNS[2:]
    graph_unavailable = frame["both_hetionet_available"].eq(0)
    graph_available = frame["both_hetionet_available"].eq(1)
    structure_unavailable = frame["both_structures_available"].eq(0)
    structure_available = frame["both_structures_available"].eq(1)

    _require(
        frame[["hetionet_available_count", "both_hetionet_available"]].notna().all().all(),
        "Graph availability indicators contain missing values",
        errors,
    )
    _require(
        frame.loc[graph_unavailable, graph_measurements].isna().all().all(),
        "Unavailable graph measurements are encoded as values instead of missing",
        errors,
    )
    _require(
        frame.loc[graph_available, graph_measurements].notna().all().all(),
        "Available graph measurements contain unexpected missing values",
        errors,
    )
    _require(
        frame.loc[graph_available, "side_effect_intersection_count"].eq(0).any(),
        "No represented known-zero graph example was found",
        errors,
    )
    _require(
        frame[["structure_available_count", "both_structures_available"]].notna().all().all(),
        "Structure availability indicators contain missing values",
        errors,
    )
    _require(
        frame.loc[structure_unavailable, molecular_measurements].isna().all().all(),
        "Unavailable molecular descriptors are encoded as values instead of missing",
        errors,
    )
    _require(
        frame.loc[structure_available, molecular_measurements].notna().all().all(),
        "Available molecular descriptors contain unexpected missing values",
        errors,
    )


def validate_contract() -> tuple[dict[str, Any], list[str]]:
    """Return a concise validation report and all failed invariants."""
    errors: list[str] = []
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    train = _load_csv("train.csv")
    test = _load_csv("test.csv")
    complete = _load_csv("ddinter_severity_dataset.csv")
    secondary_train = _load_csv("secondary_cold_start_train.csv")
    secondary_test = _load_csv("secondary_cold_start_test.csv")
    holdout = set(
        pd.read_csv(INTERIM_DIR / "secondary_cold_start_holdout_drugs.csv")[
            "held_out_ddinter_id"
        ]
    )

    expected_columns = METADATA_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]
    _require(len(train) == contract["train_rows"], "Unexpected primary train row count", errors)
    _require(len(test) == contract["test_rows"], "Unexpected primary test row count", errors)
    _require(len(complete) == contract["total_rows"], "Unexpected complete row count", errors)
    _require(len(train) + len(test) == len(complete), "Primary split row totals do not add up", errors)
    _require(list(train.columns) == expected_columns, "Train schema or column order drifted", errors)
    _require(list(test.columns) == expected_columns, "Test schema or column order drifted", errors)
    _require(list(complete.columns) == expected_columns, "Complete schema or column order drifted", errors)
    _require(contract["features"] == FEATURE_COLUMNS, "Manifest and Python feature lists differ", errors)
    _require(contract["feature_count"] == len(FEATURE_COLUMNS) == 55, "Feature count is not 55", errors)
    _require(
        get_feature_columns(train) == FEATURE_COLUMNS,
        "Preprocessing feature selection differs from the approved feature list",
        errors,
    )
    _require(
        not set(contract["excluded_columns"]) & set(FEATURE_COLUMNS),
        "Leakage or metadata columns appear in the model feature list",
        errors,
    )

    train_pairs = set(train["pair_id"])
    test_pairs = set(test["pair_id"])
    complete_pairs = set(complete["pair_id"])
    cross_split_pairs = train_pairs & test_pairs
    _require(not train["pair_id"].duplicated().any(), "Duplicate pair in primary train", errors)
    _require(not test["pair_id"].duplicated().any(), "Duplicate pair in primary test", errors)
    _require(not complete["pair_id"].duplicated().any(), "Duplicate pair in complete dataset", errors)
    _require(not cross_split_pairs, "Canonical pair crosses the primary split", errors)
    _require(train_pairs | test_pairs == complete_pairs, "Primary split union differs from complete data", errors)
    combined = pd.concat([train, test], ignore_index=True).sort_values("pair_id").reset_index(drop=True)
    ordered_complete = complete.sort_values("pair_id").reset_index(drop=True)
    _require(combined.equals(ordered_complete), "Primary split rows differ from complete data", errors)
    for frame_name, frame in (("train", train), ("test", test), ("complete", complete)):
        canonical = frame["drug_a_ddinter_id"].astype(str) + "|" + frame["drug_b_ddinter_id"].astype(str)
        _require(frame["pair_id"].equals(canonical), f"Non-canonical pair identity in {frame_name}", errors)
        _require(
            frame["drug_a_ddinter_id"].le(frame["drug_b_ddinter_id"]).all(),
            f"Non-canonical pair ordering in {frame_name}",
            errors,
        )

    allowed = set(ALLOWED_LABELS)
    _require(set(train[TARGET_COLUMN].dropna()) == allowed, "Unexpected primary train classes", errors)
    _require(set(test[TARGET_COLUMN].dropna()) == allowed, "Unexpected primary test classes", errors)
    _require(not train[TARGET_COLUMN].isna().any(), "Missing primary train target", errors)
    _require(not test[TARGET_COLUMN].isna().any(), "Missing primary test target", errors)
    _require(_counts(train) == contract["train_class_counts"], "Train class counts drifted", errors)
    _require(_counts(test) == contract["test_class_counts"], "Test class counts drifted", errors)

    _validate_symmetry(errors)
    _validate_missingness(complete, errors)

    x_train, y_train = split_features_target(train)
    x_test, _ = split_features_target(test)
    preprocessor = build_preprocessing_pipeline(train)
    transformed_train = preprocessor.fit_transform(x_train, y_train)
    transformed_test = preprocessor.transform(x_test)
    preprocessing_ok = (
        transformed_train.shape == (len(train), len(FEATURE_COLUMNS))
        and transformed_test.shape == (len(test), len(FEATURE_COLUMNS))
        and np.isfinite(transformed_train).all()
        and np.isfinite(transformed_test).all()
    )
    _require(preprocessing_ok, "Train-fit/test-transform preprocessing smoke test failed", errors)

    train_drugs = set(train["drug_a_ddinter_id"]) | set(train["drug_b_ddinter_id"])
    test_drugs = set(test["drug_a_ddinter_id"]) | set(test["drug_b_ddinter_id"])
    overlap = train_drugs & test_drugs

    secondary_train_drugs = set(secondary_train["drug_a_ddinter_id"]) | set(
        secondary_train["drug_b_ddinter_id"]
    )
    secondary_test_drugs = set(secondary_test["drug_a_ddinter_id"]) | set(
        secondary_test["drug_b_ddinter_id"]
    )
    secondary_has_holdout = secondary_test["drug_a_ddinter_id"].isin(holdout) | secondary_test[
        "drug_b_ddinter_id"
    ].isin(holdout)
    _require(len(secondary_train) + len(secondary_test) == len(complete), "Secondary row totals differ", errors)
    _require(
        set(secondary_train["pair_id"]).isdisjoint(secondary_test["pair_id"]),
        "Canonical pair crosses the secondary split",
        errors,
    )
    _require(secondary_has_holdout.all(), "Secondary test pair lacks a held-out drug", errors)
    _require(holdout.isdisjoint(secondary_train_drugs), "Held-out drug appears in secondary train", errors)
    _require(
        bool(secondary_train_drugs & secondary_test_drugs),
        "Secondary split unexpectedly became fully drug-disjoint",
        errors,
    )

    ddinter_manifest = json.loads(DDINTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    pubchem_manifest = json.loads(PUBCHEM_MANIFEST_PATH.read_text(encoding="utf-8"))
    data_dictionary = DATA_DICTIONARY_PATH.read_text(encoding="utf-8")
    _require(ddinter_manifest.get("dataset") == "DDInter 2.0", "DDInter provenance missing", errors)
    _require(pubchem_manifest.get("api") == "PubChem PUG REST", "PubChem provenance missing", errors)
    _require("RDKit" in data_dictionary, "RDKit provenance missing from data dictionary", errors)
    _require("CrC" in data_dictionary and "resemblance" in data_dictionary, "CrC semantics undocumented", errors)
    _require(TARGET_COLUMN == "ddi_severity", "CrC or another field replaced the DDInter target", errors)

    report: dict[str, Any] = {
        "total_supervised_rows": len(complete),
        "train_rows": len(train),
        "test_rows": len(test),
        "target_classes": sorted(allowed),
        "train_class_counts": _counts(train),
        "test_class_counts": _counts(test),
        "feature_count": len(FEATURE_COLUMNS),
        "duplicate_train_pairs": int(train["pair_id"].duplicated().sum()),
        "duplicate_test_pairs": int(test["pair_id"].duplicated().sum()),
        "cross_split_pairs": len(cross_split_pairs),
        "leakage_columns_in_x": sorted(set(contract["excluded_columns"]) & set(FEATURE_COLUMNS)),
        "preprocessing_smoke_test": "PASS" if preprocessing_ok else "FAIL",
        "test_distinct_drugs": len(test_drugs),
        "test_drugs_seen_in_train": len(overlap),
        "test_drug_overlap_percentage": round(100 * len(overlap) / len(test_drugs), 6),
        "secondary_train_rows": len(secondary_train),
        "secondary_test_rows": len(secondary_test),
        "secondary_holdout_drugs": len(holdout),
        "secondary_held_out_drugs_seen_in_train": len(holdout & secondary_train_drugs),
        "secondary_partner_drug_overlap": len(secondary_train_drugs & secondary_test_drugs),
        "secondary_status": "PASS" if secondary_has_holdout.all() else "FAIL",
    }
    return report, errors


def main() -> int:
    report, errors = validate_contract()
    print("Sprint 4 feature contract validation")
    for key, value in report.items():
        print(f"- {key}: {value}")
    if errors:
        print("- errors:")
        for error in errors:
            print(f"  - {error}")
        print("FINAL: FAIL")
        return 1
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
