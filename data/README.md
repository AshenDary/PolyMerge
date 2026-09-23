# PolyMerge Data

## Primary Sprint 3 Source

The primary supervised dataset is DDInter 2.0. Its official eight category CSVs
are downloaded from `https://ddinter2.scbdd.com/download/` under CC BY-NC-SA
4.0. Raw files are intentionally ignored because redistribution is subject to
the source license. The tracked `data/original/ddinter/source_manifest.json`
records retrieval date, source URLs, filenames, and SHA-256 checksums.
Processed DDInter-derived data remains subject to CC BY-NC-SA 4.0; the source
manifest and this documentation provide attribution and identify transformations.
`data/original/pubchem/source_manifest.json` separately records the official
NCBI API, retrieval policy, query fields, cache, and conservative acceptance rule.

Acquire and verify the source, then reproduce all outputs:

```bash
python3 scripts/acquire_ddinter.py
python3 scripts/enrich_pubchem.py
python3 scripts/build_sprint3_dataset.py
python3 scripts/run_sprint3_eda.py
```

Primary outputs:

- `data/processed/sprint3/ddinter_severity_dataset.csv`
- `data/processed/sprint3/train.csv`
- `data/processed/sprint3/test.csv`
- `data/interim/sprint3/dataset_profile.json`
- `data/interim/sprint3/ddinter_hetionet_mapping.csv`
- `data/interim/sprint3/ddinter_pubchem_mapping.csv`
- `data/interim/sprint3/pubchem_query_cache.jsonl`
- `data/interim/sprint3/feature_coverage.csv`
- `data/interim/sprint3/ddinter_conflicts.csv`
- `data/interim/sprint3/excluded_unknown_severity.csv`

One row is one canonical unordered DDInter drug pair. The target is
`ddi_severity` with Major, Moderate, and Minor classes only. Unknown rows remain
in the audit output and never enter supervised data. No no-interaction class or
synthetic negative pairs are created; absence from DDInter is not evidence of
safety.

## Feature Sources

PubChem PUG REST supplies chemical identities and structures under a conservative
exact-title policy. The cached audit allows offline rebuilds. RDKit generates six
traditional descriptors from accepted structures. Hetionet supplies optional
graph features through strict exact normalized-name mapping. Unavailable graph
and molecular measurements remain missing and have explicit coverage indicators.
Neo4j and Hetionet remain the application graph sources and are not replaced.

The previous CtD classification output is retained only at
`data/processed/sprint3/legacy_ctd/ml_dataset.csv` as a historical graph-relation
prototype. It is not the primary Sprint 3 dataset.
