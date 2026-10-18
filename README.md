# PolyMerge

PolyMerge is a biomedical research decision-support prototype that explores
existing-drug combinations using represented graph evidence, configured research
rules, deterministic optimization, and traditional machine learning.

The research goal is to identify combinations worth further investigation for
multiple selected diseases, explain why they appear in the results, and expose
evidence gaps. It is not a prescribing tool or a clinically validated discovery system.

## What It Does

- Four-step simulation: Select Diseases, Analyze, Review Candidates, Understand Result.
- Neo4j disease catalog, represented treatment coverage and traceable graph paths.
- Bounded candidate generation, deterministic ranking and a greedy set-cover baseline.
- Configured research-rule evaluation with verified mapping coverage reported separately.
- Frozen Random Forest classification of supported drug-pair interaction severity.
- Simple/Researcher views, candidate pagination, reset and stale-response protection.
- Candidate-specific Research Takeaway: a deterministic summary of findings and
  unresolved research questions, not another model or a recommendation.
- Model Analysis with preserved EDA, model comparison and final evaluation results.

Analysis completion stays on Analyze. Select **Review Candidates** explicitly.
Changing candidates or views reuses the returned results; it does not rerun inference.

## Scientific Boundaries

The Random Forest predicts curated DDInter **Major, Moderate or Minor** severity
for supported drug pairs. It does not predict synergy, clinical effectiveness,
absence of interaction, dosage, complete safety or physical polypill feasibility.
Single-drug interaction prediction is not applicable. Unsupported pairs remain
unavailable; partially supported combinations retain their available pair results.

Graph coverage describes represented treatment relationships, not efficacy.
Hetionet `CrC` means compound resemblance, not a DDI label. Nine reviewed positive
drug-class mappings support the configured rules; unmapped membership is unknown,
not negative. No triggered rule is not a passed clinical safety assessment.
Graph evidence, rule applicability and supervised classification remain separate.

## Architecture and Stack

```text
Browser -> Streamlit wrapper -> iframe: Fastify-hosted static frontend
                                      -> Fastify API
                                         -> FastAPI ML/graph service
                                            -> existing local Neo4j
                                            -> frozen Random Forest + rule mappings
```

Python 3.11, FastAPI/Uvicorn, scikit-learn 1.4.0, NumPy 1.26.4, RDKit,
Neo4j 5, Node.js (22 baseline; >=20 required), Fastify, plain HTML/CSS/JavaScript,
and Streamlit 1.66.0. Streamlit and ML use separate locked environments.
MySQL/Prisma and legacy history/demo routes are not required by the local demo;
the launcher disables legacy routes. See [architecture](docs/ARCHITECTURE.md).

## Research Methodology and Results

The dataset contains 130,422 canonical labeled drug pairs and 55 frozen features:
molecular descriptors and symmetric graph summaries, with explicit missingness.
DDInter supplies severity labels; Hetionet supplies evidence and graph features;
PubChem/RDKit supply reviewed structures and descriptors. Unknown severity is
excluded; there is no synthetic no-interaction class.

Logistic Regression, Random Forest and Histogram Gradient Boosting were compared
using the same five-fold training-only CV contract. Random Forest was selected
by mean Macro F1. The held-out test split was evaluated once and must not be
reused for tuning or repeated final evaluation.

| Preserved result | Value |
| --- | ---: |
| CV Macro F1 | 0.506086 +/- 0.005695 |
| Final test Macro F1 | 0.524630 |
| Final test balanced accuracy | 0.475467 |
| Final test Macro AUROC | 0.798793 |
| Final test Macro AUPRC | 0.632468 |

Major and Minor recall are weaker than Moderate recall. These are classification
results, not clinical validation. See [final evaluation](docs/sprint5-final-model-evaluation.md)
and [algorithm limitations](docs/algorithm-limitations.md).

The reviewed graph fragment contains 3,415 nodes and 16,230 relationships:
299 compounds, 25 diseases, 1,411 genes, 37 pharmacologic classes and 1,643 side
effects. Candidate coverage uses represented `CtD` edges. Ranking prioritizes
rule status, coverage, fewer drugs and stable candidate IDs, not predicted severity.
See [graph schema](docs/knowledge-graph-schema.md) and [rule provenance](data/rules/README.md).

## Quick Start

First obtain the trusted model and an existing, correctly loaded local Neo4j
database from the project owner. Git does not contain the private model binary.
Install Python **3.11**, Node.js/npm and your chosen Neo4j runtime.
Follow [Local Setup](docs/LOCAL_SETUP.md) for environment configuration,
platform-specific prerequisites, manual startup and recovery.

| Action | macOS | Windows 10/11 |
| --- | --- | --- |
| First-time installation | Double-click `Setup-PolyMerge.command` | Double-click `Setup-PolyMerge.bat` |
| Daily start | Double-click `Start-PolyMerge.command` | Double-click `Start-PolyMerge.bat` |
| Shutdown | Double-click `Stop-PolyMerge.command` | Double-click `Stop-PolyMerge.bat` |

Setup asks before installing hash-locked packages into new isolated environments.
Daily startup does not install packages. The supervisor validates the model
checksum and complete source graph identity before starting services on loopback.
It opens Streamlit once when ready and prints the actual URLs.
Defaults: Streamlit http://127.0.0.1:8501; direct frontend http://127.0.0.1:3000.
Keep the launcher terminal open. Stop shuts down only its managed application
processes and deliberately leaves the shared database running.

Run the shared supervisor manually instead of double-clicking:

```bash
python3.11 scripts/local_demo.py start --ml-port 8000 --backend-port 3000 --streamlit-port 8501
python3.11 scripts/check_demo_readiness.py
python3.11 scripts/local_demo.py stop
```

On Windows replace `python3.11` with `py -3.11`.
Use `check_demo_readiness.py --preflight` before starting.
Logs are under `.polymerge/logs/`; they are not committed.
Port conflicts fail without killing existing services. The direct frontend is the
fallback if the wrapper fails. [Recovery instructions](docs/LOCAL_SETUP.md#recovery)
cover missing dependencies, occupied ports and stale launcher state.

## Environment and Model

Copy `.env.example` to a private `.env`, and configure `NEO4J_URI`,
`NEO4J_USER` and `NEO4J_PASSWORD` for your existing loopback database.
Do not commit credentials. The supervisor sets matching application ports,
frontend origin, iframe origin and internal service URL in its child processes.

Place the original trusted artifact at
`models/sprint5/random_forest_ddi_pipeline.joblib`, or configure
`POLYMERGE_DDI_MODEL_PATH`. Never load an untrusted joblib file.

- Model: `RandomForestClassifier-sprint5-v1-65e9834666ad19c5`
- Size: 251,404,304 bytes
- SHA-256: `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`

Do not upgrade the frozen runtime, substitute a model, retrain, or rebuild data
to make a demo pass. The launcher never provisions or overwrites graph data.

## Repository Guide

| Path | Responsibility |
| --- | --- |
| [backend](backend/README.md) | Fastify API, validation, static serving and explainability |
| [ml_engine](ml_engine/README.md) | Graph retrieval, candidate generation, rules and frozen inference |
| [frontend](frontend/README.md) | Existing research dashboard and branding assets |
| [data](data/README.md) | Dataset provenance, graph fragment and reviewed mappings |
| [scripts](scripts/README.md) | Local supervisor, read-only checks and research utilities |
| [docs](docs/README.md) | Current guides, research records and historical audits |
| `Sprints/` | Historical sprint plans and individual contributions |

## Verification

After setup, from the repository root on macOS:

```bash
npm --prefix backend test
(cd ml_engine && ../.venv-demo-ml/bin/python -m pytest -q)
.venv-demo-ml/bin/python scripts/validate_sprint4_contract.py
.venv-demo-ml/bin/python scripts/check_release_metadata.py
.venv-demo-ml/bin/python -m unittest discover -s scripts/tests -v
node --check frontend/app.js
node --check frontend/explainability.js
git diff --check
```

Windows uses `.venv-demo-ml\Scripts\python.exe`; run pytest from `ml_engine`.
Private-model prediction parity and real Neo4j scenarios require the owner's
preserved fixtures and local assets. Tests do not replace browser acceptance.
Use the [final demonstration guide](docs/FINAL_DEMO_GUIDE.md) and
[manual UI acceptance checklist](docs/sprint6-guided-demo.md).

## Status, Team and Security

Current direction: **local academic demonstration**, not public deployment.
PR #58 targets the integration branch; PR #57 targets main. Main synchronization
requires review and explicit approval. See [project status](docs/project-status.md)
and the [finalization audit](docs/audits/local-demo-finalization.md) for dated evidence,
platform checks and outstanding work. No official main demo baseline is declared
until the approved integration is merged and verified.

[Jared, Ranee and Pamela](TEAM.md) own graph/data, backend/ML integration and
optimization/explainability work. Historical deployment documents preserve
feasibility findings; they are not evidence of a live public service.

Known frozen-runtime/container vulnerability findings remain separate from local
functional verification. Scanner gates are not disabled or represented as green.
Keep the demo loopback-only and use trusted inputs. PolyMerge is research software,
not medical advice, clinical certification, regulatory approval or autonomous prescribing.
