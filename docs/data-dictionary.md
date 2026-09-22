# Sprint 3 DDInter Data Dictionary

## Dataset

- File: `data/processed/sprint3/ddinter_severity_dataset.csv`
- Unit: one canonical unordered DDInter drug pair
- Target source: DDInter 2.0
- Feature source: Hetionet v1.0 filtered fragment
- Target: `ddi_severity` (Major, Moderate, Minor)
- Unknown policy: excluded from supervised data and retained in
  `data/interim/sprint3/excluded_unknown_severity.csv`

## Metadata and Target

| Column | Role | Source / meaning | Missing behavior |
| --- | --- | --- | --- |
| `pair_id` | key | Canonical `lower_DDInter_ID\|higher_DDInter_ID` | Required and unique |
| `drug_a_ddinter_id`, `drug_b_ddinter_id` | metadata | Canonically ordered DDInter IDs | Required |
| `drug_a_name`, `drug_b_name` | metadata | DDInter display names | Required |
| `source_severity` | audit metadata | Original DDInter `Level` | Required; excluded from X |
| `source_file` | provenance | Semicolon-separated official files containing the pair | Required |
| `atc_category` | provenance | Semicolon-separated download category codes | Required |
| `source_dataset`, `dataset_version` | provenance | DDInter / DDInter 2.0 | Required |
| `drug_a_hetionet_id`, `drug_b_hetionet_id` | mapping metadata | Accepted exact-name Hetionet compound IDs | Missing when unresolved |
| `drug_a_mapping_status`, `drug_b_mapping_status` | mapping metadata | `exact_name`, `ambiguous`, or `unmapped` | Required |
| `pair_mapping_coverage` | mapping metadata | both, one, or neither drug mapped | Required |
| `ddi_severity` | target | Curated DDInter severity | Major, Moderate, Minor only |

All metadata columns are excluded from model inputs.

## Per-Drug Graph Features

Each feature appears with both `drug_a_` and `drug_b_` prefixes. Values come
from represented Hetionet edges for an exactly mapped compound. Missing values
mean graph coverage is unavailable and are median-imputed from training data.

| Suffix | Type | Hetionet source | Meaning |
| --- | --- | --- | --- |
| `ctd_disease_count` | integer | `CtD` | Distinct treated diseases |
| `cpd_disease_count` | integer | `CpD` | Distinct palliated diseases |
| `bound_gene_count` | integer | `CbG` | Distinct bound genes |
| `upregulated_gene_count` | integer | `CuG` | Distinct upregulated genes |
| `downregulated_gene_count` | integer | `CdG` | Distinct downregulated genes |
| `side_effect_count` | integer | `CcSE` | Distinct represented side effects |
| `pharmacologic_class_count` | integer | `PCiC` | Distinct pharmacologic classes |
| `resemblance_neighbor_count` | integer | `CrC` | Chemical-resemblance neighbors; never DDI truth |
| `graph_degree` | integer | all fragment edges | Incident represented edge count |

## Pairwise Graph Features

Pairwise values require both drugs to map. Otherwise they are missing and are
median-imputed from training data.

| Feature | Type | Source / transformation | Meaning |
| --- | --- | --- | --- |
| `shared_gene_count` | integer | Union of `CbG`, `CuG`, `CdG` sets | Shared represented genes |
| `shared_bound_gene_count` | integer | Intersection of `CbG` sets | Shared bound genes |
| `shared_upregulated_gene_count` | integer | Intersection of `CuG` sets | Shared upregulated genes |
| `shared_downregulated_gene_count` | integer | Intersection of `CdG` sets | Shared downregulated genes |
| `shared_side_effect_count` | integer | Intersection of `CcSE` sets | Shared side effects |
| `shared_treated_disease_count` | integer | Intersection of combined `CtD`/`CpD` sets | Shared disease context |
| `shared_pharmacologic_class_count` | integer | Intersection of `PCiC` sets | Shared pharmacologic classes |
| `gene_jaccard` | float | Gene intersection / union | Gene-set similarity, 0 when both sets empty |
| `side_effect_jaccard` | float | Side-effect intersection / union | Side-effect-set similarity |
| `disease_jaccard` | float | Disease intersection / union | Disease-context similarity |
| `pharmacologic_class_jaccard` | float | Class intersection / union | Pharmacologic-class similarity |

## Molecular Features

RDKit descriptor coverage is 0%. The official interaction CSVs do not provide
verified SMILES, InChI, or InChIKey, so no structures or descriptors are
fabricated. RDKit may be added later only through a documented, legitimate,
verified identifier-to-structure source.
