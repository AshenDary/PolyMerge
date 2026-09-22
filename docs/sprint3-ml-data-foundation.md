# Sprint 3 DDInter ML Data Foundation

## Dataset Contract

- Task: classify severity for a known curated DDInter drug pair.
- Unit: one unique canonical unordered pair, keyed by stable DDInter IDs.
- Target: `ddi_severity` from DDInter 2.0.
- Classes: Major, Moderate, Minor.
- Excluded label: Unknown, retained in an interim audit file.
- Graph feature source: the checked-in Hetionet fragment.
- Molecular descriptors: not applied because the official downloads provide no
  verified SMILES, InChI, or InChIKey.

There are no generated non-interactions or synthetic negatives. Missing DDInter
records are never interpreted as safe. Hetionet `CrC` contributes resemblance
context only and is never a label or severity proxy.

## Reproducibility and Provenance

The tracked source manifest records the official DDInter 2.0 download and terms
pages, CC BY-NC-SA 4.0 license, retrieval date, source filenames, and SHA-256
checksums. Raw CSVs are ignored. `scripts/acquire_ddinter.py` retrieves and
verifies them before `scripts/build_sprint3_dataset.py` runs.

The builder validates the observed five-column schema, preserves source file and
ATC category provenance, excludes malformed rows, canonicalizes by DDInter IDs,
deduplicates cross-category records, and quarantines any pair with conflicting
known labels. It never applies a highest-severity rule.

## Mapping and Features

DDInter names map to Hetionet compounds only when a normalized exact name has one
unambiguous candidate. Mapping statuses are `exact_name`, `ambiguous`, or
`unmapped`; ambiguous candidates are not accepted. All DDInter rows remain in
the primary dataset because requiring both mappings would retain only 3,292 of
130,422 pairs.

The 29 traditional graph features include per-drug relationship counts and
degree plus pairwise shared-entity counts and Jaccard similarities. Missing
features represent unavailable graph coverage, not zero biological activity.

## Split and Preprocessing

The checked-in primary split is 80/20, stratified by severity, with random state
42. Canonical pairs cannot cross splits. The same drug can appear in both; the
profile records 98.937% test-drug overlap, so the split primarily evaluates new
pairs among familiar drugs rather than cold-start drugs.

`ml_engine/app/data/preprocessing.py` returns `X`, `y`, and a scikit-learn
`ColumnTransformer`. Target and metadata fields are excluded. Imputation,
scaling, and encoding must be fitted on training data or CV folds only.

Sprint 4 can compare Logistic Regression, Random Forest, and Gradient Boosting
using the same split and preprocessing contract. Macro F1 is recommended due to
the small Minor class. No predictive model has been trained in Sprint 3, and
application responses remain `mlStatus: "not_applied"`.
