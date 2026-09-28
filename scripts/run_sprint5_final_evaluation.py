#!/usr/bin/env python3
"""Run the one official Sprint 5 final Random Forest evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ML_ENGINE_ROOT = REPO_ROOT / "ml_engine"
if str(ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ENGINE_ROOT))

from app.models.final_evaluation import (  # noqa: E402
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_FEATURE_CONTRACT_PATH,
    DEFAULT_METADATA_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_SPRINT4_EXPERIMENT_PATH,
    DEFAULT_TEST_PATH,
    DEFAULT_TRAIN_PATH,
    FinalEvaluationPaths,
    run_final_evaluation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fit the frozen Sprint 4 RandomForestClassifier on train.csv and "
            "perform the one official predictive evaluation on test.csv."
        )
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST_PATH)
    parser.add_argument("--feature-contract", type=Path, default=DEFAULT_FEATURE_CONTRACT_PATH)
    parser.add_argument("--sprint4-experiment", type=Path, default=DEFAULT_SPRINT4_EXPERIMENT_PATH)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = run_final_evaluation(
        FinalEvaluationPaths(
            train_path=args.train.resolve(),
            test_path=args.test.resolve(),
            feature_contract_path=args.feature_contract.resolve(),
            sprint4_experiment_path=args.sprint4_experiment.resolve(),
            artifact_path=args.artifact.resolve(),
            metadata_path=args.metadata.resolve(),
            report_path=args.report.resolve(),
        )
    )
    metrics = metadata["final_test_metrics"]
    print(f"Evaluation run: {metadata['evaluation_run_id']}")
    print(f"Model version: {metadata['model_version']}")
    print(f"Final test Macro F1: {metrics['macro_f1']:.6f}")
    print(f"Validation-to-test gap: {metadata['validation_to_test_gap']:.6f}")
    print(f"Artifact: {metadata['artifact_path']}")
    print(f"Artifact SHA-256: {metadata['artifact_sha256']}")
    print(f"Metadata: {metadata['metadata_path']}")
    print(f"Report: {metadata['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
