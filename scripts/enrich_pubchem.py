"""Create the cached DDInter-to-PubChem structure mapping."""

from __future__ import annotations

from datetime import date
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "ml_engine"))

from app.data.ddinter_dataset import audit_and_deduplicate_pairs, load_ddinter_sources  # noqa: E402
from app.data.pubchem_enrichment import enrich_pubchem_mapping  # noqa: E402


def main() -> None:
    valid, _, _ = load_ddinter_sources()
    deduplicated, _, _ = audit_and_deduplicate_pairs(valid)
    drugs = pd.concat([
        deduplicated[["DDInterID_A", "Drug_A"]].set_axis(["ddinter_id", "ddinter_name"], axis=1),
        deduplicated[["DDInterID_B", "Drug_B"]].set_axis(["ddinter_id", "ddinter_name"], axis=1),
    ]).drop_duplicates("ddinter_id")
    mapping = enrich_pubchem_mapping(drugs, retrieved_at=date.today().isoformat(), workers=4)
    print(f"Wrote {len(mapping)} DDInter-to-PubChem audit rows")
    print(mapping["mapping_status"].value_counts().to_dict())
    print(mapping["structure_status"].value_counts().to_dict())


if __name__ == "__main__":
    main()
