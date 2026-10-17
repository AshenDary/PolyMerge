# Neo4j Index Review Plan (Not Applied)

Local read-only EXPLAIN/PROFILE found label scans for Disease.id and Compound.id;
SHOW INDEXES returned only two token lookup indexes and no constraints.
Graph retrieval was about 0.1 seconds, not the dominant measured bottleneck.

Before any shared-environment migration:

1. Confirm graph owner approval, backup/rollback procedure and Neo4j version.
2. Check missing, duplicate and differently typed IDs on Disease and Compound.
3. If uniqueness is a reviewed data invariant, propose named uniqueness
   constraints on each label's id property; otherwise propose range indexes.
   Do not create both a redundant range index and uniqueness-backed index.
4. Review exact version-compatible DDL separately. Schedule index population
   under an agreed resource budget; do not alter graph entities or relationships.
5. Wait for ONLINE state, repeat parameterized query plans and compare complete
   graph paths/provenance, counts and canonical responses against the baseline.
6. Roll back only the newly approved named schema objects if validation fails.

No DDL or graph mutation was executed for this task. Gene and side-effect
queries currently run once each per compound (not per candidate). Bounded batch
retrieval and driver lifecycle improvements deserve a separate equivalence-tested
change if larger graphs make this cost significant.
