# Sprint 3 DDInter Feature Foundation

## Dataset Contract

The task remains three-class severity classification for known curated DDInter
2.0 pairs: Major, Moderate, or Minor. Unknown is audited and excluded. No
synthetic non-interactions are generated, and absence is never treated as safe.

## Reproducible Sources

- DDInter 2.0: labels and pair provenance; official files are checksum-verified.
- PubChem PUG REST: chemical identity and structures. Queries are cached locally,
  started below five requests/second, and accepted only for a single exact
  normalized title with SMILES, InChI, InChIKey, and successful RDKit parsing.
- RDKit: molecular weight, LogP, TPSA, HBD, HBA, and rotatable-bond counts.
- Hetionet: graph context only. `CrC` is resemblance, never DDI severity.

Run `scripts/acquire_ddinter.py`, `scripts/enrich_pubchem.py`,
`scripts/build_sprint3_dataset.py`, then `scripts/run_sprint3_eda.py`. The
PubChem JSONL cache makes normal rebuilds offline and deterministic.

## Coverage and Features

PubChem provides 1,315 accepted structures for 1,939 drugs (67.818%); 77,764
pairs have both structures (59.62%). Hetionet mapping remains 227 drugs
(11.707%) and 3,292 both-mapped pairs (2.52%) because the checked-in graph nodes
contain no additional stable cross-reference.

The 55 model features are symmetric under pair swapping: mean and absolute
difference for drug-level values, and intersection/union/Jaccard for graph sets.
Coverage indicators are complete. Missing graph or molecular measurements are
`NaN`, while a represented empty graph set is a known zero. The feature-coverage
artifact reports missingness, zeros, unique values, and distribution statistics.

## Splits and Preprocessing

The primary 80/20 pair-stratified split remains fixed at random state 42 and has
98.937% test-drug overlap. A secondary deterministic 10% drug-holdout split
ensures every test pair includes at least one unseen drug. Partner drugs may
still be familiar, so this is cold-start analysis, not a fully drug-disjoint set.

The shared `ColumnTransformer` excludes labels, identifiers, names, mapping
metadata, and provenance. Median imputation and scaling are fitted only on
training data or CV folds.

Sprint 4 should compare Logistic Regression, Random Forest, and
HistGradientBoostingClassifier using identical folds and macro F1. The literal
GradientBoostingClassifier is the fallback if required by the course. A
most-frequent predictor is context only, not one of the three models. Class
weights or resampling may be investigated only inside training/CV folds.

No model has been trained or selected. Application output remains
`mlStatus: "not_applied"`.
