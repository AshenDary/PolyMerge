# Sprint 1 GitHub Issues

These issue bodies are ready to copy into GitHub, or to create with `scripts/create_sprint1_issues.sh` after authenticating the GitHub CLI.

## Issue 1: Sprint 1 — Foundation & Knowledge Graph

Labels: `sprint-1`, `documentation`, `integration`, `priority-high`

Assignee: Team

### Goal

Move PolyMerge from demo/placeholder data toward a real biomedical knowledge-graph-backed foundation.

### Sprint Objectives

- [ ] Establish reproducible development environments
- [ ] Connect PolyMerge to Neo4j
- [ ] Implement real Hetionet-based disease/drug retrieval
- [ ] Establish evidence and provenance
- [ ] Connect graph retrieval to candidate generation
- [ ] Establish backend/ML integration
- [ ] Establish the first optimization pipeline
- [ ] Add automated tests
- [ ] Document the current architecture and graph schema

### Likely Affected Areas

- `README.md`
- `CONTEXT.md`
- `ROADMAP.md`
- `docker-compose.yml`
- `.env.example`
- `backend/`
- `ml_engine/`
- `docs/`

### Dependencies

- Docker infrastructure must run Neo4j and MySQL locally.
- Sprint task issues should be completed through focused feature branches and PRs.

### Definition of Done

- [ ] All assigned Sprint 1 issues are completed or explicitly carried forward
- [ ] Tests pass
- [ ] Changes are reviewed through Pull Requests
- [ ] Documentation is updated
- [ ] Main development branch contains the completed Sprint 1 work
- [ ] Team can reproduce the environment locally

## Issue 2: Jared: Implement Real Neo4j Knowledge Graph Foundation

Labels: `sprint-1`, `knowledge-graph`, `integration`, `priority-high`, `testing`, `documentation`

Assignee: Jared

### Goal

Replace demo graph access with a real Neo4j-backed biomedical data foundation using the current Hetionet fragment.

### Tasks

- [ ] Verify the Hetionet graph schema
- [ ] Implement Neo4j connection using environment variables
- [ ] Use parameterized Cypher queries
- [ ] Implement disease search
- [ ] Implement disease to compound retrieval using `CtD`
- [ ] Implement multi-disease treatment coverage
- [ ] Retrieve compound-gene evidence using `CbG`, `CuG`, and `CdG`
- [ ] Retrieve side-effect evidence using `CcSE`
- [ ] Preserve Hetionet provenance
- [ ] Return graph-backed candidate information
- [ ] Clearly distinguish graph data from future ML predictions
- [ ] Add unit/integration tests
- [ ] Document the graph schema

### Likely Affected Areas

- `ml_engine/app/utils/neo4j_client.py`
- `ml_engine/app/services/graph_service.py`
- `ml_engine/app/services/knowledge_graph.py`
- `ml_engine/app/services/candidate_generator.py`
- `ml_engine/main.py`
- `ml_engine/tests/`
- `docs/knowledge-graph-schema.md`

### Dependencies

- Neo4j must contain the current Hetionet fragment.
- `.env` must define `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.

### Definition of Done

- [ ] Neo4j connection works
- [ ] Disease retrieval uses Neo4j
- [ ] Disease to drug retrieval uses real graph relationships
- [ ] Candidate generation no longer depends on hard-coded demo drugs
- [ ] Evidence/provenance is returned
- [ ] Tests pass
- [ ] Documentation is committed
- [ ] No DDI risk is derived from `CrC`

### Notes

`CrC` represents compound resemblance and must not be treated as a drug-drug interaction label.

## Issue 3: Jared: Replace Hard-Coded Disease Catalog

Labels: `sprint-1`, `knowledge-graph`, `backend`, `priority-high`, `integration`, `testing`

Assignee: Jared

### Goal

Replace the hard-coded backend disease catalog with the real Neo4j-backed disease catalog exposed through the ML graph service.

### Tasks

- [ ] Replace the hard-coded `/api/diseases` catalog
- [ ] Retrieve available diseases from Neo4j
- [ ] Return stable disease identifiers
- [ ] Return disease names
- [ ] Validate that selected disease IDs exist in Neo4j
- [ ] Preserve clear graph provenance in API responses where applicable
- [ ] Add backend and ML integration tests
- [ ] Update API documentation

### Likely Affected Areas

- `backend/src/server.js`
- `ml_engine/main.py`
- `ml_engine/app/services/graph_service.py`
- `backend/tests/`
- `ml_engine/tests/`
- `README.md`

### Dependencies

- Issue 2 should provide stable graph-backed disease search/retrieval.
- Backend-to-ML communication must be available.

### Definition of Done

- [ ] The frontend can retrieve the available disease catalog from the real Neo4j-backed service
- [ ] Unknown disease IDs return a clear not-found or validation error
- [ ] Tests pass
- [ ] API documentation describes the disease response shape

## Issue 4: Ranee: Backend and ML Engine Integration

Labels: `sprint-1`, `backend`, `ml`, `integration`, `testing`, `priority-medium`

Assignee: Ranee

### Goal

Make Fastify-to-FastAPI communication reliable and ensure graph-backed responses preserve data provenance and ML status fields.

### Tasks

- [ ] Verify Fastify to FastAPI communication
- [ ] Verify request/response schemas
- [ ] Add input validation
- [ ] Verify error handling
- [ ] Verify health endpoints
- [ ] Verify candidate search endpoint
- [ ] Preserve `dataStatus`
- [ ] Preserve `mlStatus`
- [ ] Ensure ML fields are not presented as real predictions when ML is not implemented
- [ ] Add integration tests

### Likely Affected Areas

- `backend/src/server.js`
- `backend/tests/`
- `ml_engine/main.py`
- `README.md`

### Dependencies

- Issue 2 should provide graph-backed ML service responses.
- Local development infrastructure must run Neo4j, MySQL, backend, and ML engine.

### Definition of Done

- [ ] Fastify can reliably communicate with the ML engine
- [ ] Backend returns structured candidate responses
- [ ] Error cases are tested
- [ ] Responses distinguish deterministic KG data from future ML predictions

## Issue 5: Pamela: Set-Cover Optimization Foundation

Labels: `sprint-1`, `optimization`, `knowledge-graph`, `testing`, `priority-medium`

Assignee: Pamela

### Goal

Implement a baseline optimizer that consumes real graph-derived candidate coverage and produces research candidate selections.

### Tasks

- [ ] Define the candidate coverage matrix
- [ ] Accept graph-derived candidate coverage
- [ ] Implement the first greedy/set-cover baseline
- [ ] Support multi-disease coverage
- [ ] Track selected drug count
- [ ] Preserve coverage information
- [ ] Prepare configurable optimization parameters
- [ ] Add unit tests

### Likely Affected Areas

- `ml_engine/app/services/set_cover_optimizer.py`
- `ml_engine/app/services/candidate_generator.py`
- `ml_engine/app/services/candidate_ranker.py`
- `ml_engine/tests/`
- `docs/`

### Dependencies

- Issue 2 should provide candidate coverage data derived from Neo4j treatment relationships.

### Definition of Done

- [ ] Optimizer can receive real graph-derived candidate coverage
- [ ] Optimizer produces a research candidate set
- [ ] Coverage is not described as clinical efficacy
- [ ] Tests pass

## Issue 6: Team: Reproducible Development Environment

Labels: `sprint-1`, `documentation`, `integration`, `testing`, `priority-medium`

Assignee: Team

### Goal

Ensure any teammate can clone PolyMerge and run the local development baseline with Neo4j, MySQL, backend, ML engine, and frontend.

### Tasks

- [ ] Verify Node.js environment
- [ ] Verify Python environment
- [ ] Verify Neo4j
- [ ] Verify MySQL
- [ ] Verify Prisma
- [ ] Verify frontend
- [ ] Verify backend
- [ ] Verify ML engine
- [ ] Update `.env.example`
- [ ] Document setup instructions
- [ ] Ensure secrets are not committed

### Likely Affected Areas

- `README.md`
- `.env.example`
- `docker-compose.yml`
- `backend/package.json`
- `backend/prisma/`
- `ml_engine/requirements.txt`
- `frontend/`

### Dependencies

- Docker Desktop or Docker Engine must be available.
- Local `.env` must remain uncommitted.

### Definition of Done

- [ ] A teammate can clone the repository and follow the README to run the project locally
- [ ] Backend `/health` works
- [ ] ML engine `/health` works
- [ ] Neo4j Browser is accessible
- [ ] MySQL is healthy
- [ ] Tests pass
- [ ] No secrets are committed
