#!/usr/bin/env python3
"""Run Sprint 4 model comparison and generate selection report.

This script:
1. Loads the Sprint 4 training data (test set remains untouched)
2. Evaluates three candidate models using cross-validation
3. Compares results using macro F1 as the primary metric
4. Generates a comprehensive comparison report
5. Recommends the best model for Sprint 5 final evaluation

Usage:
    python ml_engine/scripts/run_sprint4_model_comparison.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from ml_engine.app.models.model_comparison import (
    generate_comparison_report,
    print_comparison_summary,
    save_comparison_report,
)


def main() -> None:
    """Run Sprint 4 model comparison."""
    
    # Paths
    train_path = REPO_ROOT / "data" / "processed" / "sprint3" / "train.csv"
    output_path = REPO_ROOT / "data" / "interim" / "sprint4" / "model_comparison_report.json"
    
    # Verify training data exists
    if not train_path.exists():
        print(f"❌ Training data not found: {train_path}")
        print("Run the dataset builder first to generate train.csv")
        sys.exit(1)
    
    print("=" * 80)
    print("Sprint 4 Model Comparison")
    print("=" * 80)
    print(f"\nLoading training data from: {train_path}")
    
    # Load training data only (test set remains untouched)
    train_data = pd.read_csv(train_path)
    print(f"✓ Loaded {len(train_data):,} training samples")
    
    # Generate comparison report
    print("\nStarting model comparison (this may take several minutes)...\n")
    report = generate_comparison_report(
        train_data=train_data,
        cv_folds=5,
        random_state=42,
    )
    
    # Save report
    save_comparison_report(report, output_path)
    
    # Print summary
    print_comparison_summary(report)
    
    print(f"\n📄 Full report saved to: {output_path}")
    print("\n✅ Sprint 4 model comparison complete!")
    print("   Test set remains untouched for Sprint 5 final evaluation.")


if __name__ == "__main__":
    main()
