# Sprint 4 Model Comparison

Sprint 4 has one canonical training-only comparison command, run from the
repository root:

```bash
python3 scripts/run_sprint4_training.py
```

The command loads `data/processed/sprint3/train.csv`, applies fold-local median
imputation and standard scaling, and evaluates the three approved classifiers
on one materialized five-fold `StratifiedKFold` split. The untouched
`data/processed/sprint3/test.csv` split is not loaded.

The machine-readable result is
`data/interim/sprint4/training_experiment.json`. It contains provenance,
parameters, fold metrics, out-of-fold metrics, the selected model, test
isolation, and inactive-serving metadata. Sprint 4 does not create a fitted
model artifact or figures.

The model set, parameters, folds, seed, preprocessing, and selection metric are
frozen by `docs/sprint4-experiment-contract.md`. They must not be customized
when reproducing this experiment. Macro F1 is the sole selection metric, and
the most-frequent baseline is context only.

Validate the contract with:

```bash
python3 scripts/validate_sprint4_contract.py
```

Full results and limitations are in `docs/sprint4-model-comparison.md`.
