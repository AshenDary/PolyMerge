# Sprint 3 EDA Findings

Generated from `data/processed/sprint3/ml_dataset.csv`.

## Dataset Summary

- Rows: 426
- Columns: 21
- Train rows: 340
- Test rows: 86
- Target: `ctd_label`
- Target distribution: {0: 284, 1: 142}
- Duplicate Compound x Disease pairs: 0
- Missing cells: 0
- Unit of analysis: one row = one Compound x Disease pair

## Visualizations

1. `target_distribution.svg` — target distribution shows the deterministic 2:1 sampled non-positive design.
2. `missing_values.svg` — missing-value overview confirms whether imputers should be active.
3. `compound_feature_distributions.svg` — compound feature histograms show skewed graph-count features.
4. `target_by_disease.svg` — disease-level label counts show which represented diseases dominate the fallback task.
5. `numeric_correlation.svg` — numeric correlation matrix checks redundant graph-count features.
6. `feature_vs_target_boxplot.svg` — side-effect count by target inspects one feature/target relationship.

## Data Quality Findings

- Required graph columns were validated before output generation.
- Target classes are stratified across the train/test split.
- No target or metadata columns are included by the preprocessing helper.
- The negative label means sampled lack of represented CtD in this fragment, not clinical non-treatment or safety.

## Feature/Target Findings

- Highest positive numeric correlations with `ctd_label`: {'disease_graph_degree': 0.696, 'disease_other_ctd_compound_count': 0.685, 'compound_graph_degree': 0.57}
- Lowest numeric correlations with `ctd_label`: {'compound_other_ctd_disease_count': 0.21, 'compound_cpD_disease_count': 0.161, 'disease_cpD_compound_count': -0.079}
- Top diseases by represented CtD positive rows: {'hypertension': 68, 'coronary artery disease': 28, 'type 2 diabetes mellitus': 22, 'atherosclerosis': 6, 'glaucoma': 3}

## Preprocessing Implications

- Count features are numeric and can be median-imputed and scaled for Logistic Regression.
- Tree-based Sprint 4 models can reuse the same fitted-on-train preprocessing pipeline for comparability.
- Class balance is controlled by deterministic sampling, but evaluation should still report class-sensitive metrics.
