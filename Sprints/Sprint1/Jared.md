# Jared - Sprint 1

Role: Knowledge Graph / Biomedical Data Engineer

## Tasks

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

## Notes

- `CrC` is compound resemblance and must not be treated as a DDI label.
- Coverage means knowledge-graph treatment coverage, not clinical efficacy.
