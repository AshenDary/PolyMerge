#!/usr/bin/env python3
"""Generate visualizations for Sprint 4 model comparison report.

Creates figures showing:
- Macro F1 comparison across models
- Per-class performance breakdown
- Confusion matrices
- Cross-validation score distributions

Usage:
    python ml_engine/scripts/visualize_model_comparison.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Add project root to Python path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def load_comparison_report(report_path: Path) -> dict:
    """Load the comparison report JSON."""
    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_macro_f1_comparison(report: dict, output_dir: Path) -> None:
    """Plot macro F1 comparison across models."""
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Extract data
    models = []
    means = []
    stds = []
    
    # Add baseline
    baseline = report["baseline"]
    models.append(f"{baseline['name']}\n(non-competing)")
    means.append(baseline["macro_f1_mean"])
    stds.append(baseline["macro_f1_std"])
    
    # Add candidate models
    for model in report["models"]:
        models.append(model["name"])
        means.append(model["macro_f1_mean"])
        stds.append(model["macro_f1_std"])
    
    # Create bar plot
    x = np.arange(len(models))
    colors = ["lightgray"] + ["steelblue"] * (len(models) - 1)
    bars = ax.bar(x, means, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor="black")
    
    # Highlight best model
    best_idx = np.argmax(means[1:]) + 1
    bars[best_idx].set_color("darkgreen")
    bars[best_idx].set_alpha(1.0)
    
    ax.set_ylabel("Macro F1 Score", fontsize=12, fontweight="bold")
    ax.set_title("Sprint 4 Model Comparison\n5-Fold Cross-Validation on Training Data", 
                 fontsize=14, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.axhline(y=means[0], color="red", linestyle="--", alpha=0.5, linewidth=1, 
               label="Baseline")
    
    # Add value labels on bars
    for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
        height = bar.get_height()
        label = f"{mean:.4f}\n±{std:.4f}"
        ax.text(bar.get_x() + bar.get_width() / 2, height + std + 0.02,
                label, ha="center", va="bottom", fontsize=9, fontweight="bold")
    
    plt.tight_layout()
    output_path = output_dir / "macro_f1_comparison.svg"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_per_class_performance(report: dict, output_dir: Path) -> None:
    """Plot per-class F1 scores for each model."""
    
    # Extract per-class metrics
    data = []
    for model in report["models"]:
        for class_metric in model["per_class_metrics"]:
            data.append({
                "Model": model["name"],
                "Class": class_metric["class"],
                "Precision": class_metric["precision"],
                "Recall": class_metric["recall"],
                "F1 Score": class_metric["f1_score"],
            })
    
    df = pd.DataFrame(data)
    
    # Create subplots for each metric
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    metrics = ["Precision", "Recall", "F1 Score"]
    for ax, metric in zip(axes, metrics):
        pivot = df.pivot(index="Model", columns="Class", values=metric)
        pivot.plot(kind="bar", ax=ax, width=0.8, edgecolor="black", alpha=0.8)
        ax.set_title(f"Per-Class {metric}", fontsize=12, fontweight="bold")
        ax.set_ylabel(metric, fontsize=11)
        ax.set_xlabel("")
        ax.set_ylim(0, 1.0)
        ax.legend(title="Class", loc="lower right")
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    
    plt.suptitle("Per-Class Performance Breakdown", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    
    output_path = output_dir / "per_class_performance.svg"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_confusion_matrices(report: dict, output_dir: Path) -> None:
    """Plot confusion matrices for each model."""
    
    n_models = len(report["models"])
    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4))
    
    if n_models == 1:
        axes = [axes]
    
    classes = ["Major", "Moderate", "Minor"]
    
    for ax, model in zip(axes, report["models"]):
        cm = np.array(model["confusion_matrix"])
        
        # Normalize for better visualization
        cm_normalized = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
        
        sns.heatmap(
            cm_normalized,
            annot=cm,
            fmt="d",
            cmap="Blues",
            xticklabels=classes,
            yticklabels=classes,
            ax=ax,
            cbar_kws={"label": "Normalized Rate"},
            vmin=0,
            vmax=1,
        )
        
        ax.set_title(f"{model['name']}\nMacro F1: {model['macro_f1_mean']:.4f}", 
                     fontsize=11, fontweight="bold")
        ax.set_ylabel("True Label", fontsize=10)
        ax.set_xlabel("Predicted Label", fontsize=10)
    
    plt.suptitle("Confusion Matrices (Cross-Validation Predictions)", 
                 fontsize=14, fontweight="bold", y=1.05)
    plt.tight_layout()
    
    output_path = output_dir / "confusion_matrices.svg"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_metric_distributions(report: dict, output_dir: Path) -> None:
    """Plot distributions of CV scores across folds."""
    
    # This would require storing individual fold scores, which we don't have in the report
    # For now, we'll create a summary plot showing mean ± std for all metrics
    
    metrics = ["macro_f1", "weighted_f1", "micro_f1", "accuracy"]
    metric_labels = ["Macro F1", "Weighted F1", "Micro F1", "Accuracy"]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(metrics))
    width = 0.25
    
    for i, model in enumerate(report["models"]):
        means = [model["cv_scores_summary"][m]["mean"] for m in metrics]
        stds = [model["cv_scores_summary"][m]["std"] for m in metrics]
        
        offset = (i - 1) * width
        ax.bar(x + offset, means, width, yerr=stds, capsize=3,
               label=model["name"], alpha=0.8, edgecolor="black")
    
    ax.set_ylabel("Score", fontsize=12, fontweight="bold")
    ax.set_title("Cross-Validation Score Summary (Mean ± Std)", 
                 fontsize=14, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    plt.tight_layout()
    output_path = output_dir / "metric_distributions.svg"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_minority_class_focus(report: dict, output_dir: Path) -> None:
    """Create a focused view on minority class (Minor) performance."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Extract Minor class metrics
    models = []
    minor_precision = []
    minor_recall = []
    minor_f1 = []
    minor_support = []
    
    for model in report["models"]:
        for class_metric in model["per_class_metrics"]:
            if class_metric["class"] == "Minor":
                models.append(model["name"])
                minor_precision.append(class_metric["precision"])
                minor_recall.append(class_metric["recall"])
                minor_f1.append(class_metric["f1_score"])
                minor_support.append(class_metric["support"])
                break
    
    # Plot 1: Precision-Recall tradeoff
    x = np.arange(len(models))
    width = 0.35
    
    ax1.bar(x - width/2, minor_precision, width, label="Precision", 
            alpha=0.8, edgecolor="black", color="steelblue")
    ax1.bar(x + width/2, minor_recall, width, label="Recall", 
            alpha=0.8, edgecolor="black", color="coral")
    
    ax1.set_ylabel("Score", fontsize=12, fontweight="bold")
    ax1.set_title("Minor Class: Precision vs Recall", fontsize=12, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=45, ha="right")
    ax1.set_ylim(0, 1.0)
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3, linestyle="--")
    
    # Plot 2: F1 score with support annotation
    bars = ax2.bar(x, minor_f1, alpha=0.8, edgecolor="black", color="darkgreen")
    
    # Highlight best
    best_idx = np.argmax(minor_f1)
    bars[best_idx].set_color("green")
    bars[best_idx].set_alpha(1.0)
    
    ax2.set_ylabel("F1 Score", fontsize=12, fontweight="bold")
    ax2.set_title(f"Minor Class F1 Score\n(Support: {minor_support[0] if minor_support else 'N/A'})", 
                  fontsize=12, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, rotation=45, ha="right")
    ax2.set_ylim(0, 1.0)
    ax2.grid(axis="y", alpha=0.3, linestyle="--")
    
    # Add value labels
    for i, (bar, f1) in enumerate(zip(bars, minor_f1)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, height + 0.02,
                f"{f1:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    
    plt.suptitle("Minority Class (Minor) Performance Focus", 
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    
    output_path = output_dir / "minority_class_focus.svg"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved: {output_path}")
    plt.close()


def main() -> None:
    """Generate all visualization plots."""
    
    # Paths
    report_path = REPO_ROOT / "data" / "interim" / "sprint4" / "model_comparison_report.json"
    output_dir = REPO_ROOT / "docs" / "figures" / "sprint4"
    
    # Verify report exists
    if not report_path.exists():
        print(f"❌ Comparison report not found: {report_path}")
        print("Run run_sprint4_model_comparison.py first to generate the report")
        sys.exit(1)
    
    print("=" * 80)
    print("Sprint 4 Model Comparison Visualization")
    print("=" * 80)
    print(f"\nLoading report from: {report_path}")
    
    # Load report
    report = load_comparison_report(report_path)
    print(f"✓ Loaded report for {len(report['models'])} models")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating visualizations in: {output_dir}\n")
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams["font.family"] = "sans-serif"
    
    # Generate plots
    plot_macro_f1_comparison(report, output_dir)
    plot_per_class_performance(report, output_dir)
    plot_confusion_matrices(report, output_dir)
    plot_metric_distributions(report, output_dir)
    plot_minority_class_focus(report, output_dir)
    
    print(f"\n✅ All visualizations generated successfully!")
    print(f"📁 Output directory: {output_dir}")


if __name__ == "__main__":
    main()
