# PolyMerge dashboard demo

This workflow uses the graph-backed candidate-set API. Candidate results and
evidence must come from the configured Hetionet graph service; do not use demo
or synthetic paths for screenshots.

## Start the services

From the repository root, start Neo4j and MySQL:

```powershell
docker compose up -d neo4j mysql
```

Load the checked-in Hetionet fragment once, after Neo4j is healthy:

```powershell
python scripts/load_fragment.py
```

Start the graph and ML API in a separate terminal (create and activate the
`ml_engine\.venv` first if needed, then install `ml_engine\requirements.txt`):

```powershell
Set-Location ml_engine
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Start the dashboard API in another terminal:

```powershell
Set-Location backend
npm.cmd start
```

Open `http://localhost:3000`. Confirm the disease catalog loads before starting
the walkthrough. If it is unavailable, check `http://localhost:8000/health`,
`http://localhost:8000/api/diseases`, and `http://localhost:3000/health/dependencies`.

## Walkthrough

1. Search for a disease by name or stable ID, select one or more diseases, and
   choose **Search Candidate Sets**.
2. Review candidate ranking, drug names and IDs, represented disease coverage,
   and accepted/rejected state.
3. Choose **View evidence** on an accepted candidate. Review its graph paths,
   deterministic rules, and ML status as separate evidence channels.
4. Repeat for a rejected candidate and inspect the structured reason, affected
   drug pair, and rule stage.
5. If the service reports ML as applied, review only the returned pairwise
   severity classes and model/version details. If it is not applied or
   unavailable, verify that state is stated clearly and no prediction is shown.
6. Use the sidebar arrow to collapse and expand navigation, then repeat the
   search at a narrow viewport to check the responsive layout.

## Screenshot checklist

Capture real dashboard states in the browser after the services are healthy.
Use the same disease query throughout so the evidence can be traced to one
search. Suggested filenames:

- `01-disease-selection.png`
- `02-candidate-results.png`
- `03-graph-evidence.png`
- `04-deterministic-rules.png`
- `05-ml-prediction.png` (only when the model returns an applied prediction)
- `06-explainability.png`
- `07-service-unavailable.png` (optional, clearly showing the unavailable state)

Keep the research disclaimer visible where practical. Do not present graph
coverage as efficacy, rule checks as comprehensive safety validation, or ML
severity as clinical guidance. Never combine the channels into a safety score.
