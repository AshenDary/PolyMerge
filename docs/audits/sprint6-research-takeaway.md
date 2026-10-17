# Research Takeaway Verification

Date: 2026-10-16. Starting branch: `fix/polymerge-availability-and-rule-mapping`.
Starting commit: `2ab885b0f7d88a5aaffba7c0f72084cdeb0095ea`; worktree clean.

## Scope

A deterministic synthesis of graph coverage, configured-rule applicability,
and available drug-pair classification evidence, identifying unresolved
research questions.

The new unframed section follows all Step 4 explanation and technical details.
Three sentences use the selected response only: selected/covered disease IDs,
rule applicability/exclusion, and distinct supported unordered drug pairs.
Missing coverage data is unknown, not invented zero coverage. Uncovered names
come from the catalog; missing names remain explicitly unavailable, with stable
IDs in Researcher View. Single-drug prediction is not applicable, not an issue.

Review categories prioritize exclusions/incomplete rules, unclassified pairs
or actual Major classifications, uncovered diseases, then missing graph paths.
At most three categories are visible; an optional native disclosure retains
additional graph gaps. Only supplied failure reasons are used. Rule mapping
completeness is distinct from clinical validation. No overall severity, score,
synergy, clinical recommendation or new model is generated.

Both modes share exactly the same conclusion. Selection uses existing results;
reset and stale-response guards remain in force. Existing graph, model analysis,
pair predictions, ranking, paging, APIs and Streamlit wrapper are unchanged.

## Automated Checks

- Backend suite: 107 passed, including 58 frontend behavioral tests (15 added).
- ML suite: 105 passed; six existing dependency deprecation warnings.
- Sprint 4 contract validation: PASS; no frozen-model evaluation/retraining.
- Release metadata check and five script unit tests: PASS.
- JavaScript syntax checks for app.js and explainability.js: PASS.
- git diff --check: PASS.
- Frozen model SHA-256 unchanged:
  `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.

Tests cover full/partial/zero/unknown coverage; all rule states and exclusions;
single/all/partial/no predictions; deduplicated unordered pairs; actual Major
classification without approval/rejection; no fabricated reasons; three-category
limit; escaping; mode/selection/reset/stale lifecycle; preserved evidence.

## Live Response Checks

Local backend http://127.0.0.1:3002 serves the latest static assets without a
restart. Actual API responses were rendered through the frontend in both modes;
candidate objects remained unchanged. These are not browser acceptance tests.

- Hypertension DOID:10763: Valsartan single and Valsartan + Verapamil pair,
  full 1/1 coverage; rules not evaluable.
- Hypertension + type 2 diabetes DOID:9352: single and multi-drug candidates,
  full 2/2 coverage; supported pair prediction retained.
- DOID:14221, 585, 6364, 8398, 7148: Hydrochlorothiazide + Metformin + Timolol,
  3/5 represented coverage, all three pairs classified; osteoarthritis and
  rheumatoid arthritis correctly listed as uncovered.
- DOID:3393 + 1936: Pravastatin + Acetylsalicylic acid, partial rule evaluation.
- DOID:9352 with maxDrugCount=3/maxCandidateSets=500: rank 467,
  Acarbose + Chlorpropamide + Gliclazide, 1/3 classified pairs; actual reviewed
  bridge-mapping reason retained. No default search limit changed.
- Backend dependency health, frontend, Streamlit root and Streamlit health all
  returned HTTP 200. Streamlit remains at http://127.0.0.1:8503.

## Pending Manual Acceptance

Browser discovery reported **No browser is available**. Desktop/mobile visual
layout, keyboard interaction, console checks and actual Streamlit iframe
rendering remain pending. Mode/selection/reset are verified behaviorally, not
visually. Follow the guided-demo checklist before acceptance.

Existing incomplete rule mappings, unsupported ML feature bridges and graph
coverage gaps remain genuine limitations. Fully evaluated/triggered rules and
Major interpretation are fixture-tested, not claimed as observed live results.
Existing security/public-deployment restrictions remain unchanged. No public
deployment, merge, PR, paper edits or presentation edits were performed.
