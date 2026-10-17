# Guided Navigation and Research-Rule Coverage Remediation

Date: 2026-10-17 (Asia/Manila).
Starting branch: `fix/polymerge-availability-and-rule-mapping`.
Starting SHA: `40aea9991726f1b55d1cc8f2f91c23d6eedda93a` (clean).
Work branch: `fix/simulation-navigation-and-mapping-coverage`.
Performance, guided simulation, availability, readability and Research Takeaway
commits were present before branching. No merge, PR, public deployment, paper
or presentation modification was performed.

## Navigation Root Cause

Three independent conditions caused the reported behavior:

1. `analyzeCombination` explicitly called `setSimulationStep(3, true)` on
   success and returned to Step 1 on errors.
2. Step 2 availability depended exclusively on `analysisStartedAt`, which was
   cleared in the request's `finally` block. Completed Analyze was inaccessible.
3. CSS hid `#workflow` only on Step 1 and showed `#analysis-summary` only on
   Step 3. Thus Review displayed the Analyze panel and summary simultaneously.

An additional premature unlock came from automatically selecting the first
candidate at response time and allowing Step 4 with any current result.

The frontend now has explicit idle/running/complete/error analysis state.
Step 2 stays active during and after analysis, including failures. It owns the
completed summary, actual errors, retry and explicit Review Candidates action.
The workflow panel is visible only on Step 2; candidate cards only on Step 3.
Steps are native buttons with current/completed/available/unavailable states.
Running requests lock other steps; reset remains available. Completed Analyze
is revisitable without fetching. Step 4 requires a valid user-selected returned
candidate. Invalid IDs do not fall back silently to the first candidate.
Selection, five-card pagination and display mode persist across navigation.
Generation guards prevent late responses/errors from restoring results.

## Mapping Root Cause and Inventory

Live Neo4j and checked-in CSV identity contracts agree on **299 compounds**,
each with a canonical ID/name. There are **91 PCiC edges across 63 compounds**.
Graph identity availability is not the same as reviewed rule-category evidence.

Before: the rule artifact reviewed only aspirin (DB00945), a positive NSAID
membership from PCiC. Thus 1/299 compounds had reviewed category evidence and
298 lacked it. No compound had verified membership/nonmembership across all
six configured categories. Neither ID formatting nor frontend interpretation
caused the 99 unknown candidates; missing category evidence was genuine.

The four-disease scenario is metabolic syndrome X (DOID:14221), coronary artery
disease (DOID:3393), chronic kidney failure (DOID:784), hypertension (DOID:10763).
Before expansion, Metformin appeared in all 100 results, Valsartan in 68 and
Ramipril in 20. These common drugs lacked reviewed rule-category records.
Coronary/atherosclerosis results were dominated by Pravastatin, Lovastatin and
Niacin (27 occurrences each). Hypertension commonly included Esmolol (22) and
Ramipril (12). Full per-scenario frequency lists and canonical compound
enumeration are emitted by `scripts/audit_rule_coverage.py`.

Missing PCiC edges cannot establish negative membership. Some existing edges
describe effects such as decreased blood pressure, not a configured class;
converting those to ACE-inhibitor membership would be unjustified. Expanding
the six supported rule categories would alter rule meaning, not repair data.

## New Positive Evidence

Artifact version: `polymerge-research-rules-2026-10-17-v2`.
Eight additions; total reviewed identity/category records now **9/299**.
All new records verified 2026-10-17 against existing graph IDs/names and the
following authoritative category sources. The original aspirin record remains.

| Compound | Canonical suffix | Positive category | Classification source |
|---|---|---|---|
| Ramipril | DB00178 | ACE inhibitor | [DailyMed label](https://www.dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d5c58fb5-b415-4567-9790-55631705c5cd&type=display) |
| Benazepril | DB00542 | ACE inhibitor | [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=0653322d-70c6-45f7-a9d1-41efee1d7387) |
| Enalapril | DB00584 | ACE inhibitor | [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=8fe8dc52-dee6-4d33-b798-e90128011f46) |
| Lisinopril | DB00722 | ACE inhibitor | [DailyMed label](https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b62815f3-77fc-4074-a28a-918ab5cc32db) |
| Captopril | DB01197 | ACE inhibitor | [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1a91ac7f-b75d-d111-e063-6394a90a2a93) |
| Amiloride | DB00594 | Potassium-sparing diuretic | [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=60e8e566-28c6-99ba-e053-2a91aa0a8dbe) |
| Triamterene | DB00384 | Potassium-sparing diuretic | [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=fea50328-b3d5-4300-8c67-82cda0a975b7) |
| Spironolactone | DB00421 | Potassium-sparing diuretic | [NLM MeSH D013148](https://www.ncbi.nlm.nih.gov/mesh/?term=D013148) |

Identity notes explicitly distinguish salts, active moieties and prodrugs;
enalapril is not renamed enalaprilat. Brand names and combination products are
not aliased. Source IDs, URLs, dates and provenance are retained per record.
No restricted DrugBank dataset or complete label text was redistributed.
Source attribution/reuse boundaries are in `data/rules/README.md`.

## Conservative Evaluation

Python and JavaScript read the same artifact. Positive tokens trigger only
the existing three configured research exclusions. Each identity exposes
per-category `verified_member` or `unknown` evidence. No reviewed closed-world
negative source was established, so **zero verified-nonmember records** were
added. A `complete` flag cannot turn canonical unknown memberships into absent
ones. Closed-world literal categories remain legacy fixtures only.

A known prohibited pair makes that individual rule evaluated/triggered while
the remaining rules can stay unknown. Partial applicability is not a passed
check. No rejection alone establishes no-interaction status or clinical safety.
The exclusion semantics are research-only, not clinically validated; source
labels establish category membership, not universal clinical prohibition.

## Measured Before and After

Each nonempty scenario returns the configured top 100 candidates.
F/P/N = fully evaluated / partially evaluated / not evaluable candidate counts.

| Scenario | Before F/P/N | After F/P/N | Rejected before/after | Candidates with predictions before/after |
|---|---:|---:|---:|---:|
| Hypertension | 0/0/100 | 0/19/81 | 0/0 | 32/32 |
| Hypertension + diabetes | 0/0/100 | 0/22/78 | 0/0 | 93/93 |
| Coronary disease + atherosclerosis | 0/4/96 | 0/20/80 | 0/0 | 94/94 |
| Four-disease screenshot | 0/1/99 | 0/28/72 | 0/0 | 100/100 |
| Osteoarthritis + rheumatoid arthritis | 0/0/0 | 0/0/0 | 0/0 | 0/0 |

Fully evaluated counts did **not** increase. For example, the four-disease
pool now has 28 partially evaluated individual rules and 272 not-evaluable
rules out of 300; it does not have 28 fully evaluated candidates.
Its ML statuses remain 98 applied and 2 partial. The other nonempty scenarios
retain 68/32, 7/93 and 6/94 not-applied/applied counts respectively.

### Ranking and Exclusions

The ranking algorithm was not modified. It already places candidates without
triggered exclusions first. New evidence therefore legitimately changes its
inputs: Ramipril + Triamterene and Ramipril + Spironolactone now trigger the
existing ACE-inhibitor/potassium-sparing-diuretic research exclusion.

Those two pairs leave the hypertension top 100; the corresponding triples with
Metformin leave the four-disease top 100. Their prior ranks were 74/75 and 94/96.
Each pool retains 98 candidates, with 25 and 5 shared ranks shifting respectively.
This explains why returned rejection counts remain zero despite newly detected
exclusions: untriggered candidates fill the capped list first.

Graph evidence, covered/uncovered IDs and pair-prediction payloads are identical
for every retained candidate across all scenarios. Two-disease and coronary
scenario candidate sets/ranks are completely unchanged. Optimizer selected
drugs are unchanged in all five scenarios; separate canonical-ID tests verify
that the merged optimizer selection cannot bypass a newly mapped exclusion.

## UX and Takeaway

Analysis Summary separates selected-disease, returned-candidate and
candidate-with-prediction counts (not pair counts). Research-rule coverage has
a short summary and an expandable exact count breakdown. No dense warning is
duplicated above the technical pipeline. Research Rule Check uses checked,
limited-evaluation or insufficient-information wording; actual exclusions stay
prominent. Technical details retain status, category evidence, provenance,
mapping version, source identifiers and dates.

Research Takeaway remains three deterministic sentences with at most three
visible review categories. It follows current candidate rule values, remains
identical across modes and adds no requests, LLM or aggregate severity score.

## Verification

- Backend: **114 passed**, including **64 frontend behavioral tests**.
- ML: **116 passed**, six existing dependency deprecation warnings.
- Focused availability, candidate generation and optimizer tests: **40 passed**.
- Mapping tests cover every reviewed canonical ID/provenance, Python/JS parity,
  unknowns, no invented negatives, canonical triggers and merged selections.
- Seven script unit tests, release metadata and Sprint 4 feature contract: PASS.
- app.js/explainability.js syntax and git diff --check: PASS.
- Live graph import/identity contract: all 299 IDs/names match the CSV; 91 PCiC
  edges unchanged; all nine reviewed records resolve to actual graph compounds.
- Frozen Random Forest SHA-256 unchanged:
  `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
- No frozen final-test reevaluation, retraining, 55-feature contract change or
  graph modification. Routine suite fixture-model tests are not a new final run.

Before/after API evidence is retained locally in `/tmp/polymerge-nav-before`
and `/tmp/polymerge-nav-after`; rerun the audit script with `--output` and
`--baseline` to compare equivalent snapshots. The script distinguishes new
candidates from changes to evidence/predictions of shared candidates.

Live HTTP + frontend-state/renderer checks passed for hypertension, two and
four diseases, and unsupported treatment coverage. They verify staying on Step
2, explicit 3/4 navigation, return to 2/3, mode consistency, pagination,
selection, no refetch during navigation, and reset. Backend/ML restarted only
to load the mapping; Streamlit was left running. Backend dependencies, Streamlit
root and Streamlit health returned HTTP 200.

## Remaining Review

Browser discovery returned **No browser is available**. Real desktop/mobile
layout, browser keyboard behavior, console and Streamlit iframe rendering are
manual acceptance items, not passed visual tests. Open http://127.0.0.1:3002
and http://127.0.0.1:8503 and follow `docs/sprint6-guided-demo.md`.

There remain **290 compounds without reviewed category records** and **299
without complete closed-world evidence**. Eplerenone, Trandolapril and other
unreviewed potentially relevant drugs remain unknown; primary classes of
common Valsartan/Metformin/Esmolol do not prove nonmembership in all configured
categories. The mapping expansion is deliberately partial, not a comprehensive
drug-class catalog. Sources and category decisions still merit independent
biomedical review. Clinical exclusions, dosing, safety, therapeutic synergy and
formulation feasibility are not validated. Existing public-deployment security
restrictions remain in force.
