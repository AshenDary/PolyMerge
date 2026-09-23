"""Build the Sprint 3 DDInter severity dataset with optional Hetionet features."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import random

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

GRAPH_DRUG_FEATURES = [
    "ctd_disease_count", "cpd_disease_count", "bound_gene_count",
    "upregulated_gene_count", "downregulated_gene_count", "side_effect_count",
    "pharmacologic_class_count", "resemblance_neighbor_count", "graph_degree",
]
GRAPH_SET_FEATURES = [
    ("gene", "gene"), ("bound_gene", "bound"),
    ("upregulated_gene", "up"), ("downregulated_gene", "down"),
    ("side_effect", "side_effect"), ("treated_disease", "disease"),
    ("pharmacologic_class", "pharmacologic_class"),
]
GRAPH_FEATURE_COLUMNS = [
    "hetionet_available_count", "both_hetionet_available",
    *[f"graph_{suffix}_{summary}" for suffix in GRAPH_DRUG_FEATURES for summary in ("mean", "abs_difference")],
    *[f"{name}_{summary}" for name, _ in GRAPH_SET_FEATURES for summary in ("intersection_count", "union_count", "jaccard")],
]
MOLECULAR_DESCRIPTOR_NAMES = [
    "molecular_weight", "logp", "tpsa", "hbd", "hba", "rotatable_bonds",
]
MOLECULAR_FEATURE_COLUMNS = [
    "structure_available_count", "both_structures_available",
    *[f"{name}_{summary}" for name in MOLECULAR_DESCRIPTOR_NAMES for summary in ("mean", "abs_difference")],
]
FEATURE_COLUMNS = GRAPH_FEATURE_COLUMNS + MOLECULAR_FEATURE_COLUMNS
METADATA_COLUMNS = [
    "pair_id", "drug_a_ddinter_id", "drug_a_name", "drug_b_ddinter_id",
    "drug_b_name", "source_severity", "source_file", "atc_category",
    "source_dataset", "dataset_version", "drug_a_hetionet_id",
    "drug_b_hetionet_id", "drug_a_mapping_status", "drug_b_mapping_status",
    "pair_mapping_coverage", "drug_a_pubchem_cid", "drug_b_pubchem_cid",
    "drug_a_pubchem_status", "drug_b_pubchem_status", "pair_structure_coverage",
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
    a = lookup.get(str(a_id)) if not pd.isna(a_id) else None
    b = lookup.get(str(b_id)) if not pd.isna(b_id) else None
    result: dict[str, object] = {
        "hetionet_available_count": int(a is not None) + int(b is not None),
        "both_hetionet_available": int(a is not None and b is not None),
    }
    if not a or not b:
        result.update({column: pd.NA for column in GRAPH_FEATURE_COLUMNS[2:]})
        return result
    scalar_keys = {
        "ctd_disease_count": "ctd", "cpd_disease_count": "cpd",
        "bound_gene_count": "bound", "upregulated_gene_count": "up",
        "downregulated_gene_count": "down", "side_effect_count": "side_effect",
        "pharmacologic_class_count": "pharmacologic_class",
        "resemblance_neighbor_count": "resemblance", "graph_degree": "degree",
    }
    for suffix, key in scalar_keys.items():
        left = a[key] if key == "degree" else len(a[key])
        right = b[key] if key == "degree" else len(b[key])
        result[f"graph_{suffix}_mean"] = (left + right) / 2
        result[f"graph_{suffix}_abs_difference"] = abs(left - right)
    for name, key in GRAPH_SET_FEATURES:
        result[f"{name}_intersection_count"] = len(a[key] & b[key])
        result[f"{name}_union_count"] = len(a[key] | b[key])
        result[f"{name}_jaccard"] = _jaccard(a[key], b[key])
    return result


def _pair_molecular_features(a_smiles: object, b_smiles: object) -> dict[str, object]:
    from app.data.pubchem_enrichment import rdkit_descriptors

    a_available = not pd.isna(a_smiles)
    b_available = not pd.isna(b_smiles)
    result: dict[str, object] = {
        "structure_available_count": int(a_available) + int(b_available),
        "both_structures_available": int(a_available and b_available),
    }
    if not a_available or not b_available:
        result.update({column: pd.NA for column in MOLECULAR_FEATURE_COLUMNS[2:]})
        return result
    a = rdkit_descriptors(a_smiles)
    b = rdkit_descriptors(b_smiles)
    for name in MOLECULAR_DESCRIPTOR_NAMES:
        result[f"{name}_mean"] = (a[name] + b[name]) / 2
        result[f"{name}_abs_difference"] = abs(a[name] - b[name])
    return result


def build_supervised_dataset(
    deduplicated: pd.DataFrame,
    mapping: pd.DataFrame,
    edges: pd.DataFrame,
    pubchem_mapping: pd.DataFrame | None = None,
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

    if pubchem_mapping is None:
        pubchem_mapping = pd.DataFrame({
            "ddinter_id": pd.concat([known["DDInterID_A"], known["DDInterID_B"]]).unique(),
            "pubchem_cid": pd.NA, "mapping_status": "unmapped", "smiles": pd.NA,
        })
    pubchem_index = pubchem_mapping.set_index("ddinter_id")
    for side in ("A", "B"):
        id_column = f"DDInterID_{side}"
        prefix = f"drug_{side.lower()}"
        known[f"{prefix}_pubchem_cid"] = known[id_column].map(pubchem_index["pubchem_cid"])
        known[f"{prefix}_pubchem_status"] = known[id_column].map(pubchem_index["mapping_status"])
        known[f"{prefix}_smiles"] = known[id_column].map(pubchem_index["smiles"])
    a_structured = known["drug_a_pubchem_status"] == "exact_unique"
    b_structured = known["drug_b_pubchem_status"] == "exact_unique"
    known["pair_structure_coverage"] = "neither_structured"
    known.loc[a_structured & b_structured, "pair_structure_coverage"] = "both_structured"
    known.loc[a_structured ^ b_structured, "pair_structure_coverage"] = "one_structured"

    lookup = build_graph_feature_lookup(edges)
    graph_features = pd.DataFrame([
        _pair_graph_features(row.drug_a_hetionet_id, row.drug_b_hetionet_id, lookup)
        for row in known.itertuples()
    ])
    molecular_features = pd.DataFrame([
        _pair_molecular_features(row.drug_a_smiles, row.drug_b_smiles)
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
    dataset = pd.concat([renamed, graph_features, molecular_features], axis=1)
    dataset = dataset[METADATA_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]]
    return dataset.sort_values("pair_id").reset_index(drop=True), unknown


def split_dataset(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = train_test_split(
        dataset, test_size=TEST_SIZE, random_state=RANDOM_STATE,
        stratify=dataset[TARGET_COLUMN],
    )
    return train.sort_values("pair_id").reset_index(drop=True), test.sort_values("pair_id").reset_index(drop=True)


def build_cold_start_split(
    dataset: pd.DataFrame,
    holdout_fraction: float = 0.1,
) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    """Hold out drugs so every secondary-test pair contains an unseen drug."""
    drugs = sorted(set(dataset["drug_a_ddinter_id"]) | set(dataset["drug_b_ddinter_id"]))
    shuffled = drugs.copy()
    random.Random(RANDOM_STATE).shuffle(shuffled)
    holdout = set(shuffled[:round(len(shuffled) * holdout_fraction)])
    test_mask = dataset["drug_a_ddinter_id"].isin(holdout) | dataset["drug_b_ddinter_id"].isin(holdout)
    train = dataset.loc[~test_mask].sort_values("pair_id").reset_index(drop=True)
    test = dataset.loc[test_mask].sort_values("pair_id").reset_index(drop=True)
    return train, test, holdout


def feature_coverage_profile(dataset: pd.DataFrame) -> pd.DataFrame:
    provenance = {
        **{column: "Hetionet graph" for column in GRAPH_FEATURE_COLUMNS},
        **{column: "PubChem structure + RDKit" for column in MOLECULAR_FEATURE_COLUMNS},
    }
    rows = []
    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(dataset[column], errors="coerce")
        nonmissing = values.dropna()
        rows.append({
            "feature": column, "provenance": provenance[column],
            "nonmissing_count": int(values.notna().sum()),
            "missing_count": int(values.isna().sum()),
            "missing_percentage": round(100 * values.isna().mean(), 6),
            "zero_percentage_of_nonmissing": round(100 * nonmissing.eq(0).mean(), 6) if len(nonmissing) else pd.NA,
            "unique_nonmissing_values": int(nonmissing.nunique()),
            "mean": nonmissing.mean(), "std": nonmissing.std(),
            "min": nonmissing.min(), "q25": nonmissing.quantile(0.25),
            "median": nonmissing.median(), "q75": nonmissing.quantile(0.75),
            "max": nonmissing.max(),
        })
    return pd.DataFrame(rows)


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    return {str(k): int(v) for k, v in frame[column].value_counts().sort_index().items()}


def build_and_write_sprint3_dataset() -> DatasetBuildResult:
    from app.data.pubchem_enrichment import MAPPING_PATH, validate_pubchem_mapping

    valid, malformed, source_profile = load_ddinter_sources()
    deduplicated, conflicts, pair_audit = audit_and_deduplicate_pairs(valid)
    nodes = pd.read_csv(NODES_PATH, dtype="string").fillna("")
    edges = pd.read_csv(EDGES_PATH, dtype="string").fillna("")
    drugs = pd.concat([
        deduplicated[["DDInterID_A", "Drug_A"]].set_axis(["ddinter_id", "ddinter_name"], axis=1),
        deduplicated[["DDInterID_B", "Drug_B"]].set_axis(["ddinter_id", "ddinter_name"], axis=1),
    ]).drop_duplicates()
    mapping = build_hetionet_mapping(drugs, nodes)
    if not MAPPING_PATH.exists():
        raise FileNotFoundError("Missing PubChem mapping. Run scripts/enrich_pubchem.py first.")
    pubchem_mapping = pd.read_csv(MAPPING_PATH, dtype={"ddinter_id": "string", "pubchem_cid": "Int64"})
    validate_pubchem_mapping(pubchem_mapping)
    dataset, unknown = build_supervised_dataset(deduplicated, mapping, edges, pubchem_mapping)
    train, test = split_dataset(dataset)
    secondary_train, secondary_test, holdout_drugs = build_cold_start_split(dataset)
    feature_coverage = feature_coverage_profile(dataset)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUTPUT_DIR / "ddinter_severity_dataset.csv"
    train_path, test_path = OUTPUT_DIR / "train.csv", OUTPUT_DIR / "test.csv"
    profile_path = INTERIM_DIR / "dataset_profile.json"
    dataset.to_csv(dataset_path, index=False)
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    secondary_train.to_csv(OUTPUT_DIR / "secondary_cold_start_train.csv", index=False)
    secondary_test.to_csv(OUTPUT_DIR / "secondary_cold_start_test.csv", index=False)
    pd.DataFrame({"held_out_ddinter_id": sorted(holdout_drugs)}).to_csv(
        INTERIM_DIR / "secondary_cold_start_holdout_drugs.csv", index=False
    )
    feature_coverage.to_csv(INTERIM_DIR / "feature_coverage.csv", index=False)
    mapping.to_csv(INTERIM_DIR / "ddinter_hetionet_mapping.csv", index=False)
    conflicts.to_csv(INTERIM_DIR / "ddinter_conflicts.csv", index=False)
    unknown.to_csv(INTERIM_DIR / "excluded_unknown_severity.csv", index=False)
    malformed.to_csv(INTERIM_DIR / "ddinter_malformed_rows.csv", index=False)

    train_drugs = set(train["drug_a_ddinter_id"]) | set(train["drug_b_ddinter_id"])
    test_drugs = set(test["drug_a_ddinter_id"]) | set(test["drug_b_ddinter_id"])
    overlap = train_drugs & test_drugs
    accepted_structures = pubchem_mapping["mapping_status"].eq("exact_unique")
    secondary_train_drugs = set(secondary_train["drug_a_ddinter_id"]) | set(secondary_train["drug_b_ddinter_id"])
    secondary_test_drugs = set(secondary_test["drug_a_ddinter_id"]) | set(secondary_test["drug_b_ddinter_id"])
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
        "pubchem_mapping_status_counts": _counts(pubchem_mapping, "mapping_status"),
        "pubchem_unique_mapping_count": int(accepted_structures.sum()),
        "pubchem_mapping_percentage": round(100 * accepted_structures.mean(), 3),
        "valid_smiles_count": int(pubchem_mapping["smiles"].notna().where(accepted_structures, False).sum()),
        "valid_inchikey_count": int(pubchem_mapping["inchikey"].notna().where(accepted_structures, False).sum()),
        "valid_structure_count": int(accepted_structures.sum()),
        "rdkit_structure_coverage": int(accepted_structures.sum()),
        "rdkit_structure_coverage_percentage": round(100 * accepted_structures.mean(), 3),
        "rdkit_descriptor_names": MOLECULAR_DESCRIPTOR_NAMES,
        "pair_structure_coverage": _counts(dataset, "pair_structure_coverage"),
        "rdkit_note": "Accepted exact-title PubChem structures parsed successfully with RDKit; unresolved structures remain missing.",
        "feature_columns": FEATURE_COLUMNS,
        "graph_feature_count": len(GRAPH_FEATURE_COLUMNS),
        "molecular_feature_count": len(MOLECULAR_FEATURE_COLUMNS),
        "final_feature_count": len(FEATURE_COLUMNS),
        "constant_or_near_constant_features": feature_coverage.loc[
            (feature_coverage["unique_nonmissing_values"] <= 1)
            | (feature_coverage["zero_percentage_of_nonmissing"] >= 99.5),
            "feature",
        ].tolist(),
        "metadata_columns": METADATA_COLUMNS,
        "test_distinct_drugs": len(test_drugs),
        "test_drugs_seen_in_train": len(overlap),
        "test_drug_overlap_percentage": round(100 * len(overlap) / len(test_drugs), 3),
        "fully_novel_test_drugs": len(test_drugs - train_drugs),
        "secondary_split": {
            "design": "10% deterministic drug holdout; every test pair contains at least one held-out drug",
            "holdout_drugs": len(holdout_drugs),
            "train_rows": len(secondary_train),
            "test_rows": len(secondary_test),
            "train_target_distribution": _counts(secondary_train, TARGET_COLUMN),
            "test_target_distribution": _counts(secondary_test, TARGET_COLUMN),
            "held_out_drugs_seen_in_train": len(holdout_drugs & secondary_train_drugs),
            "all_test_drug_overlap_count": len(secondary_train_drugs & secondary_test_drugs),
            "limitation": "Partner drugs may occur in training; this is one-or-more-drug cold start, not a fully drug-disjoint partition.",
        },
    }
    profile_path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    return DatasetBuildResult(dataset_path, train_path, test_path, profile_path, len(dataset), len(train), len(test))


def _require_columns(frame: pd.DataFrame, required: Iterable[str], path: Path) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing required column(s): {', '.join(missing)}")
