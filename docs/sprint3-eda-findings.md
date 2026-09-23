# Sprint 3 DDInter Feature-Enrichment EDA

Generated from `data/processed/sprint3/ddinter_severity_dataset.csv` without model training.

## Dataset and Labels

- Final known-severity pairs: 130,422; distinct drugs: 1,939.
- Class counts: {'Major': 26914, 'Moderate': 96675, 'Minor': 6833}.
- Class percentages: {'Major': 20.64, 'Moderate': 74.12, 'Minor': 5.24}.
- DDInter remains the sole label source. Unknown is excluded, with no synthetic negatives.

## Identity and Structure Coverage

- PubChem exact-title mappings with RDKit-valid structures: 1,315 (67.818% of drugs).
- PubChem status counts: {'ambiguous': 159, 'exact_unique': 1315, 'unmapped': 465}.
- Pair structure coverage: {'both_structured': 77764, 'neither_structured': 8907, 'one_structured': 43751}; both-structured coverage is 59.62%.
- Hetionet exact-name mappings remain 227 (11.707%); the checked-in graph metadata has no additional stable cross-reference.
- Both-drugs-Hetionet coverage remains 3,292 pairs (2.52%).

## Visualizations and Interpretation

1. `severity_distribution.svg`: Moderate remains dominant and Minor remains 5.24%, supporting macro F1.
2. `pubchem_mapping_status.svg`: PubChem mappings are accepted only for exact normalized title matches with valid structures; title mismatches remain ambiguous.
3. `pair_structure_coverage.svg`: Molecular descriptors are available only when both pair members have accepted structures; one-structure pairs remain explicitly incomplete.
4. `hetionet_mapping_coverage.svg`: Hetionet pair coverage remains sparse, so the graph cannot be the sole feature source.
5. `feature_missingness.svg`: Graph and molecular missingness are shown separately. Availability indicators are complete, while unavailable measurements remain `NaN`.
6. `rdkit_descriptor_distributions.svg`: RDKit molecular-weight, LogP, and TPSA distributions are shown only for both-structured pairs and are descriptive, not model-selection evidence.
7. `feature_variance.svg`: Unsupervised variance auditing flagged these constant or near-constant features: ['pharmacologic_class_intersection_count', 'pharmacologic_class_jaccard']. No target-informed feature removal occurred.

## Feature Semantics

- All drug-level graph and molecular measurements are symmetric pair summaries (`mean`, `abs_difference`), so swapping pair order does not change X.
- Set features use intersection, union, and Jaccard. `CrC` remains chemical resemblance context and never supplies DDI truth.
- Known graph zeros remain `0`; mapping failures remain `NaN`. `hetionet_available_count` and `both_hetionet_available` expose coverage.
- Missing structures remain `NaN`. `structure_available_count` and `both_structures_available` expose molecular coverage.
- Median imputation and scaling remain train-fitted through the shared `ColumnTransformer`.
- Molecular feature missingness ranges from 0.00% to 29.55%; graph feature missingness ranges from 0.00% to 97.48%.
- Descriptor maxima are {'molecular_weight_mean': 6971.528, 'logp_mean': 17.263, 'tpsa_mean': 3097.005, 'hbd_mean': 99.5, 'hba_mean': 109.0, 'rotatable_bonds_mean': 182.5}. Large biologic and multi-component records create real outliers; scaling and robustness checks must stay inside training/CV.

## Split and Sprint 4 Implications

- Primary split: 104,337/26,085, stratified, with 98.937% test-drug overlap.
- Secondary cold-start split: 105,979/24,443; 190 held-out drugs and 0 held-out drugs leak into training.
- Secondary class distributions are train {'Major': 22375, 'Minor': 5562, 'Moderate': 78042} and test {'Major': 4539, 'Minor': 1271, 'Moderate': 18633}; the holdout remains usable but is not exactly stratified.
- The secondary test guarantees at least one unseen drug per pair, but partner drugs may be familiar; it is not a fully drug-disjoint partition.
- Sprint 4 should compare Logistic Regression, Random Forest, and HistGradientBoostingClassifier with identical training-only CV folds and macro F1. Use GradientBoostingClassifier only if the course requires that literal class.
- Class weighting or resampling may be investigated only inside training/CV folds. The primary test set remains untouched.
