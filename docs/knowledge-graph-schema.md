# PolyMerge Knowledge Graph Schema

This document describes the currently loaded Neo4j development graph inspected on 2026-09-16.

## Data Source

- Source: Hetionet
- Local graph version: Hetionet v1.0 filtered PolyMerge fragment
- Loader input:
  - `data/processed/fragment_nodes.csv`
  - `data/processed/fragment_edges.csv`
- Loader script: `scripts/load_fragment.py`

The fragment is a research knowledge graph for candidate discovery. It is not a DDI-label dataset and does not contain clinical safety guarantees.

## Entity Labels

| Label | Count | Properties |
| --- | ---: | --- |
| Compound | 299 | `id`, `name`, `kind` |
| Disease | 25 | `id`, `name`, `kind` |
| Gene | 1411 | `id`, `name`, `kind` |
| Pharmacologic Class | 37 | `id`, `name`, `kind` |
| Side Effect | 1643 | `id`, `name`, `kind` |

Example disease identifiers:

| Disease | ID |
| --- | --- |
| hypertension | `Disease::DOID:10763` |
| type 2 diabetes mellitus | `Disease::DOID:9352` |
| coronary artery disease | `Disease::DOID:3393` |

Example compound identifiers:

| Compound | ID |
| --- | --- |
| Amlodipine | `Compound::DB00381` |
| Valsartan | `Compound::DB00177` |
| Metformin | `Compound::DB00331` |

## Relationship Types

| Type | Count | Current PolyMerge Use |
| --- | ---: | --- |
| `CtD` | 142 | Compound treats Disease; primary disease to drug retrieval edge |
| `CpD` | 20 | Compound palliates Disease; available as disease evidence, not used as treatment coverage yet |
| `CdG` | 1484 | Compound downregulates Gene; target/evidence context |
| `CuG` | 977 | Compound upregulates Gene; target/evidence context |
| `CbG` | 1010 | Compound binds Gene; target/evidence context |
| `CcSE` | 11987 | Compound causes Side Effect; side-effect evidence context |
| `CrC` | 519 | Compound resembles Compound; not a DDI label |
| `PCiC` | 91 | Pharmacologic Class includes Compound; classification context |

All relationships currently expose a `metaedge` property matching the relationship type.

## Implemented Graph Queries

The ML engine graph service uses parameterized Cypher through `Neo4jClient.query()`.

Disease search:

```cypher
MATCH (d:Disease)
WITH d,
     toLower(d.id) AS id,
     toLower(d.name) AS name,
     toLower($searchQuery) AS rawQuery,
     $normalizedQuery AS normalizedQuery
WHERE normalizedQuery = ""
   OR id = rawQuery
   OR name = rawQuery
   OR name = normalizedQuery
   OR name CONTAINS normalizedQuery
RETURN d.id AS id, d.name AS name, d.kind AS kind
ORDER BY d.name
LIMIT $limit
```

Disease to drug retrieval:

```cypher
MATCH (compound:Compound)-[relationship:CtD]->(disease:Disease)
WHERE disease.id IN $diseaseIds
RETURN compound.id AS drug_id,
       compound.name AS drug_name,
       collect(DISTINCT disease.id) AS disease_ids,
       collect(DISTINCT disease.name) AS disease_names
```

Drug target evidence:

```cypher
MATCH (compound:Compound {id: $drugId})-[relationship]->(gene:Gene)
WHERE type(relationship) IN $relationshipTypes
RETURN gene.id AS id,
       gene.name AS name,
       type(relationship) AS relationship_type,
       relationship.metaedge AS metaedge
LIMIT $limit
```

Drug side-effect evidence:

```cypher
MATCH (compound:Compound {id: $drugId})-[relationship:CcSE]->(sideEffect:`Side Effect`)
RETURN sideEffect.id AS id,
       sideEffect.name AS name,
       type(relationship) AS relationship_type,
       relationship.metaedge AS metaedge
LIMIT $limit
```

## Current Retrieval Semantics

- Treatment coverage is computed only from represented `CtD` edges.
- Coverage means knowledge-graph treatment coverage for the selected disease set.
- Predictive ML, DDI, synergy, and clinical validation are not applied in this phase.
- Side effects and gene relationships are returned as evidence/provenance context, not as safety predictions.

## Baseline Research Optimization

The ML engine represents graph-derived candidate coverage as a matrix:

- Rows are candidate compound IDs.
- Columns are resolved disease IDs.
- A populated cell means the graph contains a represented `CtD` treatment relationship.

The baseline optimizer greedily selects the candidate with the greatest uncovered
disease count, up to `maxDrugCount`, and stops when `minimumCoverage` is reached.
Its result preserves `coverageMatrix`, `coveredDiseaseIds`, `uncoveredDiseaseIds`,
`selectedDrugs`, and `selectedDrugCount`. These values describe knowledge-graph
treatment coverage for research candidate discovery, not clinical efficacy,
prescribing suitability, or validated safety.
