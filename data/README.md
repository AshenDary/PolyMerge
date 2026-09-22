# PolyMerge Data

## Current Sources

PolyMerge currently uses the checked-in Hetionet v1.0 filtered fragment:

- `data/raw/hetionet-v1.0-nodes.tsv`
- `data/raw/hetionet-v1.0-edges.sif.gz`
- `data/processed/fragment_nodes.csv`
- `data/processed/fragment_edges.csv`

The fragment is a research knowledge graph. It is not a clinical reference, not
a DDI label dataset, and not evidence of safety.

## Sprint 3 Supervised Dataset

No legitimate DDI label dataset is present in this repository, so Sprint 3 does
not fabricate a DDI target. The implemented fallback task is represented
drug-disease CtD relationship classification.

Generated outputs:

- `data/processed/sprint3/ml_dataset.csv`
- `data/processed/sprint3/train.csv`
- `data/processed/sprint3/test.csv`
- `data/interim/sprint3/dataset_profile.json`

Recreate them with:

```bash
python3 scripts/build_sprint3_dataset.py
python3 scripts/run_sprint3_eda.py
```

The positive label means the fragment contains a represented
`Compound-[:CtD]->Disease` edge. The negative label means a deterministically
sampled Compound x Disease pair has no represented CtD edge in this fragment.
It does not mean the relationship is clinically false or safe.
