"""Generate Sprint 3 EDA figures and findings from the processed dataset."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "data" / "processed" / "sprint3" / "ml_dataset.csv"
PROFILE_PATH = REPO_ROOT / "data" / "interim" / "sprint3" / "dataset_profile.json"
FIGURE_DIR = REPO_ROOT / "docs" / "figures" / "sprint3"
FINDINGS_PATH = REPO_ROOT / "docs" / "sprint3-eda-findings.md"
TARGET = "ctd_label"

rcParams["svg.hashsalt"] = "polymerge-sprint3"


def main() -> None:
    frame = pd.read_csv(DATASET_PATH)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    figures = [
        _target_distribution(frame),
        _missing_values(frame),
        _compound_feature_histograms(frame),
        _target_by_disease(frame),
        _numeric_correlation(frame),
        _feature_by_target_boxplot(frame),
    ]
    FINDINGS_PATH.write_text(_findings_markdown(frame, profile, figures), encoding="utf-8")
    print(f"Wrote {len(figures)} EDA figures to {FIGURE_DIR}")
    print(f"Wrote EDA findings: {FINDINGS_PATH}")


def _target_distribution(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "target_distribution.svg"
    counts = frame[TARGET].value_counts().sort_index()
    ax = counts.plot(kind="bar", color=["#5b8c85", "#c36b48"], rot=0)
    ax.set_title("CtD Label Distribution")
    ax.set_xlabel("ctd_label")
    ax.set_ylabel("Rows")
    _save(path)
    return path.name


def _missing_values(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "missing_values.svg"
    missing = frame.isna().sum()
    missing = missing[missing > 0]
    if missing.empty:
        missing = pd.Series({"all_columns": 0})
    ax = missing.plot(kind="bar", color="#5b6f95")
    ax.set_title("Missing Values")
    ax.set_ylabel("Missing cells")
    _save(path)
    return path.name


def _compound_feature_histograms(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "compound_feature_distributions.svg"
    columns = [
        "compound_bound_gene_count",
        "compound_side_effect_count",
        "compound_resemblance_neighbor_count",
    ]
    axes = frame[columns].hist(figsize=(9, 4), bins=20, color="#7a9f68")
    for ax in axes.flatten():
        ax.set_ylabel("Rows")
    _save(path)
    return path.name


def _target_by_disease(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "target_by_disease.svg"
    top_diseases = frame["disease_name"].value_counts().head(10).index
    table = pd.crosstab(frame.loc[frame["disease_name"].isin(top_diseases), "disease_name"], frame[TARGET])
    ax = table.plot(kind="barh", color=["#5b8c85", "#c36b48"])
    ax.set_title("CtD Label Distribution by Disease")
    ax.set_xlabel("Rows")
    ax.set_ylabel("Disease")
    _save(path)
    return path.name


def _numeric_correlation(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "numeric_correlation.svg"
    numeric = frame.select_dtypes(include="number")
    corr = numeric.corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=6)
    ax.set_yticklabels(corr.columns, fontsize=6)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Numeric Feature Correlation")
    _save(path)
    return path.name


def _feature_by_target_boxplot(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "feature_vs_target_boxplot.svg"
    ax = frame.boxplot(column="compound_side_effect_count", by=TARGET)
    ax.set_title("Side-effect Count by CtD Label")
    ax.set_xlabel("ctd_label")
    ax.set_ylabel("compound_side_effect_count")
    plt.suptitle("")
    _save(path)
    return path.name


def _findings_markdown(frame: pd.DataFrame, profile: dict[str, object], figures: list[str]) -> str:
    duplicates = int(frame.duplicated(subset=["compound_id", "disease_id"]).sum())
    missing_cells = int(frame.isna().sum().sum())
    target_counts = frame[TARGET].value_counts().sort_index().to_dict()
    corr = (
        frame.select_dtypes(include="number")
        .corr()[TARGET]
        .drop(TARGET)
        .dropna()
        .sort_values(ascending=False)
    )
    top_positive = corr.head(3).round(3).to_dict()
    top_negative = corr.tail(3).round(3).to_dict()
    disease_positive_counts = (
        frame.loc[frame[TARGET] == 1, "disease_name"]
        .value_counts()
        .head(5)
        .to_dict()
    )

    return f"""# Sprint 3 EDA Findings

Generated from `data/processed/sprint3/ml_dataset.csv`.

## Dataset Summary

- Rows: {len(frame)}
- Columns: {len(frame.columns)}
- Train rows: {profile["train_rows"]}
- Test rows: {profile["test_rows"]}
- Target: `{TARGET}`
- Target distribution: {target_counts}
- Duplicate Compound x Disease pairs: {duplicates}
- Missing cells: {missing_cells}
- Unit of analysis: {profile["unit_of_analysis"]}

## Visualizations

1. `{figures[0]}` — target distribution shows the deterministic 2:1 sampled non-positive design.
2. `{figures[1]}` — missing-value overview confirms whether imputers should be active.
3. `{figures[2]}` — compound feature histograms show skewed graph-count features.
4. `{figures[3]}` — disease-level label counts show which represented diseases dominate the fallback task.
5. `{figures[4]}` — numeric correlation matrix checks redundant graph-count features.
6. `{figures[5]}` — side-effect count by target inspects one feature/target relationship.

## Data Quality Findings

- Required graph columns were validated before output generation.
- Target classes are stratified across the train/test split.
- No target or metadata columns are included by the preprocessing helper.
- The negative label means sampled lack of represented CtD in this fragment, not clinical non-treatment or safety.

## Feature/Target Findings

- Highest positive numeric correlations with `{TARGET}`: {top_positive}
- Lowest numeric correlations with `{TARGET}`: {top_negative}
- Top diseases by represented CtD positive rows: {disease_positive_counts}

## Preprocessing Implications

- Count features are numeric and can be median-imputed and scaled for Logistic Regression.
- Tree-based Sprint 4 models can reuse the same fitted-on-train preprocessing pipeline for comparability.
- Class balance is controlled by deterministic sampling, but evaluation should still report class-sensitive metrics.
"""


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, format="svg", metadata={"Date": None})
    plt.close("all")


if __name__ == "__main__":
    main()
