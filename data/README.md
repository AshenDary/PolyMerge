# PolyMerge Data

## Primary Sprint 3 Source

The primary supervised dataset is DDInter 2.0. Its official eight category CSVs
are downloaded from `https://ddinter2.scbdd.com/download/` under CC BY-NC-SA
4.0. Raw files are intentionally ignored because redistribution is subject to
the source license. The tracked `data/original/ddinter/source_manifest.json`
records retrieval date, source URLs, filenames, and SHA-256 checksums.
Processed DDInter-derived data remains subject to CC BY-NC-SA 4.0; the source
manifest and this documentation provide attribution and identify transformations.

Acquire and verify the source, then reproduce all outputs:

```bash
python3 scripts/acquire_ddinter.py
python3 scripts/build_sprint3_dataset.py
python3 scripts/run_sprint3_eda.py
```

Primary outputs:

- `data/processed/sprint3/ddinter_severity_dataset.csv`
- `data/processed/sprint3/train.csv`
- `data/processed/sprint3/test.csv`
- `data/interim/sprint3/dataset_profile.json`
- `data/interim/sprint3/ddinter_hetionet_mapping.csv`
- `data/interim/sprint3/ddinter_conflicts.csv`
- `data/interim/sprint3/excluded_unknown_severity.csv`

One row is one canonical unordered DDInter drug pair. The target is
`ddi_severity` with Major, Moderate, and Minor classes only. Unknown rows remain
in the audit output and never enter supervised data. No no-interaction class or
synthetic negative pairs are created; absence from DDInter is not evidence of
safety.

## Feature Sources

Hetionet supplies optional graph features through strict exact normalized-name
mapping. Unmapped graph values remain missing for train-fitted preprocessing.
The official CSVs contain no verified molecular structure identifiers, so RDKit
descriptors are not generated. Neo4j and Hetionet remain the application graph
sources and are not replaced by DDInter.

The previous CtD classification output is retained only at
`data/processed/sprint3/legacy_ctd/ml_dataset.csv` as a historical graph-relation
prototype. It is not the primary Sprint 3 dataset.
