# PolyMerge Team & Task Delegation

## Team

| Role                              | Name    | Core Domain                                              |
|------------------------------------|---------|-----------------------------------------------------------|
| Member A — ML Data Engineer        | Jared   | Neo4j, Cypher, RDKit, knowledge graph construction         |
| Member B — ML Backend Engineer     | Ranee   | Fastify, Prisma, PyTorch Geometric, API serving            |
| Member C — ML Research Engineer    | Pamela  | Set-cover search, GNNExplainer, frontend, clinical validation |

See SKILLS.md for the full tech-stack and task-routing breakdown per role.

## Current Sprint: Sprint 1 — The Skeleton

**Overall status:** in progress

### Jared (Member A)
- [ ] Hetionet fragment pulled, filtered, and loaded into Neo4j
- [ ] `neo4j_client.py` delivered and working
- [ ] Next: Restore Docker/Neo4j reachability, re-run live Cypher counts, and add `scripts/query_fragment_examples.py` showing a real drug-for-disease query.

### Ranee (Member B)
- [ ] `/api/combinations/search` extended with mocked drug-set response
- [x] Contraindication rule checks wired in and tested
- [ ] Fastify 5 migration fully verified (including the POST route, not just /health)
- [ ] Next: Add committed route coverage in `backend/tests/combinations-search.test.js` for Fastify 5 JSON body parsing, 200 response behavior, and contraindication blocking.

### Pamela (Member C)
- [ ] Minimal frontend built (Streamlit or React) hitting the backend route
- [ ] Next: Create `frontend/app.py` as a minimal Streamlit page that selects diseases, posts to `/api/combinations/search`, and displays the returned mock/stub combination table.

## Handoff Protocol

- A task is only "done" when it matches its Definition of Done in
  ROADMAP.md — not when the code merely runs once.
- If blocked, say so explicitly in the group chat with what's blocking you
  (don't sit on it) — most Sprint 1 blockers so far have been environment
  issues (Docker daemon, Git LFS), not actual code problems.
- Every PR needs at least one other member's review before merging to
  main, regardless of how small.

## Next Sync

Monday, September 14, 2026 at 10:00 AM PT, because Sprint 1 still needs live Neo4j verification, committed backend route tests, and the first frontend artifact.
