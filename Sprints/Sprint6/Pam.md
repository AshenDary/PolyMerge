# Pam — Sprint 6 · Final Frontend, Explainability & Demo Experience (#53)

## Branch: `sprint6/pamela/final-frontend-demo`

## Status: ✅ Complete

---

## What was delivered

### Backend — canonical API endpoints
- `POST /api/candidate-sets/search` — canonical endpoint for the frontend (replaces old `/predict/candidate-sets` for UI use)
- `GET /api/candidate-sets/{queryId}/explain?format=detailed|comparison|structured` — three-channel explainability payload
- `GET /api/diseases?q=` — disease search with optional query filter
- In-memory query store (thread-safe, bounded to 256 entries) so explain can look up prior searches by queryId

### Frontend — complete rewrite
| Screen | Deliverable |
|--------|-------------|
| Screen 1 | Disease selection with live search/filter, multi-select, clear button, selection count |
| Screen 2 | Dynamic workflow steps (done/active/pending/error states), ML status note with dot indicator |
| Screen 3 | Candidate ranking with coverage bars, drug name + ID display, accepted/rejected badges, rejection reason boxes with affected drug pair display, ML not-applied row |
| Screen 4 | Three-channel explainability — **Graph Evidence (blue)**, **Deterministic Safety Rules (green/red)**, **ML Prediction (purple)** — visually and structurally separated |

### Three-channel evidence separation (never combined into a score)
| Channel | Colour | What it shows |
|---------|--------|---------------|
| Graph Evidence | Blue `#1d6ae5` | CtD treatment paths, gene-context paths (CbG/CuG/CdG), side-effect paths (CcSE), source/version, path IDs |
| Deterministic Rules | Green (accepted) / Red (rejected) | accepted/rejected status, structured rejection reason, affected drug pair, rule stage |
| ML Prediction | Purple `#7c3aed` | applied / not-applied / unavailable state, predicted Major/Moderate/Minor class, probability bars, model version, research disclaimer |

### Supported graph relationship types
- ✅ Compound → CtD → Disease (treatment)
- ✅ Compound → CbG/CuG/CdG → Gene (gene_context)
- ✅ Compound → CcSE → Side Effect (side_effect_context)
- ❌ CrC never rendered as DDI evidence (tested)
- ❌ No synthetic biological paths

### UX / visual
- Consistent dashboard styling with design token system
- Responsive layout (900px and 600px breakpoints)
- Clear empty / loading (spinner) / error / graph-unavailable / ML-unavailable states
- Global research disclaimer banner
- Research-use pill badge in top bar
- XSS-safe rendering via `escHtml()`
- No combined safety score

### Frontend validation tests (`test_sprint6_frontend.py`)
All DoD checklist items covered:
- [x] main page loads / frontend JS loads / explainability assets load
- [x] candidate response renders
- [x] accepted candidate renders
- [x] rejected candidate renders (with reasons)
- [x] active ML result renders (structure verified)
- [x] not-applied ML state renders
- [x] graph paths render (CtD, gene, side-effect)
- [x] no unsafe/clinical wording
- [x] no console-blocking JS errors (ESM-safe, no syntax errors)
- [x] three-channel explainability structure verified
- [x] CrC not in graph evidence
- [x] graph unavailable → 503

---

## Files changed
- `frontend/index.html` — full rewrite
- `frontend/styles.css` — full rewrite with design tokens & channel colours
- `frontend/app.js` — full rewrite, uses canonical POST /api/candidate-sets/search
- `frontend/explainability.js` — existing reference implementation kept intact (not removed)
- `frontend/explainability.css` — existing styles kept intact (imported in index.html)
- `ml_engine/main.py` — added Sprint 6 canonical endpoints + query store
- `ml_engine/tests/test_sprint6_frontend.py` — new frontend validation test suite

---

## Definition of Done checklist

- [x] complete usable research dashboard
- [x] real candidate-set API used (`POST /api/candidate-sets/search`)
- [x] three channels visually distinct
- [x] explainability works from main flow
- [x] error/unavailable states work
- [x] frontend validation passes
- [x] no clinical recommendations
- [x] demo workflow ready
- [ ] screenshots — to be captured when backend is live (Neo4j connected)
