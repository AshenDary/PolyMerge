# PolyMerge Sprint 1 API

This document describes the current Sprint 1 API contract. It documents implemented behavior only.

## Status Fields

Graph-backed candidate responses use:

- `dataStatus: "real_graph"`
- `mlStatus: "not_applied"`

Fallback responses use:

- `dataStatus: "demo"`
- `mlStatus: "demo"`
- `upstreamStatus: "fallback"`

No trained DDI, synergy, graph embedding, or GNN model is applied in Sprint 1.

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

Purpose: validates selected diseases against the graph-backed disease catalog, calls the ML/Graph service, applies backend hard safety checks, and returns research candidate results.

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
- `candidates`: graph-derived individual compound candidates.
- `metadata.resolvedDiseases`: graph disease records.
- `metadata.candidateCoverage`: compound-to-disease coverage matrix.
- `metadata.optimization`: greedy set-cover result.
- `metadata.dataStatus`: `real_graph`.
- `metadata.mlStatus`: `not_applied`.

Candidate evidence may include:

- `CtD` treatment evidence.
- `CbG`, `CuG`, `CdG` gene evidence.
- `CcSE` side-effect evidence.

`interactionRisk` and `synergyScore` are not applied for real graph-backed Sprint 1 candidates.

### `GET /api/combinations/:id`

Returns an in-memory candidate-search result from the current backend process.

### `GET /api/combinations/:id/explain`

Returns the current limited explainability payload for a stored in-memory result. Advanced explainability and graph visualization are future work.

### `GET /api/drugs/:id`

Returns current backend reference/demo drug metadata. This endpoint is not the primary graph-backed Sprint 1 candidate flow.

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

Accepts disease IDs/names and optional optimization config. Resolves graph diseases, retrieves `CtD` compound candidates, attaches graph evidence/provenance, runs deterministic safety checks, ranks candidates, and runs the greedy set-cover baseline.

No trained predictive model is run in Sprint 1.
