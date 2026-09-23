# Jared - Sprint 3

## Tasks

- [x] Acquire and checksum official DDInter 2.0 category CSVs
- [x] Validate real schema, labels, malformed rows, duplicates, and conflicts
- [x] Canonicalize unordered pairs and exclude Unknown from supervised data
- [x] Map DDInter drugs to Hetionet with explicit exact-name statuses
- [x] Generate deterministic per-drug and pairwise graph features
- [x] Cache conservative PubChem identity/structure mappings
- [x] Generate deterministic RDKit descriptors and symmetric pair summaries
- [x] Audit feature coverage, missing semantics, and cold-start feasibility
- [x] Create deterministic train/test split
- [x] Document data dictionary, EDA findings, preprocessing, and handoff

## Definition of Done

- [x] Pipeline is reproducible with acquisition, build, and EDA scripts
- [x] Feature and target semantics are documented
- [x] Preprocessing does not introduce clinical claims
