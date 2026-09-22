"""Generate DDInter Sprint 3 EDA figures and data-grounded findings."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "data" / "processed" / "sprint3" / "ddinter_severity_dataset.csv"
PROFILE_PATH = REPO_ROOT / "data" / "interim" / "sprint3" / "dataset_profile.json"
FIGURE_DIR = REPO_ROOT / "docs" / "figures" / "sprint3"
FINDINGS_PATH = REPO_ROOT / "docs" / "sprint3-eda-findings.md"
TARGET = "ddi_severity"
CLASS_ORDER = ["Major", "Moderate", "Minor"]
COLORS = ["#b7423c", "#d69b2d", "#3d7d74"]

rcParams["svg.hashsalt"] = "polymerge-sprint3-ddinter"


def main() -> None:
    frame = pd.read_csv(DATASET_PATH)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figures = [
        _severity_distribution(frame), _category_distribution(frame),
        _mapping_coverage(frame), _feature_coverage(frame),
        _degree_by_severity(frame), _overlap_by_severity(frame),
        _numeric_correlation(frame),
    ]
    FINDINGS_PATH.write_text(_findings_markdown(frame, profile, figures), encoding="utf-8")
    print(f"Wrote {len(figures)} EDA figures to {FIGURE_DIR}")
    print(f"Wrote EDA findings: {FINDINGS_PATH}")


def _severity_distribution(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "severity_distribution.svg"
    ax = frame[TARGET].value_counts().reindex(CLASS_ORDER).plot(kind="bar", color=COLORS, rot=0)
    ax.set(title="DDInter Severity Class Distribution", xlabel="Severity", ylabel="Unique drug pairs")
    _save(path)
    return path.name


def _category_distribution(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "atc_category_distribution.svg"
    counts = frame["atc_category"].str.split(";").explode().value_counts().sort_index()
    ax = counts.plot(kind="bar", color="#4978a8", rot=0)
    ax.set(title="Supervised Pairs by Download Category", xlabel="ATC category code", ylabel="Pair memberships")
    _save(path)
    return path.name


def _mapping_coverage(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "hetionet_mapping_coverage.svg"
    order = ["both_mapped", "only_drug_a_mapped", "only_drug_b_mapped", "neither_mapped"]
    counts = frame["pair_mapping_coverage"].value_counts().reindex(order)
    ax = counts.plot(kind="bar", color=["#3d7d74", "#6f9f8d", "#8ba6bf", "#7b7b7b"], rot=15)
    ax.set(title="Hetionet Mapping Coverage per Drug Pair", xlabel="Mapping state", ylabel="Unique pairs")
    _save(path)
    return path.name


def _feature_coverage(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "graph_feature_coverage.svg"
    candidates = [column for column in frame if column.startswith("drug_") or column.startswith("shared_") or column.endswith("_jaccard")]
    columns = [column for column in candidates if frame[column].dtype.kind in "fi"]
    ax = frame[columns].notna().mean().mul(100).sort_values().plot(kind="barh", figsize=(8, 8), color="#5b7f95")
    ax.set(title="Graph Feature Availability", xlabel="Rows with a value (%)", ylabel="Feature")
    _save(path)
    return path.name


def _degree_by_severity(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "graph_degree_by_severity.svg"
    mapped = frame.loc[frame["pair_mapping_coverage"] == "both_mapped"]
    mapped.boxplot(column=["drug_a_graph_degree", "drug_b_graph_degree"], by=TARGET, figsize=(9, 5))
    plt.suptitle("Drug Graph Degree by DDInter Severity")
    _save(path)
    return path.name


def _overlap_by_severity(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "pairwise_overlap_by_severity.svg"
    columns = ["shared_gene_count", "shared_side_effect_count", "shared_treated_disease_count"]
    means = frame.groupby(TARGET)[columns].mean().reindex(CLASS_ORDER)
    ax = means.plot(kind="bar", color=["#4978a8", "#3d7d74", "#d69b2d"], rot=0)
    ax.set(title="Mean Pairwise Graph Overlap by Severity", xlabel="Severity", ylabel="Mean shared entities")
    _save(path)
    return path.name


def _numeric_correlation(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "graph_feature_correlation.svg"
    columns = ["drug_a_graph_degree", "drug_b_graph_degree", "shared_gene_count", "shared_side_effect_count", "shared_treated_disease_count", "gene_jaccard", "side_effect_jaccard", "disease_jaccard"]
    correlation = frame[columns].corr()
    fig, ax = plt.subplots(figsize=(7, 6))
    image = ax.imshow(correlation, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(columns)), labels=columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(columns)), labels=columns, fontsize=7)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Selected Graph Feature Correlations")
    _save(path)
    return path.name


def _findings_markdown(frame: pd.DataFrame, profile: dict[str, object], figures: list[str]) -> str:
    counts = frame[TARGET].value_counts().reindex(CLASS_ORDER)
    percentages = (counts / len(frame) * 100).round(2)
    mapped = frame.loc[frame["pair_mapping_coverage"] == "both_mapped"]
    overlap_columns = ["shared_gene_count", "shared_side_effect_count", "shared_treated_disease_count"]
    overlap_means = mapped.groupby(TARGET)[overlap_columns].mean().reindex(CLASS_ORDER).round(3)
    degree_columns = ["drug_a_graph_degree", "drug_b_graph_degree"]
    degree_medians = mapped.groupby(TARGET)[degree_columns].median().reindex(CLASS_ORDER)
    skewed = mapped[profile["feature_columns"]].skew(numeric_only=True).abs().sort_values(ascending=False).head(5).round(2).to_dict()
    both_mapped = profile["pair_mapping_coverage"]["both_mapped"]
    return f"""# Sprint 3 DDInter EDA Findings

Generated from `data/processed/sprint3/ddinter_severity_dataset.csv`.

## Dataset Summary

- Official raw rows: {profile['raw_rows']:,}
- Canonical unique pairs before label filtering: {profile['canonical_unique_pairs']:,}
- Final known-severity pairs: {len(frame):,}
- Distinct DDInter drugs: {profile['distinct_ddinter_drugs']:,}
- Class counts: {counts.to_dict()}
- Class percentages: {percentages.to_dict()}
- Unknown canonical pairs excluded: {profile['excluded_unknown_rows']:,}
- Exact duplicate source rows removed: {profile['exact_duplicate_rows']:,}
- Reverse-pair duplicates: {profile['reverse_duplicate_pair_count']:,}
- Conflicting-label pairs quarantined: {profile['conflicting_label_pair_count']:,}
- Malformed source rows excluded: {profile['malformed_rows']:,}

## Visualizations and Interpretation

1. `{figures[0]}`: Moderate dominates at {percentages['Moderate']:.2f}%; Minor is only {percentages['Minor']:.2f}%, so accuracy alone would hide weak minority-class performance.
2. `{figures[1]}`: Category membership is uneven and pairs may occur in multiple category downloads; `source_file` and `atc_category` preserve that provenance.
3. `{figures[2]}`: Only {both_mapped:,} pairs have both drugs mapped; requiring complete graph coverage would retain just {100 * both_mapped / len(frame):.2f}% and create a strongly selected subset.
4. `{figures[3]}`: Per-drug graph features are available when that drug maps, while pairwise overlaps require both mappings. Train-fitted median imputation is therefore required.
5. `{figures[4]}`: Among both-mapped pairs, median A/B graph degrees by severity are {degree_medians.to_dict('index')}; this is descriptive and not model evidence.
6. `{figures[5]}`: Mean pairwise overlaps among both-mapped rows are {overlap_means.to_dict('index')}; the magnitudes are small and class differences must be validated in Sprint 4.
7. `{figures[6]}`: Correlated count and Jaccard features motivate fitting all preprocessing inside training/CV folds and checking model stability.

## Data Quality and Coverage

- DDInter severity is the sole target source. Unknown was retained in an interim audit file and never mapped to a known class.
- There are no synthetic negative or no-interaction rows. Absence from DDInter is not evidence of safety.
- Exact normalized-name mapping resolves {profile['mapping_status_counts']['exact_name']:,} of {profile['distinct_ddinter_drugs']:,} drugs ({profile['mapping_percentage']:.3f}%). Unmapped and ambiguous names are never accepted automatically.
- Largest absolute feature skews in the both-mapped subset: {skewed}.
- Official interaction CSVs provide no verified molecular structure identifiers, so RDKit descriptor coverage is 0% and no structures were fabricated.

## Sprint 4 Implications

- Use macro F1 as the primary comparison metric because Minor is uncommon and all three severity classes matter. Also report per-class precision/recall and a confusion matrix only after models are trained.
- Fit imputation, scaling, and any encoding on training data or CV folds only. Never resample the complete dataset before splitting.
- The primary pair-stratified split has {profile['test_drug_overlap_percentage']:.3f}% test-drug overlap with train and only {profile['fully_novel_test_drugs']} fully novel test drugs. This evaluates new pairs mostly among known drugs, not cold-start drug generalization.
- Preserve the final test set for one final comparison; feature selection and tuning belong inside training-only cross-validation.
"""


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, format="svg", metadata={"Date": None})
    plt.close("all")


if __name__ == "__main__":
    main()
