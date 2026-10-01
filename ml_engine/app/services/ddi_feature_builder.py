"""Runtime bridge from graph candidate pairs to the frozen Sprint 3 feature row."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.ddinter_dataset import (
    EDGES_PATH,
    FEATURE_COLUMNS,
    INTERIM_DIR,
    build_graph_feature_lookup,
    _pair_graph_features,
    _pair_molecular_features,
)


class PairFeatureUnavailableError(RuntimeError):
    """Raised when a candidate pair cannot be represented by the frozen contract."""


@dataclass(frozen=True)
class PairFeatureBuilder:
    """Build one approved 55-column feature row for Hetionet compound pairs."""

    hetionet_mapping_path: Path = INTERIM_DIR / "ddinter_hetionet_mapping.csv"
    pubchem_mapping_path: Path = INTERIM_DIR / "ddinter_pubchem_mapping.csv"
    edges_path: Path = EDGES_PATH

    def __post_init__(self) -> None:
        object.__setattr__(self, "_hetionet_to_ddinter", self._load_hetionet_mapping())
        object.__setattr__(self, "_pubchem_by_ddinter", self._load_pubchem_mapping())
        edges = pd.read_csv(self.edges_path, dtype="string").fillna("")
        object.__setattr__(self, "_graph_lookup", build_graph_feature_lookup(edges))

    def build_features(self, drug_a: str, drug_b: str) -> dict[str, float | int | None]:
        if drug_a == drug_b:
            raise PairFeatureUnavailableError("candidate pair contains the same drug twice")

        left, right = sorted([drug_a, drug_b])
        left_ddinter = self._hetionet_to_ddinter.get(left)
        right_ddinter = self._hetionet_to_ddinter.get(right)
        if left_ddinter is None or right_ddinter is None:
            raise PairFeatureUnavailableError(
                "candidate pair is not fully mapped through the reviewed DDInter-Hetionet bridge"
            )

        left_pubchem = self._pubchem_by_ddinter.get(left_ddinter)
        right_pubchem = self._pubchem_by_ddinter.get(right_ddinter)
        if left_pubchem is None or right_pubchem is None:
            raise PairFeatureUnavailableError(
                "candidate pair is missing reviewed PubChem enrichment rows"
            )

        graph_features = _pair_graph_features(left, right, self._graph_lookup)
        molecular_features = _pair_molecular_features(
            left_pubchem.get("smiles"),
            right_pubchem.get("smiles"),
        )
        raw_features: dict[str, Any] = {**graph_features, **molecular_features}
        return {
            column: _json_feature_value(raw_features[column])
            for column in FEATURE_COLUMNS
        }

    def _load_hetionet_mapping(self) -> dict[str, str]:
        if not self.hetionet_mapping_path.is_file():
            raise PairFeatureUnavailableError(
                f"missing DDInter-Hetionet mapping: {self.hetionet_mapping_path}"
            )
        mapping = pd.read_csv(self.hetionet_mapping_path, dtype="string")
        exact = mapping.loc[
            mapping["mapping_status"].eq("exact_name")
            & mapping["hetionet_compound_id"].notna()
            & mapping["ddinter_id"].notna()
        ]
        return {
            str(row.hetionet_compound_id): str(row.ddinter_id)
            for row in exact.itertuples(index=False)
        }

    def _load_pubchem_mapping(self) -> dict[str, dict[str, Any]]:
        if not self.pubchem_mapping_path.is_file():
            raise PairFeatureUnavailableError(
                f"missing PubChem mapping: {self.pubchem_mapping_path}"
            )
        mapping = pd.read_csv(self.pubchem_mapping_path, dtype="string")
        return {
            str(row.ddinter_id): {
                "mapping_status": row.mapping_status,
                "smiles": row.smiles if not pd.isna(row.smiles) else pd.NA,
            }
            for row in mapping.itertuples(index=False)
        }


def _json_feature_value(value: Any) -> float | int | None:
    if pd.isna(value):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    return float(value)
