# Sprint 4 Model Comparison Scripts

This directory contains scripts for executing the Sprint 4 model comparison and selection process.

## Overview

Sprint 4 focuses on comparing three traditional classifiers using cross-validation on the training data:
1. LogisticRegression
2. RandomForestClassifier  
3. HistGradientBoostingClassifier

The **primary selection metric is macro F1**, which gives equal weight to all severity classes.

## Prerequisites

1. **Dataset Built**: Run the dataset builder to generate `train.csv`:
   ```bash
   python -m app.data.ddinter_dataset
   # or whatever the dataset builder script is
   ```

2. **Python Dependencies**:
   ```bash
   pip install scikit-learn pandas numpy matplotlib seaborn
   ```

3. **Verify Contract** (optional but recommended):
   ```bash
   python scripts/validate_sprint4_contract.py
   ```

## Running the Comparison

### Step 1: Execute Model Comparison

```bash
python ml_engine/scripts/run_sprint4_model_comparison.py
```

**What it does:**
- Loads training data (104,337 samples)
- Evaluates 3 candidate models + baseline using 5-fold CV
- Computes macro F1, per-class metrics, confusion matrices, AUROC
- Generates comprehensive JSON report
- Prints summary to console
- **Does NOT touch the test set**

**Output:**
- `data/interim/sprint4/model_comparison_report.json`

**Duration:** 5-15 minutes depending on hardware

### Step 2: Generate Visualizations

```bash
python ml_engine/scripts/visualize_model_comparison.py
```

**What it does:**
- Loads the JSON report from Step 1
- Creates 5 visualization plots
- Saves as SVG files

**Output:**
- `docs/figures/sprint4/macro_f1_comparison.svg`
- `docs/figures/sprint4/per_class_performance.svg`
- `docs/figures/sprint4/confusion_matrices.svg`
- `docs/figures/sprint4/metric_distributions.svg`
- `docs/figures/sprint4/minority_class_focus.svg`

**Duration:** <1 minute

## Understanding the Results

### Primary Metric: Macro F1

Macro F1 is the unweighted average of per-class F1 scores:

```
Macro F1 = (F1_Major + F1_Moderate + F1_Minor) / 3
```

This metric treats all classes equally, making it appropriate when:
- Classes are imbalanced
- Minority class performance matters
- You want balanced performance across severities

### Model Selection

The model with the **highest mean macro F1** across 5 CV folds is recommended for Sprint 5 final evaluation.

### Interpreting Variability

Standard deviation across folds indicates:
- **Low std**: Stable, consistent performance
- **High std**: Sensitive to data composition, potential overfitting

### Minority Class Performance

Pay special attention to Minor class metrics:
- Low support (fewer samples)
- Often harder to predict correctly
- Critical for balanced clinical decision-support

## File Locations

### Inputs
- Training data: `data/processed/sprint3/train.csv`
- Test data (untouched): `data/processed/sprint3/test.csv`

### Outputs
- JSON report: `data/interim/sprint4/model_comparison_report.json`
- Figures: `docs/figures/sprint4/*.svg`

### Code
- Comparison logic: `ml_engine/app/models/model_comparison.py`
- Preprocessing: `ml_engine/app/data/preprocessing.py`
- Dataset: `ml_engine/app/data/ddinter_dataset.py`

### Documentation
- This README: `ml_engine/scripts/README_sprint4.md`
- Full report template: `docs/sprint4-model-comparison.md`
- Experiment contract: `docs/sprint4-experiment-contract.md`

## Customization

### Changing CV Folds

Edit `run_sprint4_model_comparison.py`:

```python
report = generate_comparison_report(
    train_data=train_data,
    cv_folds=10,  # Change from 5 to 10
    random_state=42,
)
```

### Adding Models

Edit `ml_engine/app/models/model_comparison.py`:

```python
def get_model_pipelines() -> dict[str, Pipeline]:
    preprocessing = build_preprocessing_pipeline()
    
    return {
        "LogisticRegression": ...,
        "RandomForestClassifier": ...,
        "HistGradientBoostingClassifier": ...,
        "YourNewModel": Pipeline([
            ("preprocessing", preprocessing),
            ("classifier", YourClassifier(...)),
        ]),
    }
```

### Tuning Hyperparameters

Models currently use default or lightly tuned parameters. To add comprehensive tuning:

1. Use `GridSearchCV` or `RandomizedSearchCV` within the pipeline
2. Ensure preprocessing is fitted only on training folds
3. Update `evaluate_model()` to handle nested CV
4. Be mindful of computation time

## Troubleshooting

### "Training data not found"

**Solution**: Run the dataset builder first:
```bash
python scripts/build_sprint3_dataset.py
# or equivalent dataset generation script
```

### "Comparison report not found" (visualization)

**Solution**: Run the comparison script before visualization:
```bash
python ml_engine/scripts/run_sprint4_model_comparison.py
```

### Memory errors

**Solution**: 
- Reduce `n_jobs=-1` to `n_jobs=1` in `evaluate_model()`
- Reduce `cv_folds` from 5 to 3
- Use a machine with more RAM

### Slow execution

**Tips**:
- Reduce `n_estimators` in RandomForest (e.g., 50 instead of 100)
- Reduce `max_iter` in HistGradientBoosting
- Use `n_jobs=-1` for parallel fold processing
- Run on a machine with more CPU cores

## Next Steps

After reviewing the Sprint 4 comparison results:

1. **Document the recommendation** in `docs/sprint4-model-comparison.md`
2. **Prepare for Sprint 5**: Final evaluation on untouched test set
3. **Optional**: Run secondary cold-start evaluation
4. **Optional**: Perform model interpretation/explainability analysis

## Sprint 5 Preview

Sprint 5 will:
- Load the selected model from Sprint 4
- Train on full training set (no CV)
- Evaluate once on the untouched test set
- Generate final performance report
- Compare validation vs test performance
- Optionally evaluate on secondary cold-start split

**Critical**: No model selection or tuning decisions are made using test set results.

## Questions?

Refer to:
- Issue #33: Sprint 4 task description
- `docs/sprint4-experiment-contract.md`: Feature and split definitions
- `docs/sprint4-model-comparison.md`: Full methodology documentation
