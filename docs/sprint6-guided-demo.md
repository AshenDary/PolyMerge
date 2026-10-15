# Guided Simulation Manual Acceptance

Local frontend: http://127.0.0.1:3002
Local wrapper: http://127.0.0.1:8503
Local ML health: http://127.0.0.1:8000/health

Browser acceptance is PENDING: the browser tool reported no available browser.
Static DOM tests and HTTP checks do not verify visual layout or iframe behavior.

1. On desktop, laptop, tablet and mobile, open Simulation. Confirm Simple View,
   Select Diseases, visible focus, readable contrast and no horizontal overflow.
2. Search hypertension (Disease::DOID:10763), select it and Analyze Candidates.
   Confirm Analyze shows elapsed time without fabricated percentages.
3. Confirm Review Candidates shows five rows and full-response summary counts.
   Show next 5 must show ranks 6-10; previous must return to 1-5.
4. Select a single-drug candidate. Understand Result must say Not applicable for
   interaction prediction, show treatment connections and a short explanation.
5. Switch Researcher View. Confirm selected candidate and counts persist without
   a network analysis request. Expand pipeline, IDs, provenance, graph paths and
   model details; optionally show all returned candidates.
6. Reset, select hypertension and type 2 diabetes (Disease::DOID:9352), analyze,
   and inspect a supported multi-drug candidate. Predictions are per pair, not a
   clinical score; graph evidence and configured rules remain separate.
7. Reset from each step, including during analysis. Selection, results, evidence
   and timers clear; no late result/error returns. Mode may persist. Server work
   can continue, and a new request can receive a busy response until it finishes.
8. Use keyboard-only navigation for steps, modes, pagination, details and reset.
   Check long IDs wrap and graph connections remain readable at all viewports.
9. Review Model Analysis comparison, EDA, metrics and limitations. Repeat in the
   Streamlit wrapper and inspect the console for errors. Capture screenshots.

Do not interpret untriggered rules as safety: configured class/literal tokens
are not yet mapped to canonical Compound::DB identifiers. Public deployment
remains blocked by the separate security findings in the historical audit.
