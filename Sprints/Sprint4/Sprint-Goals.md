# Sprint 4 - Traditional Supervised ML Model Comparison

## Goal

Train and compare the course-required traditional supervised models using the
Sprint 3 dataset, split, preprocessing helper, and target definition.

## Shared Tasks

- [ ] Train Logistic Regression
- [ ] Train Random Forest
- [ ] Train Gradient Boosting
- [ ] Use `data/processed/sprint3/train.csv`
- [ ] Use `data/processed/sprint3/test.csv`
- [ ] Use `ml_engine/app/data/preprocessing.py`
- [ ] Fit preprocessing on train only
- [ ] Report the same primary metric for all three models
- [ ] Document row-split leakage risk and limitations

## Important Constraint

Hetionet `CrC` must not be treated as a DDI dataset. Sprint 3 fallback labels
describe represented `CtD` relationships, not clinical truth.
