# Sprint 4 Model Comparison Report

## Objective

Define and produce the Sprint 4 comparison report used to select one traditional classifier from shared cross-validation results without evaluating the untouched test set early.

## Executive Summary

This report documents the comparison of three candidate machine learning models for DDI severity classification using 5-fold stratified cross-validation on the training data. The **primary selection metric is macro F1**, which gives equal weight to all three severity classes (Major, Moderate, Minor) regardless of their frequency in the dataset.

### Key Findings

- **Best Model**: [To be determined after running evaluation]
- **Selection Basis**: Highest mean macro F1 score across 5 cross-validation folds
- **Test Set Status**: Untouched and reserved for Sprint 5 final evaluation
- **Baseline Context**: Most-frequent classifier included as non-competing baseline

## Scope

### Models Compared

1. **LogisticRegression**
   - Multi-class multinomial logistic regression
   - Linear decision boundaries
   - Interpretable coefficients
   - Configuration: `max_iter=1000`, `solver='lbfgs'`, `random_state=42`

2. **RandomForestClassifier**
   - Ensemble of decision trees
   - Non-linear decision boundaries
   - Handles feature interactions
   - Configuration: `n_estimators=100`, `class_weight='balanced'`, `random_state=42`

3. **HistGradientBoostingClassifier**
   - Histogram-based gradient boosting
   - Fast training on large datasets
   - Native support for missing values
   - Configuration: `max_iter=100`, `learning_rate=0.1`, `random_state=42`

### Baseline

- **Most-Frequent Classifier (DummyClassifier)**
  - Always predicts the majority class
  - Provides non-competing context for minimum acceptable performance
  - Not a candidate for selection

## Evaluation Protocol

### Dataset

- **Source**: DDInter 2.0 processed dataset
- **Training Rows**: 104,337 canonical drug pairs
- **Test Rows**: 26,085 pairs (untouched)
- **Features**: 55 numeric symmetric pair features
  - Hetionet graph summaries and availability indicators
  - PubChem structure availability indicators
  - RDKit molecular descriptor summaries
- **Target Classes**: Major, Moderate, Minor
- **Split Strategy**: 80/20 stratified by severity, random_state=42

### Cross-Validation Strategy

- **Method**: StratifiedKFold
- **Folds**: 5
- **Stratification**: Target class (ddi_severity)
- **Shuffle**: True with random_state=42
- **Fit/Transform**: Preprocessing fitted on training folds only, then applied to validation folds

### Preprocessing Pipeline

All models use identical preprocessing:

1. **Imputation**: Median imputation for numeric features (fitted on training data per fold)
2. **Scaling**: StandardScaler normalization (fitted on training data per fold)
3. **Leak Prevention**: Preprocessing fitted only on training folds, never on validation data

Reference: `ml_engine/app/data/preprocessing.py`

### Metrics Collected

#### Primary Metric

- **Macro F1**: Unweighted average of per-class F1 scores
  - Gives equal importance to all classes regardless of frequency
  - **This is the sole model selection criterion**

#### Secondary Metrics (for context and minority-class assessment)

- **Per-Class Metrics**: Precision, Recall, F1 for each severity class
- **Weighted F1**: Class-frequency-weighted average F1
- **Micro F1**: Global precision and recall average
- **Accuracy**: Overall classification accuracy
- **AUROC**: Multi-class one-vs-rest area under ROC curve (where applicable)
- **Confusion Matrix**: Predicted vs true class counts

#### Minority Class Focus

Given the class imbalance, we explicitly report:
- Minor class precision, recall, and F1
- Per-class support (sample counts)
- Confusion patterns showing minority class misclassifications

## Comparison Results

> **Note**: Results will be populated when `run_sprint4_model_comparison.py` is executed.

### Macro F1 Comparison

| Model | Macro F1 Mean | Macro F1 Std | Status |
|-------|---------------|--------------|--------|
| Baseline (Most Frequent) | TBD | TBD | Non-competing context |
| Model 1 | TBD | TBD | Candidate |
| Model 2 | TBD | TBD | Candidate |
| Model 3 | TBD | TBD | Candidate |

### Per-Class Performance

#### Major Class

| Model | Precision | Recall | F1 Score | Support |
|-------|-----------|--------|----------|---------|
| LogisticRegression | TBD | TBD | TBD | TBD |
| RandomForestClassifier | TBD | TBD | TBD | TBD |
| HistGradientBoostingClassifier | TBD | TBD | TBD | TBD |

#### Moderate Class

| Model | Precision | Recall | F1 Score | Support |
|-------|-----------|--------|----------|---------|
| LogisticRegression | TBD | TBD | TBD | TBD |
| RandomForestClassifier | TBD | TBD | TBD | TBD |
| HistGradientBoostingClassifier | TBD | TBD | TBD | TBD |

#### Minor Class (Minority)

| Model | Precision | Recall | F1 Score | Support |
|-------|-----------|--------|----------|---------|
| LogisticRegression | TBD | TBD | TBD | TBD |
| RandomForestClassifier | TBD | TBD | TBD | TBD |
| HistGradientBoostingClassifier | TBD | TBD | TBD | TBD |

### Confusion Matrices

> See `docs/figures/sprint4/confusion_matrices.svg` after running visualization script.

### Cross-Validation Score Variability

Reporting mean ± standard deviation across folds provides uncertainty estimates:
- Low variability indicates stable, generalizable performance
- High variability suggests sensitivity to fold composition or potential overfitting

## Recommendation

### Selected Model

**Model**: [TBD after evaluation]

**Macro F1**: [TBD] ± [TBD]

**Justification**: 
[Will be populated with the model achieving highest mean macro F1 across cross-validation folds]

### Minority Class Performance

[Will document Minor class precision, recall, and F1 for the selected model]

### Next Steps

**Sprint 5**: Final evaluation on the untouched test set (26,085 pairs)
- Single evaluation run with no further tuning
- Comprehensive performance report
- Comparison of validation vs test performance
- Secondary cold-start split evaluation

## Limitations and Context

### Split Characteristics

1. **Drug Overlap**: 98.94% of test drugs appear in training
   - Split evaluates new combinations among familiar drugs
   - **Not** a cold-start or fully unseen-drug evaluation
   - Secondary cold-start split (190 held-out drugs) available for stress testing

2. **Pair-Level Split**: Pairs are disjoint between train/test, drugs are not
   - Tests generalization to new drug combinations
   - Does not test generalization to completely novel drugs

### Model Limitations

1. **Validation Performance**: Results are cross-validation on training data
   - Final test performance may differ
   - Test set is reserved for Sprint 5 unbiased evaluation

2. **Hyperparameter Tuning**: Models use default or lightly tuned parameters
   - No comprehensive grid search performed
   - Focus is on architecture comparison, not optimal tuning

3. **Class Imbalance**: Minority class (Minor) has limited representation
   - Macro F1 prioritizes balanced performance over majority-class accuracy
   - Per-class metrics show performance variability across severities

4. **Feature Coverage**: Graph and molecular features have varying availability
   - Missing values imputed from training data
   - Availability indicators distinguish missing from zero values

5. **Evaluation Scope**: Comparison uses the same folds and preprocessing
   - Ensures fair comparison
   - Does not explore alternative feature engineering or sampling strategies

### System Status

This is a **research classification system** for DDI severity prediction:
- **Not validated for clinical safety decisions**
- **Not a drug interaction compatibility claim**
- Intended for decision-support and research purposes only
- No clinical guarantee provided

### Provenance

- **Target Annotations**: DDInter 2.0
- **Chemical Identity**: PubChem PUG REST API
- **Molecular Descriptors**: RDKit
- **Graph Evidence**: Hetionet v1.0
- **Processing Scripts**: Checked into repository with manifests
- **Reproducibility**: All random states fixed, full pipeline documented

## Visualizations

After running the comparison, visualizations are generated in `docs/figures/sprint4/`:

1. **macro_f1_comparison.svg**: Bar chart comparing macro F1 across models
2. **per_class_performance.svg**: Per-class precision, recall, F1 breakdown
3. **confusion_matrices.svg**: Confusion matrices for each model
4. **metric_distributions.svg**: Distribution of CV scores across metrics
5. **minority_class_focus.svg**: Detailed Minor class performance analysis

## Reproducibility

### Running the Comparison

```bash
# Run model comparison (generates report JSON)
python ml_engine/scripts/run_sprint4_model_comparison.py

# Generate visualizations
python ml_engine/scripts/visualize_model_comparison.py
```

### Outputs

- **JSON Report**: `data/interim/sprint4/model_comparison_report.json`
- **Figures**: `docs/figures/sprint4/*.svg`
- **Console Summary**: Printed during execution

### Dependencies

- scikit-learn: Model training and evaluation
- pandas: Data manipulation
- numpy: Numerical operations
- matplotlib: Visualization
- seaborn: Statistical plotting

## References

- **Experiment Contract**: `docs/sprint4-experiment-contract.md`
- **Data Dictionary**: `docs/data-dictionary.md`
- **Feature Contract**: `data/interim/sprint4/feature_contract.json`
- **Dataset Profile**: `data/interim/sprint3/dataset_profile.json`
- **Preprocessing**: `ml_engine/app/data/preprocessing.py`
- **Model Comparison Code**: `ml_engine/app/models/model_comparison.py`

## Acceptance Criteria Checklist

- [x] Report structure and metric definitions are reproducible
- [x] Macro F1 is the sole primary model-selection metric
- [x] All three models compared under identical evaluation contract
- [x] Minority-class results and uncertainty/variability explicit
- [x] Untouched test set reserved for Sprint 5 final evaluation
- [x] Recommendation includes limitations and provenance
- [x] Results framed as research decision-support, not clinical guarantee
- [x] No separate model implementation trained (uses cross_validate)
- [x] No model serving activated
- [x] Predicted risk kept distinct from known graph evidence

---

**Document Version**: 1.0  
**Last Updated**: [To be set after first run]  
**Status**: Ready for evaluation execution
