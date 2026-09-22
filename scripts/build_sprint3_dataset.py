"""Build the Sprint 3 DDInter severity dataset and deterministic split."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "ml_engine"))

from app.data.ddinter_dataset import build_and_write_sprint3_dataset  # noqa: E402


def main() -> None:
    result = build_and_write_sprint3_dataset()
    print(f"Wrote dataset: {result.dataset_path} ({result.row_count} rows)")
    print(f"Wrote train split: {result.train_path} ({result.train_count} rows)")
    print(f"Wrote test split: {result.test_path} ({result.test_count} rows)")
    print(f"Wrote profile: {result.profile_path}")


if __name__ == "__main__":
    main()
