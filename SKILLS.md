# Team Domains, Tech Stack & Task Playbook

This file has two jobs: tell each teammate what to actually learn/use for
their role, and tell Codex (or any AI assistant working on this repo) how
to route a task to the right stack, files, and conventions without needing
the whole project re-explained every session.

## Member A — ML Data Engineer (Knowledge Graph & Representation)

**Core skills:** Neo4j + Cypher, RDKit, Python (pandas), Hetionet/DrugBank
data wrangling, traditional supervised feature engineering, scikit-learn.

**Owns:** `ml_engine/app/utils/neo4j_client.py`,
`scripts/filter_hetionet_fragment.py`, `scripts/load_fragment.py`,
`data/processed/`, `ml_engine/app/data/`, Sprint 3 data scripts.

**"Done" looks like:** any claim about graph state is backed by an actual
Cypher query result (`MATCH (n) RETURN count(n)`-style sanity checks), not
an assumption from the source CSVs.

**Known gotchas:**
- Hetionet has no direct Compound-Compound interaction edge — only `CrC`
  (chemical resemblance). DDI labels come from TWOSIDES, not Hetionet.
- Hetionet's 137 disease nodes don't include hyperlipidemia; the project
  uses coronary artery disease (`Disease::DOID:3393`) instead.
- `hetionet-v1.0-edges.sif.gz` is Git-LFS tracked — a plain
  `raw.githubusercontent.com` curl returns a pointer file, not data. Use
  the `media.githubusercontent.com/media/...` URL or `git lfs pull`.
- Docker Desktop's daemon can be down even when `docker-compose.yml` looks
  fine — confirm `docker info` succeeds before debugging a failed load.

## Member B — ML Backend Engineer (Predictive Modeling & Serving)

**Core skills:** scikit-learn model serving foundations, Fastify, Node.js,
Prisma, API security.

**Owns:** `backend/src/server.js`, `backend/src/rules/contraindications.js`,
`backend/prisma/schema.prisma`, `ml_engine/main.py`,
`ml_engine/app/data/preprocessing.py`, `ml_engine/app/services/combination_search.py`
(shared with Member C).

**"Done" looks like:** every response from `/api/combinations/search`
passes through `contraindications.js` before reaching a client, with no
code path that skips it; the Fastify↔FastAPI JSON contract stays stable
across model swaps.

**Known gotchas:**
- Never run model logic directly from Node; model/data logic belongs behind the
  `ml_engine` service boundary.
- Local MySQL migrations need the shadow database
  (`docker/mysql/init/01-shadow-database.sql`) — don't remove it or switch
  to the root user to "simplify" this.
- After any Fastify version bump, test an actual POST route with a body,
  not just `GET /health` — CORS and body parsing are what actually change
  between major versions.

## Member C — ML Research Engineer (Optimization & Explainability)

**Core skills:** greedy set-cover / integer programming, traditional model
evaluation, Streamlit or React, clinical-trial validation (reading trial data,
not running trials).

**Owns:** `ml_engine/app/services/combination_search.py` (shared with
Member B), `ml_engine/app/services/explainability.py`, `frontend/`,
Sprint evaluation reports.

**"Done" looks like:** every returned drug combination is traceable to a
specific explanation or a rule-based block reason; the UI visually
distinguishes "hard rule blocked this" from "model scored this as risky."

**Known gotchas:**
- Future model scores are inputs to research ranking only, never clinical
  decisions by themselves — see CONTEXT.md's design principles section before
  changing this logic.
- Validation against Polycap/PolyIran is a sanity check, not a proof —
  write up disagreements honestly rather than only reporting matches.

## How Codex Should Approach a Task, By Topic

Use this table to route work without re-deriving the project's structure
each session. If a task doesn't cleanly fit one row, say so explicitly
rather than guessing an owner.

| Task mentions...                                      | Owner            | Stack                           | Key files                                               | Watch out for |
|---------------------------------------------------------|------------------|----------------------------------|------------------------------------------------------------|---------------|
| Neo4j, Cypher, Hetionet, knowledge graph, nodes/edges    | Member A         | Python, `neo4j` driver, pandas  | `ml_engine/app/utils/neo4j_client.py`, `scripts/`           | Confirm Docker daemon is actually running before touching Neo4j; verify row counts after any load, don't assume |
| traditional ML, scikit-learn, preprocessing, train/test split | Members A+B      | pandas, scikit-learn             | `ml_engine/app/data/`, `scripts/build_sprint3_dataset.py`    | Fit preprocessing on train only; do not treat sampled non-positive labels as clinical truth |
| Fastify route, API endpoint, backend server              | Member B         | Fastify, Node                    | `backend/src/server.js`                                     | Must call `contraindications.js` before returning any drug set to a client |
| Prisma, MySQL, schema, migration                         | Member B         | Prisma CLI                       | `backend/prisma/schema.prisma`                               | Shadow DB is required for `migrate dev` locally — don't bypass it |
| set-cover, combinatorial search, optimization             | Member C (w/ B)  | Python                           | `ml_engine/app/services/combination_search.py`               | Operates on documented evidence/model fields, never clinical assumptions |
| explainability, "why" trace                               | Member C         | Python                           | `ml_engine/app/services/explainability.py`                   | Every prediction needs a trace — this is a hard requirement, not polish |
| frontend, UI, Streamlit, React, dashboard                 | Member C         | Streamlit or React               | `frontend/`                                                 | Must visually separate rule-based blocks from model-predicted risk |
| Docker, docker-compose, local environment                 | whoever's blocked | n/a                              | `docker-compose.yml`, `Makefile`                             | Check `docker info` succeeds (daemon up), not just that the compose file looks right |
| Tests                                                     | task owner       | `node --test` / `pytest`         | `backend/tests/`, `ml_engine/tests/`                          | New logic needs a matching test in the same change, not a follow-up |

## General Operating Rules for Codex on This Repo

- Read `CONTEXT.md`, `ROADMAP.md`, and this file before starting any task —
  don't rely on general knowledge of polypills, Hetionet, or Fastify; use
  what's specified here, since it reflects real decisions already made.
- Report exact numbers (row counts, test pass counts, response bodies),
  never a vague summary like "everything works."
- Don't start/stop Docker containers unless a task explicitly asks for it
  or the daemon itself is confirmed down — check `docker info` first.
- If a task touches a file outside its stated scope, say so explicitly in
  the report rather than silently including it.
