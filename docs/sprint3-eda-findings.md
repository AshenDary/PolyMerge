# Sprint 3 DDInter EDA Findings

Generated from `data/processed/sprint3/ddinter_severity_dataset.csv`.

## Dataset Summary

- Official raw rows: 222,664
- Canonical unique pairs before label filtering: 160,235
- Final known-severity pairs: 130,422
- Distinct DDInter drugs: 1,939
- Class counts: {'Major': 26914, 'Moderate': 96675, 'Minor': 6833}
- Class percentages: {'Major': 20.64, 'Moderate': 74.12, 'Minor': 5.24}
- Unknown canonical pairs excluded: 29,813
- Exact duplicate source rows removed: 62,428
- Reverse-pair duplicates: 0
- Conflicting-label pairs quarantined: 0
- Malformed source rows excluded: 1

## Visualizations and Interpretation

1. `severity_distribution.svg`: Moderate dominates at 74.12%; Minor is only 5.24%, so accuracy alone would hide weak minority-class performance.
2. `atc_category_distribution.svg`: Category membership is uneven and pairs may occur in multiple category downloads; `source_file` and `atc_category` preserve that provenance.
3. `hetionet_mapping_coverage.svg`: Only 3,292 pairs have both drugs mapped; requiring complete graph coverage would retain just 2.52% and create a strongly selected subset.
4. `graph_feature_coverage.svg`: Per-drug graph features are available when that drug maps, while pairwise overlaps require both mappings. Train-fitted median imputation is therefore required.
5. `graph_degree_by_severity.svg`: Among both-mapped pairs, median A/B graph degrees by severity are {'Major': {'drug_a_graph_degree': 1.0, 'drug_b_graph_degree': 1.0}, 'Moderate': {'drug_a_graph_degree': 6.0, 'drug_b_graph_degree': 2.0}, 'Minor': {'drug_a_graph_degree': 65.0, 'drug_b_graph_degree': 80.0}}; this is descriptive and not model evidence.
6. `pairwise_overlap_by_severity.svg`: Mean pairwise overlaps among both-mapped rows are {'Major': {'shared_gene_count': 0.608, 'shared_side_effect_count': 3.597, 'shared_treated_disease_count': 0.07}, 'Moderate': {'shared_gene_count': 0.382, 'shared_side_effect_count': 5.045, 'shared_treated_disease_count': 0.037}, 'Minor': {'shared_gene_count': 0.729, 'shared_side_effect_count': 12.924, 'shared_treated_disease_count': 0.11}}; the magnitudes are small and class differences must be validated in Sprint 4.
7. `graph_feature_correlation.svg`: Correlated count and Jaccard features motivate fitting all preprocessing inside training/CV folds and checking model stability.

## Data Quality and Coverage

- DDInter severity is the sole target source. Unknown was retained in an interim audit file and never mapped to a known class.
- There are no synthetic negative or no-interaction rows. Absence from DDInter is not evidence of safety.
- Exact normalized-name mapping resolves 227 of 1,939 drugs (11.707%). Unmapped and ambiguous names are never accepted automatically.
- Largest absolute feature skews in the both-mapped subset: {'pharmacologic_class_jaccard': 35.65, 'shared_downregulated_gene_count': 35.4, 'shared_upregulated_gene_count': 35.3, 'shared_pharmacologic_class_count': 34.05, 'shared_gene_count': 31.73}.
- Official interaction CSVs provide no verified molecular structure identifiers, so RDKit descriptor coverage is 0% and no structures were fabricated.

## Sprint 4 Implications

- Use macro F1 as the primary comparison metric because Minor is uncommon and all three severity classes matter. Also report per-class precision/recall and a confusion matrix only after models are trained.
- Fit imputation, scaling, and any encoding on training data or CV folds only. Never resample the complete dataset before splitting.
- The primary pair-stratified split has 98.937% test-drug overlap with train and only 19 fully novel test drugs. This evaluates new pairs mostly among known drugs, not cold-start drug generalization.
- Preserve the final test set for one final comparison; feature selection and tuning belong inside training-only cross-validation.
