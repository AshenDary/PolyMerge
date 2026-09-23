# Sprint 3 DDInter Feature Data Dictionary

## Contract

- Unit: one canonical unordered DDInter drug pair.
- Target: `ddi_severity` from DDInter 2.0; Major, Moderate, or Minor.
- Identity/structure source: PubChem PUG REST, accepted only on a unique exact
  normalized title match and successful RDKit parsing.
- Graph source: the checked-in Hetionet fragment through explicit mapping.
- Missing measurements are `NaN`; availability indicators distinguish missing
  coverage from a known zero.

## Metadata and Target

| Columns | Meaning | Model use |
| --- | --- | --- |
| `pair_id` | Canonical DDInter-ID pair key | Excluded |
| `drug_a_ddinter_id`, `drug_b_ddinter_id` | Canonically ordered source IDs | Excluded |
| `drug_a_name`, `drug_b_name` | DDInter names | Excluded |
| `source_severity` | Original DDInter label retained for audit | Excluded |
| `source_file`, `atc_category`, `source_dataset`, `dataset_version` | Label provenance | Excluded |
| `drug_a_hetionet_id`, `drug_b_hetionet_id` | Accepted mapped graph IDs | Excluded |
| `drug_a_mapping_status`, `drug_b_mapping_status`, `pair_mapping_coverage` | Graph mapping audit | Excluded |
| `drug_a_pubchem_cid`, `drug_b_pubchem_cid` | Accepted PubChem CIDs | Excluded |
| `drug_a_pubchem_status`, `drug_b_pubchem_status`, `pair_structure_coverage` | Structure mapping audit | Excluded |
| `ddi_severity` | Major, Moderate, Minor | Target only |

## Availability Features

| Feature | Type | Meaning |
| --- | --- | --- |
| `hetionet_available_count` | integer | Number of pair members mapped to Hetionet: 0, 1, or 2 |
| `both_hetionet_available` | binary | Both pair members have graph mappings |
| `structure_available_count` | integer | Number of pair members with accepted PubChem structures: 0, 1, or 2 |
| `both_structures_available` | binary | Both pair members have valid structures |

These four features are never missing. They expose coverage without leaking IDs.

## Symmetric Graph Scalar Features

For each base below, two columns exist:
`graph_<base>_mean` and `graph_<base>_abs_difference`. Both require two graph
mappings; otherwise they are `NaN` and median-imputed using training data only.

| Base | Type | Hetionet provenance |
| --- | --- | --- |
| `ctd_disease_count` | numeric | Distinct `CtD` diseases |
| `cpd_disease_count` | numeric | Distinct `CpD` diseases |
| `bound_gene_count` | numeric | Distinct `CbG` genes |
| `upregulated_gene_count` | numeric | Distinct `CuG` genes |
| `downregulated_gene_count` | numeric | Distinct `CdG` genes |
| `side_effect_count` | numeric | Distinct `CcSE` side effects |
| `pharmacologic_class_count` | numeric | Distinct `PCiC` classes |
| `resemblance_neighbor_count` | numeric | Distinct `CrC` neighbors; resemblance only, never DDI truth |
| `graph_degree` | numeric | Incident represented graph edges |

## Symmetric Graph Set Features

Each set family has `<family>_intersection_count`, `<family>_union_count`, and
`<family>_jaccard`. They require both mappings; known empty sets produce zero,
while mapping failure produces `NaN`.

| Family | Hetionet provenance |
| --- | --- |
| `gene` | Union of `CbG`, `CuG`, and `CdG` entities |
| `bound_gene` | `CbG` entities |
| `upregulated_gene` | `CuG` entities |
| `downregulated_gene` | `CdG` entities |
| `side_effect` | `CcSE` entities |
| `treated_disease` | Union of `CtD` and `CpD` entities |
| `pharmacologic_class` | `PCiC` entities |

## Symmetric Molecular Features

PubChem `SMILES` is parsed by RDKit. For each descriptor below, two columns
exist: `<descriptor>_mean` and `<descriptor>_abs_difference`. Both require two
accepted structures; otherwise they are `NaN` and median-imputed from training.

| Descriptor | Type | RDKit calculation |
| --- | --- | --- |
| `molecular_weight` | float | `Descriptors.MolWt` |
| `logp` | float | `Crippen.MolLogP` |
| `tpsa` | float | `CalcTPSA` |
| `hbd` | integer | Hydrogen-bond donors |
| `hba` | integer | Hydrogen-bond acceptors |
| `rotatable_bonds` | integer | Rotatable bonds |

The final matrix has 55 features: 41 graph/availability features and 14
molecular/availability features. Exact per-column coverage and distribution
statistics are in `data/interim/sprint3/feature_coverage.csv`.
