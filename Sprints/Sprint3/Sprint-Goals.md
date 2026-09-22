# Sprint 3 - Dataset, EDA & Traditional Feature Engineering

## Goal

Build the reproducible supervised-data foundation for Sprint 4 traditional
machine-learning comparison while keeping graph evidence separate from future
model predictions.

## Implemented Dataset Decision

- Primary source: official DDInter 2.0 downloads under CC BY-NC-SA 4.0.
- Target: `ddi_severity`, with Major, Moderate, and Minor classes.
- Unknown remains auditable but is excluded from supervised data.
- Hetionet supplies optional graph features; `CrC` is never a DDI label.
- The old CtD task is retained only as a legacy prototype.

## Definition of Done

- [x] DDInter source provenance, license, hashes, and target are documented
- [x] No synthetic negatives or no-interaction class are created
- [x] Pair canonicalization, duplicate, conflict, and Unknown audits exist
- [x] DDInter-to-Hetionet mapping coverage is explicit
- [x] Data dictionary exists
- [x] Dataset loading, validation, feature generation, and split code are reusable
- [x] EDA script, written findings, and at least five figures exist
- [x] Leakage-safe preprocessing helper exists for Sprint 4
- [x] Train/test split is deterministic and stratified
- [x] Tests pass
- [x] No model training, GNN, graph embedding, neural network, transformer, or TransE is added
