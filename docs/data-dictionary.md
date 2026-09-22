# Sprint 3 Data Dictionary

## Dataset

- File: `data/processed/sprint3/ml_dataset.csv`
- Unit of analysis: one row = one `Compound` x `Disease` pair
- Task: fallback represented CtD relationship classification
- Target: `ctd_label`
- Source: Hetionet v1.0 filtered PolyMerge fragment
- Permission/license status: derived from the repository's existing Hetionet fragment; no restricted DDI data is added.

## Columns

| Column | Type | Role | Source | Meaning | Values / Missing Behavior |
| --- | --- | --- | --- | --- | --- |
| `row_id` | string | metadata | generated | Stable `compound_id\|disease_id` row key | Required, unique |
| `compound_id` | string | metadata | graph node | Stable compound ID | Required |
| `compound_name` | string | metadata | graph node | Compound display name | Empty string if absent |
| `disease_id` | string | metadata | graph node | Stable disease ID | Required |
| `disease_name` | string | metadata | graph node | Disease display name | Empty string if absent |
| `label_source` | string | metadata | generated | Source/version used for label | Required |
| `label_semantics` | string | metadata | generated | Positive or sampled non-positive semantics | `represented_CtD_edge`, `sampled_no_represented_CtD_edge` |
| `compound_other_ctd_disease_count` | integer | feature | `CtD` edges | Count of other diseases treated by the compound, excluding the current row's pair | Median-imputed if missing |
| `compound_cpD_disease_count` | integer | feature | `CpD` edges | Count of diseases palliated by the compound | Median-imputed if missing |
| `compound_bound_gene_count` | integer | feature | `CbG` edges | Distinct bound genes for compound | Median-imputed if missing |
| `compound_upregulated_gene_count` | integer | feature | `CuG` edges | Distinct upregulated genes for compound | Median-imputed if missing |
| `compound_downregulated_gene_count` | integer | feature | `CdG` edges | Distinct downregulated genes for compound | Median-imputed if missing |
| `compound_side_effect_count` | integer | feature | `CcSE` edges | Distinct represented side effects for compound | Median-imputed if missing |
| `compound_pharmacologic_class_count` | integer | feature | `PCiC` edges | Distinct pharmacologic classes connected to compound | Median-imputed if missing |
| `compound_resemblance_neighbor_count` | integer | feature | `CrC` edges | Distinct chemical-resemblance neighbors; not a DDI label | Median-imputed if missing |
| `compound_graph_degree` | integer | feature | graph edges | Incident graph edge count for compound | Median-imputed if missing |
| `disease_other_ctd_compound_count` | integer | feature | `CtD` edges | Count of other compounds treating disease, excluding the current row's pair | Median-imputed if missing |
| `disease_cpD_compound_count` | integer | feature | `CpD` edges | Count of compounds palliating disease | Median-imputed if missing |
| `disease_graph_degree` | integer | feature | graph edges | Incident graph edge count for disease | Median-imputed if missing |
| `has_compound_palliates_disease_edge` | integer | feature | `CpD` edges | Whether the exact pair has represented `CpD` evidence | `0` or `1`; median-imputed if missing |
| `ctd_label` | integer | target | `CtD` edges + deterministic sampling | `1` if represented CtD edge exists; `0` if sampled pair lacks represented CtD in this fragment | Required; allowed values `0`, `1` |

## Labeling Strategy

Positive rows are all represented `CtD` pairs in the fragment. Non-positive rows
are sampled from Compound x Disease pairs without represented `CtD`, using
random state `42` and a 2:1 non-positive-to-positive ratio. These are dataset
representation labels, not clinical truth labels.
