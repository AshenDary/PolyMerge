# Understand Result Readability

Date: 2026-10-16 (Asia/Manila).
Started clean on fix/polymerge-availability-and-rule-mapping at
591770057efac10e605fc85115392699c1bc59c5; continued on that branch.

## Focused Change

shortCandidateSummary previously concatenated coverage, disease names, rule
status, all pair predictions and rank into one paragraph. renderSelectedCandidate
then embedded another candidate narrative inside its research details.

Both modes now render one overview from structured response fields:

1. Actual rank and drug-name heading.
2. One-sentence treatment summary, covered-disease list, graph coverage meter,
   and collapsed uncovered-disease list.
3. Rule outcome and supplied per-rule coverage counts. Incomplete coverage says
   Not fully evaluated, never passed/safe. Known exclusions remain visible even
   with incomplete coverage. Missing applicability metadata is not inferred.
4. One row per successful pair, with its actual severity. Unsupported pairs have
   a separate list retaining their reasons. Single drugs say Not applicable.
5. A short rank explanation, using the actual returned rank.

Graph evidence, rule provenance, model versions, candidate/disease identifiers,
ranking tie-breaks, optimizer selections and glossary remain accessible through
collapsed details. Researcher View opens identifiers but retains the same
overview. Switching modes does not fetch, recompute, reorder or replace results.
The unused legacy narrative helpers remain for compatibility; they are not
rendered in Understand Result. No duplicated narrative or final conclusion is
embedded in the new overview.

Ranking was inspected, not changed: the canonical path prioritizes configured
exclusion status, greater represented coverage and fewer drugs, with stable
generation/ID tie ordering. Backend rule checks can reject without reranking.
The concise text does not claim clinical superiority or ML-based ranking.

## Layout

Unframed sections use subtle dividers, constrained paragraph widths, wrapping
names and aligned prediction columns. At narrow viewport widths prediction
rows stack their label below the pair name. Statuses are mostly plain text.
The repeated global rule banner is hidden in step 4, where the candidate-specific
rule section already explains applicability; the shared research footer remains.

Stepper buttons now explicitly shrink and wrap inside their grid cells. Named
container queries switch four columns to two below 640px of available content
width, and to one below 300px. The existing viewport fallback remains. Display
mode buttons also wrap. A mobile collapsed-sidebar margin override prevents
retaining a desktop sidebar offset on a narrow screen.

The wrapper already embeds the frontend at full available width. Without a
browser or the actual screenshot image, the reported clipping's exact cause
(viewport, sidebar state, or iframe layout) cannot be proven. These CSS changes
address identified shrink/wrapping risks; they are not a measured pixel-level
acceptance result. No overflow is hidden merely to conceal clipped controls.

## Live Data Smoke Checks

The current local services remained running; no backend restart was needed for
static frontend edits. Actual canonical requests returned HTTP 200, and their
responses were passed to the real frontend renderer in a DOM-stub harness:

| Case | Candidate | Rank | Coverage | Pair rows |
| --- | --- | --- | --- | --- |
| Single drug | Valsartan | 1 | 1/1 | Not applicable |
| Two drugs | Valsartan + Verapamil | 69 | 1/1 | 1 available |
| Requested three-drug example | Hydrochlorothiazide + Metformin + Timolol | 1 | 3/5 | 3 available |
| Partial ML | Acarbose + Chlorpropamide + Gliclazide | 467 | 1/1 | 1 available, 2 unavailable |
| Partial rules | Pravastatin + Acetylsalicylic acid | 21 | 2/2 | 1 available |

Every case was rendered in Simple and Researcher modes. For the three-drug
example, the selected IDs were Disease::DOID:14221, Disease::DOID:585,
Disease::DOID:6364, Disease::DOID:8398 and Disease::DOID:7148. This reproduces
the described drug set and coverage; it does not establish that these were
the screenshot's exact five selections. The partial-ML check used the existing
bounded maxCandidateSets=500 option for type 2 diabetes, without changing any
default or ranking logic. Fully evaluated rule behavior was verified with test
fixtures only; real mapping limitations were not bypassed to create a demo.

Fastify dependency health and Streamlit /_stcore/health passed. This is API and
renderer validation, not browser interaction. Browser connection returned
"No browser is available"; desktop/mobile screenshots are unavailable.

## Tests and Integrity

Frontend tests now cover structured sections, 3/5 coverage, covered/uncovered
diseases, three pair rows, unavailable reasons, all applicability states,
backend rank, collapsed details, source/version retention, escaping, mode
consistency, reset, long-name wrapping and stepper CSS contracts. Static CSS
tests cannot prove actual absence of overflow.

Validation: 92 backend/frontend tests passed (43 frontend tests); 105 ML tests
passed with six dependency deprecation warnings. Sprint 4 contract validation,
release metadata, both JavaScript syntax checks and git diff --check passed.
Frozen model SHA-256 remained
2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d;
feature-contract SHA-256 remained
a3adc02c91e1af0cf47d978c3c87d47b22f696edc7f797dc24a14ad246328efa.

Only frontend files, frontend tests and this note changed. No backend endpoints,
graph queries, ranking, optimization, inference, mapping data, model artifacts
or feature contracts were modified. No final evaluation was run. Existing
scientific and public-deployment limitations remain unchanged.

## Manual Review

Open http://127.0.0.1:3002 and http://127.0.0.1:8503. Repeat the five-disease
selection above, then inspect the first candidate. Confirm coverage 3/5, two
uncovered diseases discoverable, Not fully evaluated rules, three separate pair
rows and the rank explanation. Expand graph/rule/model/ranking details and
switch modes without losing selection. Try a single drug and a partial result;
reset during analysis and after selection.

Check desktop, laptop, tablet and 320px/375px mobile widths, both directly and
inside Streamlit. All four step controls and mode controls must remain reachable,
long names must wrap, and prediction labels must not overlap. Verify keyboard
focus, details expansion, contrast, browser console and absence of page-level
horizontal clipping. Visual/browser acceptance remains manual.
