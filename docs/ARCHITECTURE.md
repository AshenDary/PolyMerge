# Local Architecture

```text
Browser
  Streamlit wrapper (loopback 8501)
    iframe -> Fastify static HTML/CSS/JS (loopback 3000)
                same-origin /api requests
                  Fastify validation, limits, orchestration
                    FastAPI ML/graph service (loopback 8000)
                      existing Neo4j (loopback Bolt)
                      reviewed model metadata + trusted joblib
                      frozen feature bridge + research-rule mappings
```

Ports above are defaults; the supervisor propagates custom ports consistently.
Streamlit embeds the actual frontend, not a duplicate interface. The browser
calls Fastify; FastAPI and Neo4j are internal dependencies in the normal flow.
All application listeners are loopback-only. Legacy MySQL/history/demo behavior
is disabled in the supervised local configuration.

## Data Flow

1. FastAPI retrieves the disease catalog and compounds with represented Hetionet
   treatment edges using parameterized Cypher.
2. Candidate generation constructs bounded drug combinations with coverage,
   gene/side-effect context and deterministic provenance paths.
3. Configured research rules evaluate only their represented facts. Nine
   positive canonical mappings are reviewed; unknown membership stays unknown.
4. Ranking uses eligibility, represented coverage, fewer drugs and stable IDs.
   The greedy set-cover baseline seeks uncovered represented disease coverage.
   It is not a learned clinical optimization objective.
5. The frozen feature bridge builds supported 55-feature drug-pair rows.
   Random Forest inference returns Major/Moderate/Minor only for supported pairs.
   Single-drug and unmapped/partially mapped states remain explicit.
6. Fastify validates and returns the result. Frontend pagination, modes,
   explanations and Research Takeaway reuse that response.
7. Research Takeaway in `frontend/app.js` deterministically summarizes graph
   findings, rule applicability and available classification, prioritizing
   unresolved research questions. It is not an LLM, new score or prescription.

## Model and Lifecycle

The model service checks tracked metadata, feature order and trusted checksum
before loading the original artifact. Setup preserves Python 3.11,
scikit-learn 1.4.0 and NumPy 1.26.4; Streamlit runs in a separate environment.
The supervisor checks source graph identity before startup, then waits for real
readiness rather than accepting an open port. Runtime `/ready` includes required
model/graph initialization; Streamlit has a separate health endpoint.

A local authenticated control endpoint owns shutdown. POSIX groups and Windows
Job Objects scope termination to managed application descendants. Neo4j remains
running to preserve shared state. The launcher never creates or resets data.

## Boundaries

Graph coverage is not efficacy. Research rules are incomplete and not clinically
validated. DDI classification is not synergy, dosage or comprehensive safety.
No combined medical safety score is produced. The frozen evaluation is not rerun
during startup or Model Analysis. See [limitations](algorithm-limitations.md),
[API scope](api.md) and [setup](LOCAL_SETUP.md).
