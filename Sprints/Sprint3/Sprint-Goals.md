# Sprint 3 - Dataset, EDA & Traditional Feature Engineering

## Goal

Build the reproducible supervised-data foundation for Sprint 4 traditional
machine-learning comparison while keeping graph evidence separate from future
model predictions.

## Implemented Dataset Decision

- No legitimate DDI label dataset is present in the repository.
- Hetionet `CrC` is not a DDI label.
- Sprint 3 uses the documented fallback: represented `CtD` relationship
  classification over Compound x Disease pairs.

## Definition of Done

- [x] Dataset decision and fallback target are documented
- [x] Data dictionary exists
- [x] Dataset loading, validation, feature generation, and split code are reusable
- [x] EDA script, written findings, and at least five figures exist
- [x] Leakage-safe preprocessing helper exists for Sprint 4
- [x] Train/test split is deterministic and stratified
- [x] Tests pass
- [x] No model training, GNN, graph embedding, neural network, or PyTorch model is added
