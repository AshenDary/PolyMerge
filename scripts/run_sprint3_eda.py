"""Generate enriched DDInter Sprint 3 EDA figures and findings."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "data" / "processed" / "sprint3" / "ddinter_severity_dataset.csv"
PROFILE_PATH = REPO_ROOT / "data" / "interim" / "sprint3" / "dataset_profile.json"
COVERAGE_PATH = REPO_ROOT / "data" / "interim" / "sprint3" / "feature_coverage.csv"
FIGURE_DIR = REPO_ROOT / "docs" / "figures" / "sprint3"
FINDINGS_PATH = REPO_ROOT / "docs" / "sprint3-eda-findings.md"
TARGET = "ddi_severity"
CLASS_ORDER = ["Major", "Moderate", "Minor"]
COLORS = ["#b7423c", "#d69b2d", "#3d7d74"]

rcParams["svg.hashsalt"] = "polymerge-sprint3-enriched"


def main() -> None:
    frame = pd.read_csv(DATASET_PATH)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    coverage = pd.read_csv(COVERAGE_PATH)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    figures = [
        _severity_distribution(frame), _pubchem_mapping(profile),
        _structure_coverage(frame), _hetionet_mapping(frame),
        _feature_missingness(coverage), _descriptor_distributions(frame),
        _feature_variance(coverage),
    ]
    FINDINGS_PATH.write_text(_findings_markdown(frame, profile, coverage, figures), encoding="utf-8")
    print(f"Wrote {len(figures)} EDA figures to {FIGURE_DIR}")
    print(f"Wrote EDA findings: {FINDINGS_PATH}")


def _severity_distribution(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "severity_distribution.svg"
    ax = frame[TARGET].value_counts().reindex(CLASS_ORDER).plot(kind="bar", color=COLORS, rot=0)
    ax.set(title="DDInter Severity Class Distribution", xlabel="Severity", ylabel="Unique drug pairs")
    _save(path)
    return path.name


def _pubchem_mapping(profile: dict[str, object]) -> str:
    path = FIGURE_DIR / "pubchem_mapping_status.svg"
    counts = pd.Series(profile["pubchem_mapping_status_counts"]).sort_values(ascending=False)
    ax = counts.plot(kind="bar", color="#4978a8", rot=15)
    ax.set(title="DDInter to PubChem Mapping Status", xlabel="Status", ylabel="Distinct drugs")
    _save(path)
    return path.name


def _structure_coverage(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "pair_structure_coverage.svg"
    order = ["both_structured", "one_structured", "neither_structured"]
    counts = frame["pair_structure_coverage"].value_counts().reindex(order)
    ax = counts.plot(kind="bar", color=["#3d7d74", "#d69b2d", "#7b7b7b"], rot=10)
    ax.set(title="PubChem Structure Coverage per Pair", xlabel="Coverage", ylabel="Unique pairs")
    _save(path)
    return path.name


def _hetionet_mapping(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "hetionet_mapping_coverage.svg"
    order = ["both_mapped", "only_drug_a_mapped", "only_drug_b_mapped", "neither_mapped"]
    counts = frame["pair_mapping_coverage"].value_counts().reindex(order)
    ax = counts.plot(kind="bar", color=["#3d7d74", "#6f9f8d", "#8ba6bf", "#7b7b7b"], rot=15)
    ax.set(title="Hetionet Mapping Coverage per Pair", xlabel="Coverage", ylabel="Unique pairs")
    _save(path)
    return path.name


def _feature_missingness(coverage: pd.DataFrame) -> str:
    path = FIGURE_DIR / "feature_missingness.svg"
    ordered = coverage.sort_values("missing_percentage", ascending=False)
    colors = ordered["provenance"].map({"Hetionet graph": "#4978a8", "PubChem structure + RDKit": "#3d7d74"})
    ax = ordered.plot(kind="barh", x="feature", y="missing_percentage", figsize=(9, 12), color=colors, legend=False)
    ax.set(title="Feature Missingness by Provenance", xlabel="Missing rows (%)", ylabel="Feature")
    _save(path)
    return path.name


def _descriptor_distributions(frame: pd.DataFrame) -> str:
    path = FIGURE_DIR / "rdkit_descriptor_distributions.svg"
    columns = ["molecular_weight_mean", "logp_mean", "tpsa_mean"]
    structured = frame.loc[frame["both_structures_available"] == 1]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for axis, column in zip(axes, columns):
        for label, color in zip(CLASS_ORDER, COLORS):
            structured.loc[structured[TARGET] == label, column].plot(
                kind="hist", bins=35, alpha=0.45, density=True, ax=axis, label=label, color=color
            )
        axis.set_title(column.replace("_", " "))
        axis.set_ylabel("Density")
    axes[-1].legend()
    _save(path)
    return path.name


def _feature_variance(coverage: pd.DataFrame) -> str:
    path = FIGURE_DIR / "feature_variance.svg"
    values = coverage.set_index("feature")["std"].pow(2).sort_values()
    ax = np.log10(values.replace(0, np.nan)).plot(kind="barh", figsize=(9, 12), color="#8064a2")
    ax.set(title="Feature Variance (log10 scale)", xlabel="log10 variance", ylabel="Feature")
    _save(path)
    return path.name


def _findings_markdown(frame: pd.DataFrame, profile: dict[str, object], coverage: pd.DataFrame, figures: list[str]) -> str:
    counts = frame[TARGET].value_counts().reindex(CLASS_ORDER)
    percentages = (counts / len(frame) * 100).round(2)
    both_graph = profile["pair_mapping_coverage"]["both_mapped"]
    both_structures = profile["pair_structure_coverage"].get("both_structured", 0)
    molecular = coverage.loc[coverage["provenance"] == "PubChem structure + RDKit"]
    graph = coverage.loc[coverage["provenance"] == "Hetionet graph"]
    secondary = profile["secondary_split"]
    descriptor_maxima = frame[[
        "molecular_weight_mean", "logp_mean", "tpsa_mean",
        "hbd_mean", "hba_mean", "rotatable_bonds_mean",
    ]].max().round(3).to_dict()
    return f"""# Sprint 3 DDInter Feature-Enrichment EDA

Generated from `data/processed/sprint3/ddinter_severity_dataset.csv` without model training.

## Dataset and Labels

- Final known-severity pairs: {len(frame):,}; distinct drugs: {profile['distinct_ddinter_drugs']:,}.
- Class counts: {counts.to_dict()}.
- Class percentages: {percentages.to_dict()}.
- DDInter remains the sole label source. Unknown is excluded, with no synthetic negatives.

## Identity and Structure Coverage

- PubChem exact-title mappings with RDKit-valid structures: {profile['valid_structure_count']:,} ({profile['rdkit_structure_coverage_percentage']:.3f}% of drugs).
- PubChem status counts: {profile['pubchem_mapping_status_counts']}.
- Pair structure coverage: {profile['pair_structure_coverage']}; both-structured coverage is {100 * both_structures / len(frame):.2f}%.
- Hetionet exact-name mappings remain {profile['exact_name_mapping_count']:,} ({profile['mapping_percentage']:.3f}%); the checked-in graph metadata has no additional stable cross-reference.
- Both-drugs-Hetionet coverage remains {both_graph:,} pairs ({100 * both_graph / len(frame):.2f}%).

## Visualizations and Interpretation

1. `{figures[0]}`: Moderate remains dominant and Minor remains 5.24%, supporting macro F1.
2. `{figures[1]}`: PubChem mappings are accepted only for exact normalized title matches with valid structures; title mismatches remain ambiguous.
3. `{figures[2]}`: Molecular descriptors are available only when both pair members have accepted structures; one-structure pairs remain explicitly incomplete.
4. `{figures[3]}`: Hetionet pair coverage remains sparse, so the graph cannot be the sole feature source.
5. `{figures[4]}`: Graph and molecular missingness are shown separately. Availability indicators are complete, while unavailable measurements remain `NaN`.
6. `{figures[5]}`: RDKit molecular-weight, LogP, and TPSA distributions are shown only for both-structured pairs and are descriptive, not model-selection evidence.
7. `{figures[6]}`: Unsupervised variance auditing flagged these constant or near-constant features: {profile['constant_or_near_constant_features']}. No target-informed feature removal occurred.

## Feature Semantics

- All drug-level graph and molecular measurements are symmetric pair summaries (`mean`, `abs_difference`), so swapping pair order does not change X.
- Set features use intersection, union, and Jaccard. `CrC` remains chemical resemblance context and never supplies DDI truth.
- Known graph zeros remain `0`; mapping failures remain `NaN`. `hetionet_available_count` and `both_hetionet_available` expose coverage.
- Missing structures remain `NaN`. `structure_available_count` and `both_structures_available` expose molecular coverage.
- Median imputation and scaling remain train-fitted through the shared `ColumnTransformer`.
- Molecular feature missingness ranges from {molecular['missing_percentage'].min():.2f}% to {molecular['missing_percentage'].max():.2f}%; graph feature missingness ranges from {graph['missing_percentage'].min():.2f}% to {graph['missing_percentage'].max():.2f}%.
- Descriptor maxima are {descriptor_maxima}. Large biologic and multi-component records create real outliers; scaling and robustness checks must stay inside training/CV.

## Split and Sprint 4 Implications

- Primary split: {profile['train_rows']:,}/{profile['test_rows']:,}, stratified, with {profile['test_drug_overlap_percentage']:.3f}% test-drug overlap.
- Secondary cold-start split: {secondary['train_rows']:,}/{secondary['test_rows']:,}; {secondary['holdout_drugs']} held-out drugs and {secondary['held_out_drugs_seen_in_train']} held-out drugs leak into training.
- Secondary class distributions are train {secondary['train_target_distribution']} and test {secondary['test_target_distribution']}; the holdout remains usable but is not exactly stratified.
- The secondary test guarantees at least one unseen drug per pair, but partner drugs may be familiar; it is not a fully drug-disjoint partition.
- Sprint 4 should compare Logistic Regression, Random Forest, and HistGradientBoostingClassifier with identical training-only CV folds and macro F1. Use GradientBoostingClassifier only if the course requires that literal class.
- Class weighting or resampling may be investigated only inside training/CV folds. The primary test set remains untouched.
"""


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, format="svg", metadata={"Date": None})
    plt.close("all")
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
