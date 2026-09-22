"""Build the Sprint 3 DDInter severity dataset with optional Hetionet features."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.model_selection import train_test_split


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "data" / "original" / "ddinter"
MANIFEST_PATH = SOURCE_DIR / "source_manifest.json"
NODES_PATH = REPO_ROOT / "data" / "processed" / "fragment_nodes.csv"
EDGES_PATH = REPO_ROOT / "data" / "processed" / "fragment_edges.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "sprint3"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "sprint3"
TARGET_COLUMN = "ddi_severity"
ALLOWED_LABELS = ("Major", "Moderate", "Minor")
RANDOM_STATE = 42
TEST_SIZE = 0.2
REQUIRED_SOURCE_COLUMNS = {"DDInterID_A", "Drug_A", "DDInterID_B", "Drug_B", "Level"}

DRUG_FEATURE_SUFFIXES = [
    "ctd_disease_count", "cpd_disease_count", "bound_gene_count",
    "upregulated_gene_count", "downregulated_gene_count", "side_effect_count",
    "pharmacologic_class_count", "resemblance_neighbor_count", "graph_degree",
]
PAIR_FEATURES = [
    "shared_gene_count", "shared_bound_gene_count", "shared_upregulated_gene_count",
    "shared_downregulated_gene_count", "shared_side_effect_count",
    "shared_treated_disease_count", "shared_pharmacologic_class_count",
    "gene_jaccard", "side_effect_jaccard", "disease_jaccard",
    "pharmacologic_class_jaccard",
]
FEATURE_COLUMNS = [
    *[f"drug_a_{suffix}" for suffix in DRUG_FEATURE_SUFFIXES],
    *[f"drug_b_{suffix}" for suffix in DRUG_FEATURE_SUFFIXES],
    *PAIR_FEATURES,
]
METADATA_COLUMNS = [
    "pair_id", "drug_a_ddinter_id", "drug_a_name", "drug_b_ddinter_id",
    "drug_b_name", "source_severity", "source_file", "atc_category",
    "source_dataset", "dataset_version", "drug_a_hetionet_id",
    "drug_b_hetionet_id", "drug_a_mapping_status", "drug_b_mapping_status",
    "pair_mapping_coverage",
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_source_manifest(path: Path = MANIFEST_PATH) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {"dataset", "download_page", "license", "retrieved_at", "files"}
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"Source manifest is missing: {', '.join(sorted(missing))}")
    return manifest


def load_ddinter_sources(
    source_dir: Path = SOURCE_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Load official CSVs, validate checksums/schema, and separate malformed rows."""
    manifest = load_source_manifest(manifest_path)
    frames: list[pd.DataFrame] = []
    file_profiles: dict[str, object] = {}
    for filename, expected_hash in manifest["files"].items():
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing DDInter source file: {path}. Run scripts/acquire_ddinter.py")
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"Checksum mismatch for {filename}: {actual_hash}")
        frame = pd.read_csv(path, dtype="string")
        _require_columns(frame, REQUIRED_SOURCE_COLUMNS, path)
        frame = frame[list(sorted(REQUIRED_SOURCE_COLUMNS))].copy()
        frame["source_file"] = filename
        frame["atc_category"] = re.search(r"code_([A-Z])", filename).group(1)
        frames.append(frame)
        file_profiles[filename] = {"rows": int(len(frame)), "sha256": actual_hash}

    combined = pd.concat(frames, ignore_index=True)
    for column in REQUIRED_SOURCE_COLUMNS:
        combined[column] = combined[column].str.strip()
    malformed_mask = combined[list(REQUIRED_SOURCE_COLUMNS)].isna().any(axis=1)
    malformed_mask |= combined[list(REQUIRED_SOURCE_COLUMNS)].fillna("").eq("").any(axis=1)
    malformed = combined.loc[malformed_mask].copy()
    valid = combined.loc[~malformed_mask].copy()
    unexpected = sorted(set(valid["Level"]) - set(ALLOWED_LABELS) - {"Unknown"})
    if unexpected:
        raise ValueError(f"Unexpected DDInter severity labels: {unexpected}")
    profile = {
        "raw_rows": int(len(combined)),
        "malformed_rows": int(len(malformed)),
        "source_files": file_profiles,
        "source_columns": list(combined.columns),
        "missing_values": {k: int(v) for k, v in combined.isna().sum().items()},
    }
    return valid.reset_index(drop=True), malformed.reset_index(drop=True), profile


def canonicalize_pairs(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize unordered pairs using stable DDInter IDs."""
    output = frame.copy()
    swap = output["DDInterID_A"] > output["DDInterID_B"]
    for left, right in (("DDInterID_A", "DDInterID_B"), ("Drug_A", "Drug_B")):
        left_values = output[left].copy()
        output.loc[swap, left] = output.loc[swap, right]
        output.loc[swap, right] = left_values.loc[swap]
    output["pair_id"] = output["DDInterID_A"] + "|" + output["DDInterID_B"]
    output["was_reversed_to_canonical"] = swap
    return output


def audit_and_deduplicate_pairs(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    canonical = canonicalize_pairs(frame)
    exact_subset = ["DDInterID_A", "Drug_A", "DDInterID_B", "Drug_B", "Level"]
    exact_duplicates = int(canonical.duplicated(subset=exact_subset).sum())
    orientation_counts = frame.assign(
        pair_id=frame[["DDInterID_A", "DDInterID_B"]].min(axis=1)
        + "|" + frame[["DDInterID_A", "DDInterID_B"]].max(axis=1),
        orientation=frame["DDInterID_A"] <= frame["DDInterID_B"],
    ).groupby("pair_id")["orientation"].nunique()
    reverse_duplicate_pairs = set(orientation_counts[orientation_counts > 1].index)

    conflicts = canonical.groupby("pair_id").filter(lambda group: group["Level"].nunique() > 1)
    conflict_ids = set(conflicts["pair_id"])
    clean = canonical.loc[~canonical["pair_id"].isin(conflict_ids)].copy()
    clean = clean.sort_values(["pair_id", "source_file"]).groupby("pair_id", as_index=False).agg(
        DDInterID_A=("DDInterID_A", "first"),
        Drug_A=("Drug_A", "first"),
        DDInterID_B=("DDInterID_B", "first"),
        Drug_B=("Drug_B", "first"),
        Level=("Level", "first"),
        source_file=("source_file", lambda values: ";".join(sorted(set(values)))),
        atc_category=("atc_category", lambda values: ";".join(sorted(set(values)))),
    )
    audit = {
        "exact_duplicate_rows": exact_duplicates,
        "duplicate_pair_rows": int(len(canonical) - canonical["pair_id"].nunique()),
        "reverse_duplicate_pair_count": len(reverse_duplicate_pairs),
        "conflicting_label_pair_count": len(conflict_ids),
        "canonical_unique_pairs": int(canonical["pair_id"].nunique()),
    }
    return clean, conflicts.sort_values("pair_id").reset_index(drop=True), audit


def normalize_drug_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def build_hetionet_mapping(drugs: pd.DataFrame, nodes: pd.DataFrame) -> pd.DataFrame:
    """Map unique DDInter drugs by an exact normalized, unambiguous name only."""
    compounds = nodes.loc[nodes["kind"] == "Compound", ["id", "name"]].copy()
    compounds["normalized_name"] = compounds["name"].map(normalize_drug_name)
    candidates = compounds.groupby("normalized_name").agg(
        candidate_count=("id", "nunique"),
        hetionet_compound_id=("id", "first"),
        hetionet_name=("name", "first"),
    )
    mapping = drugs.drop_duplicates("ddinter_id").copy()
    mapping["normalized_name"] = mapping["ddinter_name"].map(normalize_drug_name)
    mapping = mapping.merge(candidates, how="left", left_on="normalized_name", right_index=True)
    mapping["mapping_status"] = "unmapped"
    mapping.loc[mapping["candidate_count"].eq(1), "mapping_status"] = "exact_name"
    mapping.loc[mapping["candidate_count"].gt(1), "mapping_status"] = "ambiguous"
    mapping["mapping_method"] = mapping["mapping_status"].map({
        "exact_name": "normalized case-insensitive exact generic name",
        "ambiguous": "multiple exact normalized-name candidates; not accepted",
        "unmapped": "none",
    })
    mapping.loc[mapping["mapping_status"] != "exact_name", ["hetionet_compound_id", "hetionet_name"]] = pd.NA
    return mapping[[
        "ddinter_id", "ddinter_name", "hetionet_compound_id", "hetionet_name",
        "mapping_method", "mapping_status",
    ]].sort_values("ddinter_id").reset_index(drop=True)


def build_graph_feature_lookup(edges: pd.DataFrame) -> dict[str, dict[str, set[str] | int]]:
    compounds = set(edges.loc[edges["source"].str.startswith("Compound::"), "source"])
    compounds |= set(edges.loc[edges["target"].str.startswith("Compound::"), "target"])
    lookup: dict[str, dict[str, set[str] | int]] = {}
    for compound_id in compounds:
        outgoing = edges.loc[edges["source"] == compound_id]
        incident = edges.loc[(edges["source"] == compound_id) | (edges["target"] == compound_id)]
        sets = {
            "ctd": set(outgoing.loc[outgoing["metaedge"] == "CtD", "target"]),
            "cpd": set(outgoing.loc[outgoing["metaedge"] == "CpD", "target"]),
            "bound": set(outgoing.loc[outgoing["metaedge"] == "CbG", "target"]),
            "up": set(outgoing.loc[outgoing["metaedge"] == "CuG", "target"]),
            "down": set(outgoing.loc[outgoing["metaedge"] == "CdG", "target"]),
            "side_effect": set(outgoing.loc[outgoing["metaedge"] == "CcSE", "target"]),
            "pharmacologic_class": {
                row.source if row.target == compound_id else row.target
                for row in incident.loc[incident["metaedge"] == "PCiC"].itertuples()
            },
            "resemblance": {
                row.target if row.source == compound_id else row.source
                for row in incident.loc[incident["metaedge"] == "CrC"].itertuples()
            },
        }
        sets["gene"] = sets["bound"] | sets["up"] | sets["down"]
        sets["disease"] = sets["ctd"] | sets["cpd"]
        lookup[compound_id] = {**sets, "degree": int(len(incident))}
    return lookup


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _pair_graph_features(a_id: object, b_id: object, lookup: dict[str, dict[str, set[str] | int]]) -> dict[str, object]:
    if pd.isna(a_id) and pd.isna(b_id):
        return {column: pd.NA for column in FEATURE_COLUMNS}
    result: dict[str, object] = {}
    for prefix, compound_id in (("drug_a", a_id), ("drug_b", b_id)):
        item = lookup.get(str(compound_id)) if not pd.isna(compound_id) else None
        values = {
            "ctd_disease_count": len(item["ctd"]) if item else pd.NA,
            "cpd_disease_count": len(item["cpd"]) if item else pd.NA,
            "bound_gene_count": len(item["bound"]) if item else pd.NA,
            "upregulated_gene_count": len(item["up"]) if item else pd.NA,
            "downregulated_gene_count": len(item["down"]) if item else pd.NA,
            "side_effect_count": len(item["side_effect"]) if item else pd.NA,
            "pharmacologic_class_count": len(item["pharmacologic_class"]) if item else pd.NA,
            "resemblance_neighbor_count": len(item["resemblance"]) if item else pd.NA,
            "graph_degree": item["degree"] if item else pd.NA,
        }
        result.update({f"{prefix}_{key}": value for key, value in values.items()})
    a = lookup.get(str(a_id)) if not pd.isna(a_id) else None
    b = lookup.get(str(b_id)) if not pd.isna(b_id) else None
    if not a or not b:
        result.update({column: pd.NA for column in PAIR_FEATURES})
        return result
    for output, key in (
        ("shared_gene_count", "gene"), ("shared_bound_gene_count", "bound"),
        ("shared_upregulated_gene_count", "up"), ("shared_downregulated_gene_count", "down"),
        ("shared_side_effect_count", "side_effect"),
        ("shared_treated_disease_count", "disease"),
        ("shared_pharmacologic_class_count", "pharmacologic_class"),
    ):
        result[output] = len(a[key] & b[key])
    for output, key in (
        ("gene_jaccard", "gene"), ("side_effect_jaccard", "side_effect"),
        ("disease_jaccard", "disease"),
        ("pharmacologic_class_jaccard", "pharmacologic_class"),
    ):
        result[output] = _jaccard(a[key], b[key])
    return result


def build_supervised_dataset(
    deduplicated: pd.DataFrame,
    mapping: pd.DataFrame,
    edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    unknown = deduplicated.loc[deduplicated["Level"] == "Unknown"].copy()
    known = deduplicated.loc[deduplicated["Level"].isin(ALLOWED_LABELS)].copy()
    map_index = mapping.set_index("ddinter_id")
    for side in ("A", "B"):
        id_column = f"DDInterID_{side}"
        prefix = f"drug_{side.lower()}"
        known[f"{prefix}_hetionet_id"] = known[id_column].map(map_index["hetionet_compound_id"])
        known[f"{prefix}_mapping_status"] = known[id_column].map(map_index["mapping_status"])
    a_mapped = known["drug_a_mapping_status"] == "exact_name"
    b_mapped = known["drug_b_mapping_status"] == "exact_name"
    known["pair_mapping_coverage"] = "neither_mapped"
    known.loc[a_mapped & b_mapped, "pair_mapping_coverage"] = "both_mapped"
    known.loc[a_mapped & ~b_mapped, "pair_mapping_coverage"] = "only_drug_a_mapped"
    known.loc[~a_mapped & b_mapped, "pair_mapping_coverage"] = "only_drug_b_mapped"

    lookup = build_graph_feature_lookup(edges)
    features = pd.DataFrame([
        _pair_graph_features(row.drug_a_hetionet_id, row.drug_b_hetionet_id, lookup)
        for row in known.itertuples()
    ])
    renamed = known.rename(columns={
        "DDInterID_A": "drug_a_ddinter_id", "Drug_A": "drug_a_name",
        "DDInterID_B": "drug_b_ddinter_id", "Drug_B": "drug_b_name",
        "Level": "source_severity",
    }).reset_index(drop=True)
    renamed["source_dataset"] = "DDInter"
    renamed["dataset_version"] = "DDInter 2.0"
    renamed[TARGET_COLUMN] = renamed["source_severity"]
    dataset = pd.concat([renamed, features], axis=1)
    dataset = dataset[METADATA_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]]
    return dataset.sort_values("pair_id").reset_index(drop=True), unknown


def split_dataset(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = train_test_split(
        dataset, test_size=TEST_SIZE, random_state=RANDOM_STATE,
        stratify=dataset[TARGET_COLUMN],
    )
    return train.sort_values("pair_id").reset_index(drop=True), test.sort_values("pair_id").reset_index(drop=True)


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    return {str(k): int(v) for k, v in frame[column].value_counts().sort_index().items()}


def build_and_write_sprint3_dataset() -> DatasetBuildResult:
    valid, malformed, source_profile = load_ddinter_sources()
    deduplicated, conflicts, pair_audit = audit_and_deduplicate_pairs(valid)
    nodes = pd.read_csv(NODES_PATH, dtype="string").fillna("")
    edges = pd.read_csv(EDGES_PATH, dtype="string").fillna("")
    drugs = pd.concat([
        deduplicated[["DDInterID_A", "Drug_A"]].set_axis(["ddinter_id", "ddinter_name"], axis=1),
        deduplicated[["DDInterID_B", "Drug_B"]].set_axis(["ddinter_id", "ddinter_name"], axis=1),
    ]).drop_duplicates()
    mapping = build_hetionet_mapping(drugs, nodes)
    dataset, unknown = build_supervised_dataset(deduplicated, mapping, edges)
    train, test = split_dataset(dataset)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUTPUT_DIR / "ddinter_severity_dataset.csv"
    train_path, test_path = OUTPUT_DIR / "train.csv", OUTPUT_DIR / "test.csv"
    profile_path = INTERIM_DIR / "dataset_profile.json"
    dataset.to_csv(dataset_path, index=False)
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    mapping.to_csv(INTERIM_DIR / "ddinter_hetionet_mapping.csv", index=False)
    conflicts.to_csv(INTERIM_DIR / "ddinter_conflicts.csv", index=False)
    unknown.to_csv(INTERIM_DIR / "excluded_unknown_severity.csv", index=False)
    malformed.to_csv(INTERIM_DIR / "ddinter_malformed_rows.csv", index=False)

    train_drugs = set(train["drug_a_ddinter_id"]) | set(train["drug_b_ddinter_id"])
    test_drugs = set(test["drug_a_ddinter_id"]) | set(test["drug_b_ddinter_id"])
    overlap = train_drugs & test_drugs
    profile = {
        "task": "DDInter drug-drug interaction severity classification",
        "unit_of_analysis": "one unique canonical unordered DDInter drug pair",
        "target_column": TARGET_COLUMN,
        "target_classes": list(ALLOWED_LABELS),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        **source_profile,
        **pair_audit,
        "raw_severity_distribution": _counts(valid, "Level"),
        "excluded_unknown_rows": int(len(unknown)),
        "excluded_conflicting_pairs": int(pair_audit["conflicting_label_pair_count"]),
        "final_supervised_rows": int(len(dataset)),
        "target_distribution": _counts(dataset, TARGET_COLUMN),
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_target_distribution": _counts(train, TARGET_COLUMN),
        "test_target_distribution": _counts(test, TARGET_COLUMN),
        "distinct_ddinter_drugs": int(mapping["ddinter_id"].nunique()),
        "mapping_status_counts": _counts(mapping, "mapping_status"),
        "exact_id_mapping_count": 0,
        "exact_name_mapping_count": int(mapping["mapping_status"].eq("exact_name").sum()),
        "verified_alias_mapping_count": 0,
        "ambiguous_mapping_count": int(mapping["mapping_status"].eq("ambiguous").sum()),
        "unmapped_drug_count": int(mapping["mapping_status"].eq("unmapped").sum()),
        "mapping_percentage": round(100 * mapping["mapping_status"].eq("exact_name").mean(), 3),
        "pair_mapping_coverage": _counts(dataset, "pair_mapping_coverage"),
        "rdkit_structure_coverage": 0,
        "rdkit_structure_coverage_percentage": 0.0,
        "rdkit_note": "Official downloadable interaction CSVs provide no verified SMILES, InChI, or InChIKey; descriptors were not fabricated.",
        "feature_columns": FEATURE_COLUMNS,
        "metadata_columns": METADATA_COLUMNS,
        "test_distinct_drugs": len(test_drugs),
        "test_drugs_seen_in_train": len(overlap),
        "test_drug_overlap_percentage": round(100 * len(overlap) / len(test_drugs), 3),
        "fully_novel_test_drugs": len(test_drugs - train_drugs),
    }
    profile_path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    return DatasetBuildResult(dataset_path, train_path, test_path, profile_path, len(dataset), len(train), len(test))


def _require_columns(frame: pd.DataFrame, required: Iterable[str], path: Path) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing required column(s): {', '.join(missing)}")
