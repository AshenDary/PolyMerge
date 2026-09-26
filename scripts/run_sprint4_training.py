#!/usr/bin/env python3
"""Run the reproducible Sprint 4 training-only model comparison."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ML_ENGINE_ROOT = REPO_ROOT / "ml_engine"
if str(ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ENGINE_ROOT))

from app.models.training_pipeline import (  # noqa: E402
    DEFAULT_CONTRACT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_TRAIN_PATH,
    run_training_experiment,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the three approved Sprint 4 classifiers using training-only "
            "cross-validation. The untouched test split is never loaded."
        )
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_training_experiment(
        train_path=args.train.resolve(),
        contract_path=args.contract.resolve(),
        output_path=args.output.resolve(),
        n_splits=args.folds,
        random_seed=args.seed,
    )
    selection = report["selection"]
    print(f"Experiment: {report['experiment_id']}")
    print(f"Selected by validation macro F1: {selection['selected_model']}")
    print(
        "Validation macro F1: "
        f"{selection['selected_validation_macro_f1_mean']:.6f} "
        f"+/- {selection['selected_validation_macro_f1_std']:.6f}"
    )
    print(f"Results: {args.output.resolve()}")
    print("Test split: untouched and reserved for Sprint 5")
    print("Serving: inactive; mlStatus remains not_applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

