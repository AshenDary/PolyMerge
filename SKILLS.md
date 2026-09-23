# Team Domains, Tech Stack & Task Playbook

This file has two jobs: tell each teammate what to actually learn/use for
their role, and tell Codex (or any AI assistant working on this repo) how
to route a task to the right stack, files, and conventions without needing
the whole project re-explained every session.

## Member A - ML Data Engineer (Knowledge Graph & Feature Engineering)

**Core skills:** Neo4j + Cypher, PubChem PUG REST, RDKit, Python (pandas),
Hetionet and DDInter data wrangling, data dictionaries, leakage-safe feature
engineering, and reproducible train/test dataset preparation.

**Owns:** `ml_engine/app/utils/neo4j_client.py`,
`scripts/filter_hetionet_fragment.py`, `scripts/load_fragment.py`,
`data/original/ddinter/source_manifest.json`, `data/processed/`,
`ml_engine/app/data/`, and the Sprint 3 DDInter acquisition, build, enrichment,
and EDA scripts.

**"Done" looks like:** any claim about graph state is backed by an actual
Cypher query result (`MATCH (n) RETURN count(n)`-style sanity checks), not
an assumption from the source CSVs. Any supervised dataset has a documented
target variable, negative-label strategy, source/license, and data dictionary.

**Known gotchas:**
- Hetionet has no direct Compound-Compound interaction edge; `CrC` is chemical
  resemblance, not DDI evidence.
- Absence of a known DDI label is not proof that a drug pair is safe.
- Hetionet's 137 disease nodes don't include hyperlipidemia; the project uses
  coronary artery disease (`Disease::DOID:3393`) instead.
- `hetionet-v1.0-edges.sif.gz` is Git-LFS tracked. A plain
  `raw.githubusercontent.com` curl returns a pointer file, not data. Use the
  `media.githubusercontent.com/media/...` URL or `git lfs pull`.
- Docker Desktop's daemon can be down even when `docker-compose.yml` looks
  fine. Confirm `docker info` succeeds before debugging a failed load.

## Member B - ML Backend Engineer (Traditional Modeling & Serving)

**Core skills:** scikit-learn, pandas, Fastify, Node.js, Prisma, API security,
model metadata, reproducible model-serving contracts, and unavailable-model
handling.

**Owns:** `backend/src/server.js`, `backend/src/rules/contraindications.js`,
`backend/prisma/schema.prisma`, `ml_engine/main.py`, future traditional model
training/serving modules in `ml_engine/`, and
`ml_engine/app/services/combination_search.py` (shared with Member C).

**"Done" looks like:** every response from `/api/combinations/search` and
candidate-set endpoints passes through deterministic safety checks before
reaching a client; the Fastify-to-FastAPI JSON contract stays stable across
model swaps; current graph-backed responses keep `mlStatus: "not_applied"`
until a trained traditional model is integrated.

**Known gotchas:**
- Do not add neural-network, deep-learning, graph-neural-network, transformer,
  pretrained foundation-model, or AutoML-generated solutions for the academic
  ML model.
- The planned comparison algorithms are `LogisticRegression`,
  `RandomForestClassifier`, and `HistGradientBoostingClassifier`. They must use
  the same split, preprocessing, cross-validation strategy, and macro F1
  primary metric. `GradientBoostingClassifier` is only a course fallback.
- Local MySQL migrations need the shadow database
  (`docker/mysql/init/01-shadow-database.sql`). Do not remove it or switch to
  the root user to "simplify" this.
- After any Fastify version bump, test an actual POST route with a body, not
  just `GET /health`; CORS and body parsing are what actually change between
  major versions.

## Member C - ML Research Engineer (Optimization, Evaluation & Deployment)

**Core skills:** greedy set-cover / integer programming, model comparison,
cross-validation reporting, Streamlit or React, research evaluation, and
clinical-trial validation context (reading trial data, not running trials).

**Owns:** `ml_engine/app/services/combination_search.py` (shared with Member B),
future evaluation and reporting docs, `frontend/` or Streamlit app, and
`docs/validation-report.md`.

**"Done" looks like:** every returned drug combination is traceable to known
graph evidence, deterministic rule outcomes, and any future traditional model
prediction metadata; the UI visually distinguishes "hard rule blocked this"
from "model scored this as risky."

**Known gotchas:**
- Model scores are inputs to ranking/selection support, never final clinical
  answers by themselves. See `CONTEXT.md` before changing this logic.
- Validation against Polycap/PolyIran is a sanity check, not a proof. Write up
  disagreements honestly rather than only reporting matches.
- Streamlit is the preferred academic deployment unless the instructor approves
  another framework.

## How Codex Should Approach a Task, By Topic

Use this table to route work without re-deriving the project's structure each
session. If a task doesn't cleanly fit one row, say so explicitly rather than
guessing an owner.

| Task mentions... | Owner | Stack | Key files | Watch out for |
| --- | --- | --- | --- | --- |
| Neo4j, Cypher, Hetionet, knowledge graph, nodes/edges | Member A | Python, `neo4j` driver, pandas | `ml_engine/app/utils/neo4j_client.py`, `scripts/` | Confirm Docker daemon is actually running before touching Neo4j; verify row counts after any load |
| DDInter dataset, PubChem, RDKit, EDA, feature engineering, data dictionary | Member A | pandas, RDKit, scikit-learn | `ml_engine/app/data/`, `scripts/`, `data/` | Preserve the finalized target and explicit missingness semantics |
| Logistic Regression, Random Forest, Histogram Gradient Boosting | Members A+B | scikit-learn | future `ml_engine/app/models/` or training scripts | Same split, preprocessing, CV folds, and macro F1 metric for all models |
| Fastify route, API endpoint, backend server | Member B | Fastify, Node | `backend/src/server.js` | Must call deterministic safety checks before returning any drug set to a client |
| Prisma, MySQL, schema, migration | Member B | Prisma CLI | `backend/prisma/schema.prisma` | Shadow DB is required for `migrate dev` locally; do not bypass it |
| set-cover, combinatorial search, optimization | Member C (w/ B) | Python | `ml_engine/app/services/combination_search.py` | Operates on graph coverage, rules, and future traditional model scores without treating any as clinical truth |
| explainability, why trace, reporting | Member C | Python, Streamlit/React | future reporting docs or app files | Every prediction needs provenance and a trace; this is a hard requirement, not polish |
| frontend, UI, Streamlit, React, dashboard | Member C | Streamlit or React | `frontend/` or future Streamlit app | Must visually separate rule-based blocks from model-predicted risk |
| Docker, docker-compose, local environment | whoever's blocked | n/a | `docker-compose.yml`, `Makefile` | Check `docker info` succeeds, not just that the compose file looks right |
| Tests | task owner | `node --test` / `pytest` | `backend/tests/`, `ml_engine/tests/` | New logic needs a matching test in the same change, not a follow-up |

## General Operating Rules for Codex on This Repo

- Read `CONTEXT.md`, `ROADMAP.md`, and this file before starting any task.
  Use what is specified here, since it reflects real project decisions.
- Report exact numbers such as row counts, test pass counts, and response
  bodies. Avoid vague summaries like "everything works."
- Do not start or stop Docker containers unless a task explicitly asks for it or
  the daemon itself is confirmed down. Check `docker info` first.
- If a task touches a file outside its stated scope, say so explicitly in the
  report rather than silently including it.
