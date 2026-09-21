# PolyMerge API

This document describes the current implemented API contract. It documents
implemented behavior only.

## Status Fields

Graph-backed candidate responses use:

- `dataStatus: "real_graph"`
- `mlStatus: "not_applied"`

Fallback responses use:

- `dataStatus: "demo"`
- `mlStatus: "demo"`
- `upstreamStatus: "fallback"`

No trained DDI, synergy, graph embedding, or GNN model is applied to current
graph-backed candidate responses.

## Backend Endpoints

### `GET /health`

Returns backend liveness.

Example response:

```json
{
  "status": "ok",
  "service": "polymerge-backend"
}
```

### `GET /health/dependencies`

Checks backend dependencies, currently the ML/Graph service.

Success response:

```json
{
  "status": "ok",
  "service": "polymerge-backend",
  "dependencies": {
    "mlEngine": "ok"
  }
}
```

If the ML/Graph service is unavailable, this endpoint returns HTTP 503 and reports `mlEngine: "unavailable"`.

### `GET /api/diseases`

Purpose: returns the disease catalog from the graph-backed ML service. Neo4j disease nodes are the source of truth.

Request body: none.

Example response:

```json
{
  "diseases": [
    {
      "id": "Disease::DOID:10763",
      "name": "hypertension",
      "kind": "Disease",
      "source": "Hetionet",
      "graphVersion": "Hetionet v1.0 filtered PolyMerge fragment"
    }
  ]
}
```

Disease IDs are stable Neo4j/Hetionet identifiers. Clients should send these IDs back to candidate search.

If the graph-backed catalog cannot be loaded, the backend returns HTTP 503:

```json
{
  "error": "Disease catalog unavailable",
  "detail": "..."
}
```

### `POST /api/combinations/search`

Purpose: validates selected diseases against the graph-backed disease catalog,
calls the ML/Graph service, applies hard safety checks, and returns graph-derived
research candidate-set results.

Request:

```json
{
  "diseases": ["Disease::DOID:10763", "Disease::DOID:9352"],
  "optimizationConfig": {
    "maxDrugCount": 5,
    "minimumCoverage": 0.8
  }
}
```

Validation:

- `diseases` must be a non-empty array of strings.
- At most 10 disease IDs/names are accepted.
- Disease values must exist in the graph-backed disease catalog.
- Unknown disease IDs return HTTP 400 and are not silently ignored.
- `optimizationConfig.maxDrugCount` must be an integer from 0 to 50.
- `optimizationConfig.minimumCoverage` must be a number from 0 to 1.

Graph-backed response properties:

- `queryId`: request/result identifier.
- `diseases`: resolved disease names.
- `candidates`: graph-derived candidate sets. Single-compound candidates are
  represented as one-drug candidate sets.
- `metadata.resolvedDiseases`: graph disease records.
- `metadata.candidateCoverage`: compound-to-disease coverage matrix.
- `metadata.candidateSetGeneration`: candidate-set generation limits and counts.
- `metadata.optimization`: greedy candidate-set optimization result.
- `metadata.dataStatus`: `real_graph`.
- `metadata.mlStatus`: `not_applied`.

## Disease x Drug Coverage Contract

The current coverage contract is:

```text
Drug / Compound
    |
    v
Covered requested target disease IDs
    |
    v
Represented Neo4j CtD graph relationship
    |
    v
Evidence + provenance
```

`metadata.candidateCoverage` is the canonical drug-level matrix for downstream
candidate-set generation. It maps stable compound IDs to the stable disease IDs
covered by represented `CtD` edges:

```json
{
  "metadata": {
    "candidateCoverage": {
      "Compound::DB00177": [
        "Disease::DOID:10763",
        "Disease::DOID:9352"
      ]
    }
  }
}
```

Coverage semantics:

- A row is a graph-derived compound/drug ID.
- A column is a resolved requested disease ID.
- A disease is covered only when Neo4j contains a represented
  `(Compound)-[:CtD]->(Disease)` relationship for that requested disease.
- Disease relationships outside the requested target set do not count toward
  target coverage.
- `coverage`, `coverageCount`, `targetDiseaseCount`, `treatedDiseaseIds`, and
  `uncoveredDiseaseIds` describe knowledge-graph treatment coverage, not
  clinical efficacy.

Candidate-set fields:

- `candidateSetId`: stable ID for this generated candidate set.
- `drugs`: stable compound IDs contained in the set.
- `drugNames`: display names for the compounds.
- `treatedDiseaseIds`: requested disease IDs covered by the set.
- `uncoveredDiseaseIds`: requested disease IDs not covered by the set.
- `comparison.drugs[].coveredDiseaseIds`: per-drug contribution to candidate-set
  coverage.

Candidate evidence may include:

- `CtD` treatment evidence.
- `CbG`, `CuG`, `CdG` gene evidence.
- `CcSE` side-effect evidence.

For every disease ID in `treatedDiseaseIds`, the candidate evidence should
include corresponding treatment evidence where:

- `relationship` is `CtD`.
- `targetId` is the covered disease ID.
- `source`, `graphVersion`, `metaedge`, `targetName`, and `evidenceType`
  preserve graph provenance.

`interactionRisk` and `synergyScore` are not applied for real graph-backed
candidates.

### `GET /api/combinations/:id`

Returns an in-memory candidate-search result from the current backend process.

### `GET /api/combinations/:id/explain`

Returns the current limited explainability payload for a stored in-memory result. Advanced explainability and graph visualization are future work.

### `GET /api/drugs/:id`

Returns current backend reference/demo drug metadata. This endpoint is not the
primary graph-backed candidate-search flow.

### `GET /api/drugs/:id/interactions`

Returns current backend reference/demo interaction metadata. This is not a trained DDI prediction endpoint.

## ML/Graph Service Endpoints

### `GET /health`

Returns ML/Graph service liveness.

### `GET /api/diseases`

Returns diseases from Neo4j through the graph service.

### `GET /api/drugs/{drug_id}`

Returns graph-backed drug metadata where the compound ID exists in Neo4j.

### `POST /predict/combination`

Accepts disease IDs/names and optional optimization config. Resolves graph
diseases, retrieves `CtD` compound candidates, attaches graph
evidence/provenance, generates candidate sets, runs deterministic safety checks,
ranks candidates, and runs the greedy candidate-set optimization baseline.

No trained predictive model is run for current graph-backed responses.
