"""Sprint 4 model comparison and selection using cross-validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline

from app.data.ddinter_dataset import TARGET_COLUMN
from app.data.preprocessing import build_preprocessing_pipeline, split_features_target


@dataclass
class ModelResult:
    """Results from cross-validation evaluation of a single model."""
    
    name: str
    model_type: str
    cv_scores: dict[str, np.ndarray]
    macro_f1_mean: float
    macro_f1_std: float
    predictions: np.ndarray
    prediction_proba: np.ndarray | None
    confusion_matrix: np.ndarray
    classification_report: dict[str, Any]
    per_class_metrics: pd.DataFrame
    auroc: float | None = None
    auroc_per_class: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    """Complete model comparison report for Sprint 4."""
    
    dataset_info: dict[str, Any]
    preprocessing_info: dict[str, Any]
    cv_strategy: dict[str, Any]
    baseline_result: ModelResult
    model_results: list[ModelResult]
    recommendation: dict[str, Any]
    limitations: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "sprint": "Sprint 4",
            "task": "DDI Severity Classification Model Selection",
            "primary_metric": "macro_f1",
            "dataset_info": self.dataset_info,
            "preprocessing_info": self.preprocessing_info,
            "cv_strategy": self.cv_strategy,
            "baseline": self._result_to_dict(self.baseline_result),
            "models": [self._result_to_dict(r) for r in self.model_results],
            "recommendation": self.recommendation,
            "limitations": self.limitations,
            "disclaimer": (
                "This is a research decision-support system for DDI severity classification. "
                "It makes no clinical guarantee and is not validated for clinical safety decisions."
            ),
        }
    
    def _result_to_dict(self, result: ModelResult) -> dict[str, Any]:
        """Convert ModelResult to dictionary."""
        return {
            "name": result.name,
            "model_type": result.model_type,
            "macro_f1_mean": float(result.macro_f1_mean),
            "macro_f1_std": float(result.macro_f1_std),
            "cv_scores_summary": {
                metric: {
                    "mean": float(scores.mean()),
                    "std": float(scores.std()),
                    "min": float(scores.min()),
                    "max": float(scores.max()),
                }
                for metric, scores in result.cv_scores.items()
            },
            "confusion_matrix": result.confusion_matrix.tolist(),
            "per_class_metrics": result.per_class_metrics.to_dict(orient="records"),
            "classification_report": result.classification_report,
            "auroc": float(result.auroc) if result.auroc is not None else None,
            "auroc_per_class": {k: float(v) for k, v in result.auroc_per_class.items()},
            "metadata": result.metadata,
        }


def get_model_pipelines() -> dict[str, Pipeline]:
    """Return the three Sprint 4 candidate models as sklearn pipelines."""
    preprocessing = build_preprocessing_pipeline()
    
    return {
        "LogisticRegression": Pipeline([
            ("preprocessing", preprocessing),
            ("classifier", LogisticRegression(
                random_state=42,
                max_iter=1000,
                multi_class="multinomial",
                solver="lbfgs",
            )),
        ]),
        "RandomForestClassifier": Pipeline([
            ("preprocessing", preprocessing),
            ("classifier", RandomForestClassifier(
                random_state=42,
                n_estimators=100,
                max_depth=None,
                min_samples_split=2,
                min_samples_leaf=1,
                class_weight="balanced",
            )),
        ]),
        "HistGradientBoostingClassifier": Pipeline([
            ("preprocessing", preprocessing),
            ("classifier", HistGradientBoostingClassifier(
                random_state=42,
                max_iter=100,
                learning_rate=0.1,
                max_depth=None,
            )),
        ]),
    }


def get_baseline_model() -> Pipeline:
    """Return most-frequent baseline for non-competing context."""
    preprocessing = build_preprocessing_pipeline()
    return Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", DummyClassifier(strategy="most_frequent", random_state=42)),
    ])


def evaluate_model(
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    model_name: str,
    cv_folds: int = 5,
    random_state: int = 42,
) -> ModelResult:
    """Evaluate a model using stratified k-fold cross-validation."""
    
    # Define CV strategy
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    
    # Scoring metrics for cross_validate
    scoring = {
        "macro_f1": "f1_macro",
        "weighted_f1": "f1_weighted",
        "micro_f1": "f1_micro",
        "accuracy": "accuracy",
    }
    
    # Perform cross-validation
    cv_results = cross_validate(
        model, X, y,
        cv=cv,
        scoring=scoring,
        return_train_score=False,
        n_jobs=-1,
    )
    
    # Extract scores (remove 'test_' prefix)
    cv_scores = {
        metric: cv_results[f"test_{metric}"]
        for metric in scoring.keys()
    }
    
    # Get cross-validated predictions
    y_pred = cross_val_predict(model, X, y, cv=cv, n_jobs=-1)
    
    # Get prediction probabilities if available
    try:
        y_pred_proba = cross_val_predict(
            model, X, y, cv=cv, method="predict_proba", n_jobs=-1
        )
    except AttributeError:
        y_pred_proba = None
    
    # Calculate metrics
    macro_f1_mean = cv_scores["macro_f1"].mean()
    macro_f1_std = cv_scores["macro_f1"].std()
    
    # Confusion matrix
    cm = confusion_matrix(y, y_pred, labels=["Major", "Moderate", "Minor"])
    
    # Classification report
    clf_report = classification_report(
        y, y_pred,
        labels=["Major", "Moderate", "Minor"],
        output_dict=True,
        zero_division=0,
    )
    
    # Per-class metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y, y_pred,
        labels=["Major", "Moderate", "Minor"],
        zero_division=0,
    )
    
    per_class = pd.DataFrame({
        "class": ["Major", "Moderate", "Minor"],
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "support": support,
    })
    
    # AUROC if probabilities available
    auroc = None
    auroc_per_class = {}
    if y_pred_proba is not None:
        try:
            # Multi-class AUROC (one-vs-rest)
            auroc = roc_auc_score(
                y, y_pred_proba,
                labels=["Major", "Moderate", "Minor"],
                multi_class="ovr",
                average="macro",
            )
            
            # Per-class AUROC
            from sklearn.preprocessing import label_binarize
            y_bin = label_binarize(y, classes=["Major", "Moderate", "Minor"])
            for idx, class_name in enumerate(["Major", "Moderate", "Minor"]):
                auroc_per_class[class_name] = roc_auc_score(
                    y_bin[:, idx], y_pred_proba[:, idx]
                )
        except (ValueError, AttributeError):
            pass
    
    return ModelResult(
        name=model_name,
        model_type=type(model.named_steps["classifier"]).__name__,
        cv_scores=cv_scores,
        macro_f1_mean=macro_f1_mean,
        macro_f1_std=macro_f1_std,
        predictions=y_pred,
        prediction_proba=y_pred_proba,
        confusion_matrix=cm,
        classification_report=clf_report,
        per_class_metrics=per_class,
        auroc=auroc,
        auroc_per_class=auroc_per_class,
        metadata={
            "cv_folds": cv_folds,
            "random_state": random_state,
        },
    )


def generate_comparison_report(
    train_data: pd.DataFrame,
    cv_folds: int = 5,
    random_state: int = 42,
) -> ComparisonReport:
    """Generate complete Sprint 4 model comparison report."""
    
    # Split features and target
    X_train, y_train = split_features_target(train_data)
    
    # Dataset info
    dataset_info = {
        "train_rows": len(train_data),
        "feature_count": X_train.shape[1],
        "target_distribution": y_train.value_counts().to_dict(),
        "target_classes": ["Major", "Moderate", "Minor"],
        "source": "DDInter 2.0",
        "split_strategy": "80/20 stratified pair split, random_state=42",
        "note": "Test set is untouched and reserved for Sprint 5 final evaluation",
    }
    
    # Preprocessing info
    preprocessing_info = {
        "strategy": "Median imputation + StandardScaler",
        "fit_on": "Training data only (per CV fold)",
        "features": "55 numeric symmetric pair features",
        "feature_types": [
            "Hetionet graph summaries and availability indicators",
            "PubChem structure availability indicators",
            "RDKit molecular descriptor summaries",
        ],
        "reference": "ml_engine/app/data/preprocessing.py",
    }
    
    # CV strategy info
    cv_strategy = {
        "method": "StratifiedKFold",
        "folds": cv_folds,
        "shuffle": True,
        "random_state": random_state,
        "stratification": "Target class (ddi_severity)",
    }
    
    # Evaluate baseline
    print("Evaluating baseline (most-frequent)...")
    baseline = get_baseline_model()
    baseline_result = evaluate_model(
        baseline, X_train, y_train,
        "Baseline (Most Frequent)",
        cv_folds, random_state
    )
    
    # Evaluate candidate models
    models = get_model_pipelines()
    model_results = []
    
    for name, model in models.items():
        print(f"Evaluating {name}...")
        result = evaluate_model(
            model, X_train, y_train, name, cv_folds, random_state
        )
        model_results.append(result)
    
    # Sort by macro F1 (descending)
    model_results.sort(key=lambda r: r.macro_f1_mean, reverse=True)
    
    # Generate recommendation
    best_model = model_results[0]
    recommendation = {
        "selected_model": best_model.name,
        "selection_metric": "macro_f1 (mean)",
        "macro_f1_mean": float(best_model.macro_f1_mean),
        "macro_f1_std": float(best_model.macro_f1_std),
        "justification": (
            f"{best_model.name} achieved the highest validation macro F1 "
            f"({best_model.macro_f1_mean:.4f} ± {best_model.macro_f1_std:.4f}) "
            f"across {cv_folds}-fold cross-validation on the training set."
        ),
        "minority_class_performance": {
            row["class"]: {
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "f1_score": float(row["f1_score"]),
                "support": int(row["support"]),
            }
            for _, row in best_model.per_class_metrics.iterrows()
        },
        "next_steps": "Sprint 5: Final evaluation on untouched test set",
    }
    
    # Document limitations
    limitations = [
        "Cross-validation uses the same training data; results are validation performance, not test performance.",
        "The primary split contains 98.94% drug overlap between train and test; it measures new combinations among familiar drugs, not cold-start generalization.",
        "The untouched test set is reserved for Sprint 5 final evaluation and has not been used for any model selection decision.",
        "Minority class (Minor) has limited representation; per-class performance varies significantly.",
        "This is a research classification system, not validated for clinical safety decisions.",
        "Graph and molecular features have varying coverage; missing measurements are imputed from training data.",
        "Models are compared using default or lightly tuned hyperparameters; comprehensive tuning was not performed.",
        "AUROC may not be reliable for imbalanced multiclass problems; macro F1 is the primary selection metric.",
    ]
    
    return ComparisonReport(
        dataset_info=dataset_info,
        preprocessing_info=preprocessing_info,
        cv_strategy=cv_strategy,
        baseline_result=baseline_result,
        model_results=model_results,
        recommendation=recommendation,
        limitations=limitations,
    )


def save_comparison_report(
    report: ComparisonReport,
    output_path: Path,
) -> None:
    """Save comparison report as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"\nComparison report saved to: {output_path}")


def print_comparison_summary(report: ComparisonReport) -> None:
    """Print human-readable summary of comparison results."""
    
    print("\n" + "=" * 80)
    print("Sprint 4 Model Comparison Summary")
    print("=" * 80)
    
    print("\n📊 Dataset Info:")
    print(f"  Training rows: {report.dataset_info['train_rows']:,}")
    print(f"  Features: {report.dataset_info['feature_count']}")
    print(f"  Classes: {', '.join(report.dataset_info['target_classes'])}")
    print(f"  Distribution: {report.dataset_info['target_distribution']}")
    
    print("\n🔧 Preprocessing:")
    print(f"  {report.preprocessing_info['strategy']}")
    print(f"  Fit on: {report.preprocessing_info['fit_on']}")
    
    print("\n📈 Cross-Validation Strategy:")
    print(f"  {report.cv_strategy['method']} with {report.cv_strategy['folds']} folds")
    print(f"  Stratified by: {report.cv_strategy['stratification']}")
    
    print("\n🎯 Baseline Performance:")
    baseline = report.baseline_result
    print(f"  {baseline.name}")
    print(f"    Macro F1: {baseline.macro_f1_mean:.4f} ± {baseline.macro_f1_std:.4f}")
    
    print("\n🤖 Model Performance (sorted by macro F1):")
    for i, result in enumerate(report.model_results, 1):
        print(f"\n  {i}. {result.name}")
        print(f"     Macro F1: {result.macro_f1_mean:.4f} ± {result.macro_f1_std:.4f}")
        print(f"     Weighted F1: {result.cv_scores['weighted_f1'].mean():.4f}")
        print(f"     Accuracy: {result.cv_scores['accuracy'].mean():.4f}")
        if result.auroc is not None:
            print(f"     AUROC (macro): {result.auroc:.4f}")
        
        print(f"\n     Per-class metrics:")
        for _, row in result.per_class_metrics.iterrows():
            print(f"       {row['class']:9s}: P={row['precision']:.3f}  "
                  f"R={row['recall']:.3f}  F1={row['f1_score']:.3f}  "
                  f"(n={int(row['support'])})")
    
    print("\n🏆 Recommendation:")
    rec = report.recommendation
    print(f"  Selected: {rec['selected_model']}")
    print(f"  Metric: {rec['selection_metric']}")
    print(f"  Value: {rec['macro_f1_mean']:.4f} ± {rec['macro_f1_std']:.4f}")
    print(f"  Justification: {rec['justification']}")
    
    print("\n⚠️  Limitations:")
    for limitation in report.limitations:
        print(f"  • {limitation}")
    
    print("\n" + "=" * 80)
    print(f"✅ {report.recommendation['next_steps']}")
    print("=" * 80 + "\n")
