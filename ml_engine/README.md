# ML and Graph Service

FastAPI owns Neo4j retrieval, candidate generation, deterministic research rules,
greedy optimization and frozen Random Forest drug-pair inference. Graph coverage,
rule applicability and prediction are separate, not a medical safety score.

Use [local setup](../docs/LOCAL_SETUP.md): Python 3.11, hash-locked packages,
original trusted model and existing reviewed Neo4j. Required private configuration:
`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`; optional
`POLYMERGE_DDI_MODEL_PATH`. Startup never trains or imports graph data.

The supervisor runs `python -m uvicorn main:app` with one worker and loopback
binding. Run `../.venv-demo-ml/bin/python -m pytest -q` here on macOS;
Windows uses `..\.venv-demo-ml\Scripts\python.exe -m pytest -q`.
`/ready` is the dependency/model gate, not merely process liveness.

Supported pairs use the frozen 55-feature bridge. Unsupported pairs remain
unavailable; single-drug interaction inference is not applicable.
See [model evaluation](../docs/sprint5-final-model-evaluation.md) and
[limitations](../docs/algorithm-limitations.md). Do not rerun final evaluation.
