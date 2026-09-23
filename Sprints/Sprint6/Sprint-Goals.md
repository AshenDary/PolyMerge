# Sprint 6 - Integration & Evaluation

## Goal

Integrate the complete research pipeline.

## Pipeline

Researcher -> Disease Selection -> Neo4j -> Candidate Generation -> Hard Safety Rules -> Optimization -> ML Prediction -> Ranking -> Explainability -> Research Results

## Evaluation Baselines

- [ ] Rule-based baseline
- [ ] Greedy KG baseline
- [ ] Logistic Regression baseline
- [ ] Random Forest baseline
- [ ] Histogram Gradient Boosting baseline (`GradientBoostingClassifier` fallback if required)

## Metrics to Track

- [ ] Knowledge-graph treatment coverage
- [ ] Number of drugs
- [ ] Predicted interaction risk
- [ ] Evidence strength
- [ ] Uncertainty
- [ ] AUROC
- [ ] AUPRC
- [ ] F1
- [ ] Reproducibility

## Constraint

Do not describe graph coverage as clinical efficacy or safety.
