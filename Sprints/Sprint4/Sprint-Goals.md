# Sprint 4 - Traditional Supervised ML Model Comparison

## Goal

Train and compare the course-required traditional supervised models using the
Sprint 3 dataset, split, preprocessing helper, and target definition.

## Shared Tasks

- [ ] Train Logistic Regression
- [ ] Train Random Forest
- [ ] Train Histogram Gradient Boosting (`GradientBoostingClassifier` fallback if required)
- [ ] Use `data/processed/sprint3/train.csv`
- [ ] Use `data/processed/sprint3/test.csv`
- [ ] Use `ml_engine/app/data/preprocessing.py`
- [ ] Fit preprocessing on train only
- [ ] Use macro F1 as the same primary metric for all three models
- [ ] Document pair-split drug overlap and cold-start limitations
- [ ] Keep the test split out of feature selection and tuning
- [ ] Report a most-frequent baseline for context only
- [ ] Apply weighting/resampling only inside training CV folds if justified

## Important Constraint

DDInter 2.0 is the label source. Hetionet `CrC` is resemblance context only.
Unknown is not a supervised class, and no missing pair is a safe negative.
