# Sprint 6 Availability Diagnosis and Remediation

Date: 2026-10-16 (Asia/Manila). Research prototype, not clinical validation.

## Repository and Runtime

Started clean on `sprint6/jared/performance-guided-ux`,
`7cd8158abfbc812341e6df168b552300e9d83a30`, after fetching origin.
Created `fix/polymerge-availability-and-rule-mapping` from that HEAD.
No shared graph mutations, public deployment, PR, merge or security bypass.

Initial identified processes: FastAPI PID 12529 on 8000, Fastify PID 12554 on
3002, Streamlit PID 98428 on 8503. Neo4j was listening through Docker on
7474/7687. Only FastAPI/Fastify were restarted. Other applications, older
PolyMerge ports and the Streamlit process were left alone.

## Reproduction

`scripts/diagnose_availability.py` records actual canonical responses, detailed
explanations, per-candidate unsupported pairs and read-only graph inventory.
It never reads evaluation rows or writes to Neo4j. Evidence is stored locally
under /tmp/polymerge-availability-baseline and /tmp/polymerge-availability-verified.
Earlier investigation runs are in /tmp/polymerge-availability-diagnosis-before
and /tmp/polymerge-availability-after. These temporary artifacts are not tracked.

| Scenario | Actual disease IDs | Candidates | Single drug | Fully predicted multi-drug | Unsupported multi-drug | HTTP search/explain |
| --- | --- | --- | --- | --- | --- | --- |
| Hypertension | Disease::DOID:10763 | 100 | 68 | 32 | 0 | 200/200 |
| Hypertension + type 2 diabetes | Disease::DOID:10763, Disease::DOID:9352 | 100 | 4 | 93 | 3 | 200/200 |
| Coronary artery disease + atherosclerosis | Disease::DOID:3393, Disease::DOID:1936 | 100 | 6 | 94 | 0 | 200/200 |
| Osteoarthritis + rheumatoid arthritis | Disease::DOID:8398, Disease::DOID:7148 | 0 | 0 | 0 | 0 | 200/200 |

All nonempty scenarios have real_graph evidence and coverage 1.0 for every
returned candidate. The optimizer's selected sets/drugs and represented disease
coverage are unchanged. Full responses contain the exact optimizer choices;
automated comparison asserts equality, not just equal counts. Before and after
all returned candidates have legacy status accepted (no exclusion triggered),
which does NOT mean rules are evaluable or that any candidate is safe.

The three unsupported default pairs all contain Compound::DB00177 (Valsartan),
paired respectively with Compound::DB00796 (Candesartan), Compound::DB00903
(Ethacrynic acid), or Compound::DB01120 (Gliclazide). Those latter identifiers
have no exact reviewed entry in the checked-in DDInter-Hetionet bridge. Their
names also do not occur in that bridge file. No alias/salt/class guesses were
introduced. The model itself is ready and classifies supported pairs normally.

## Unavailable-State Inventory

Classification numbers correspond to the task's eight cause categories.

| Location/state | Root cause and classification | Resolution / remaining behavior |
| --- | --- | --- |
| Single-drug candidate prediction | Expected no pair (1) | Main flow remains Not applicable; explanation API/legacy renderer repaired to match |
| Multi-drug prediction in default two-disease query | Three missing reviewed drug mappings (4) | Prediction unavailable with reasonCode, exact pair and missingDrugIds; no invented class |
| Multi-pair candidate with one failing pair | All-or-nothing exception handling erased successful predictions (7, underlying 4) | Retain successful pairs and unavailablePairs; status partial |
| Rule badges, narrative, technical pipeline and summary | Canonical IDs did not match literal rule tokens; accepted was mistaken for completed checks (3, 7) | Structured coverage and no passed/safe interpretation of missing mappings |
| Rule explanation/comparison API | Unconditionally synthesized accepted rule detail (7) | Precomputed evaluated/partially_evaluated/not_evaluable state; no rerun in presentation |
| Global rule warning | Incomplete mapping and unreviewed hard-exclusion semantics (3, 8) | Concise research-only limitation retained |
| Empty candidate list for osteoarthritis/rheumatoid arthritis | Nodes exist but no CtD edges in fragment (2) | Explicit no represented treatment connections; not a model outage |
| Graph retrieval/mapping/ranking workflow with no candidates | Same absent treatment data (2) | Honest unavailable stage, no fabricated candidates |
| Candidate graph/path panels or visualization without paths | Absent represented evidence (2); missing graph button could also throw (7) | Preserve empty evidence; guard optional visualization button |
| Gene/side-effect paths absent for a particular drug | Fragment/context coverage limitation (2) | No synthetic paths; absence is not proof of no side effects |
| Catalog unavailable/retry | Dependency/API failure path (6) | Not reproduced in healthy runtime; existing retry retained |
| Graph unavailable/search unavailable | Neo4j/service failure, invalid upstream response or busy admission (6) | Existing explicit fallback/error/busy behavior retained and regression-tested |
| Unsupported pair / absent feature sources | Bridge/feature-source gap (4) | Separate missing_drug_mapping, missing_feature_source, unsupported_pair codes |
| Model unavailable | Missing/corrupt/unverified artifact (5) | Model error remains distinct, tested with injected failure; not observed live |
| Feature validation / inference errors | Invalid frozen feature vector or failed model execution (6) | Distinct feature_validation_failure and inference_error; no fallback severity |
| Explainability unavailable | Missing history, failed endpoint or rendering error (6/7) | Actual explain requests pass; partial/single handling and optional button repaired |
| Model comparison endpoint warning | API/report unavailable (6) | Preserved checked-in metrics fallback remains labeled; endpoint healthy live |
| Raw rank/version/provenance Not provided fallbacks | Missing response metadata (6/7) | Not reproduced in live canonical responses; never filled with invented values |
| Clinical safety, efficacy, dosage, formulation or comprehensive DDI assessment | Unsupported research capabilities (8) | Remain unsupported; no combined score or clinical conclusion |

The initial symptoms were not a general outage. Live HTTP checks and service
logs showed successful canonical requests; unavailable feature cases were
handled responses, not server crashes. Browser rendering could not be observed:
the browser runtime returned no browser and its browser list was empty.

## Rule Mapping and Scientific Scope

Python and JavaScript now consume one versioned definition/mapping artifact:
`data/rules/research_rule_mapping.json`. Canonical Compound::DB identifiers and
bare DB identifiers normalize deterministically; arbitrary names do not map.
Both runtimes implement the same small evaluator, checked by a parity test.

Verified positive fact: live Neo4j and the checked-in fragment both contain
Pharmacologic Class::N0000175721 (Nonsteroidal Anti-inflammatory Compounds)
--PCiC--> Compound::DB00945 (Acetylsalicylic acid). The rule token is nsaid.
The [DailyMed aspirin label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=815a70e4-525c-4015-8d3b-83dbb979a66f)
also identifies aspirin as an NSAID. This corroborates the category, not a
universal absolute contraindication. The label describes bleeding warnings
with anticoagulants; that does not establish unconditional hard-exclusion
semantics across all formulations, doses and clinical contexts.

Graph source: Hetionet v1.0 filtered PolyMerge fragment. Mapping version:
polymerge-research-rules-2026-10-16-v1. Edge snapshot SHA-256:
`4e7b459c93743548041cb370e43ddfc1c7f4d495e71447de3d74b1e58ae9e1c1`.
One of 299 fragment compounds has a verified positive configured-category
mapping; **zero have comprehensive membership/nonmembership coverage**. There
are 37 pharmacologic classes and 91 PCiC edges, but these do not supply the
missing MAOI, SSRI, warfarin, ACE-inhibitor and potassium-sparing category
coverage needed by the configured rules. Related mechanism/class names are
not silently treated as equivalents. Warfarin is absent from the fragment.

The three existing exclusion definitions remain research_only and explicitly
clinicallyValidated: false. Their legacy API type name hard_contraindication
is retained for compatibility, but displayed messages say research exclusion.
Positive facts may trigger a configured research condition; absence of an edge
never proves negative membership. Legacy literal tokens remain supported as
explicit category inputs for regression fixtures, not canonical drug mappings.

Rules are evaluated only when both positive conditions are established or all
inputs are explicit legacy tokens. Partial positive coverage is reported as
partially_evaluated; no usable mappings as not_evaluable. Each response includes
per-rule status, identities, sources, mappingVersion and unmappedDrugIds.
Candidate generation, backend validation and optimizer use the same definitions.
The optimizer checks proposed merged unions and reports the final union's
coverage. The legacy no-coverage optimizer path now also checks the union.

| Rule coverage | Before | After |
| --- | --- | --- |
| Hypertension, 100 candidates | Unreported; displayed as passed | 100 not_evaluable |
| Two diseases, 100 candidates | Unreported; displayed as passed | 100 not_evaluable |
| Alternative pair, 100 candidates | Unreported; displayed as passed | 96 not_evaluable, 4 partially_evaluated |
| Fully evaluated real candidates in these scenarios | Not established | 0 |

Required next data review: a versioned canonical-ID-to-identity/category table
with row-level authoritative sources, explicit category scope and negative
coverage where claimed; independent domain review of each exclusion's clinical
conditions and evidence. Verify identity/salt/form equivalence before adding
rows, record provenance/version, and run Python/JS/optimizer parity tests.
Do not populate classes from names, similarity, graph absence or ML severity.

## ML Availability Repairs

Prediction runs per supported unordered pair. Both success and failure outcomes
are cached only within the current request. Successful pairs survive another
pair's failure. unavailablePairs contains reasonCode/reason/missingDrugIds and
never a severity. Status is applied, partial or not_applied; a single drug has
reasonCode not_applicable. Backend validation checks partial pair coverage,
membership, duplicates and unsupported probability/confidence fields. The
explanation adapters and both renderers retain the exact per-pair distinction.

Feature source I/O/schema failures now become explicit missing_feature_source
outcomes rather than escaping as an undifferentiated request failure. Missing
drug IDs are identified by the reviewed bridge. Model load, model inference,
feature validation and unsupported-pair errors remain distinct. No model or
feature mapping rows were added, and no missing molecular structures were
fabricated. Existing frozen missingness/imputation semantics are unchanged.

Default pair availability counts are unchanged: 32, 93 and 94 applied pairs in
the three nonempty scenarios; exactly three missing pairs in the two-disease
case. The bridge has 227 exact_name rows and 1,712 unmapped rows. That is dataset
mapping coverage, not a claim of 227 verified rule/category identities.

A live bounded diabetes-only request with maxDrugCount=3 and maxCandidateSets=500
returned 500 candidates in 1,581.614 ms: 456 applied, 1 partial, 43 not_applied
(22 single-drug and 21 unsupported two-drug candidates). The partial triple
contains Compound::DB00284, Compound::DB00672 and Compound::DB01120: the first
pair has an actual Moderate prediction; the two pairs involving DB01120 lack
the reviewed bridge. Its detailed explanation also reports partial. Under the
previous all-or-nothing implementation that triple would have discarded the
successful pair. This latter before-state is a code-path inference, not a
recorded pre-fix 500-candidate response. A 300-candidate probe contained no
partial triple, so it was not used as partial-success evidence.

## Integrity and Performance

The diagnostic comparator recursively compares complete baseline and after
canonical JSON, excluding ONLY queryId, timestamp and the added ruleEvaluation,
reasonCode, unavailablePairs, missingDrugIds fields. All four default scenarios
pass. Candidate IDs, rank order, represented coverage, graph paths/provenance,
optimizer choices, original supported classes and all other fields match.
The partial fixture test additionally preserves rank and graph evidence.

Sequential diagnostic timings (one observation per cell, not benchmark medians):

| Scenario | Before ms | After ms |
| --- | --- | --- |
| Hypertension | 896.363 | 933.346 |
| Two diseases | 1070.572 | 1212.258 |
| Alternative supported pair | 914.306 | 879.985 |
| No CtD pair | 17.534 | 17.517 |

An earlier after smoke overlapped regression work and took 1,743/1,349 ms for
one/two diseases; these are not used to infer steady-state changes. Added rule
resolution has some cost but the earlier performance gains remain. No strict
machine-dependent timing assertions were added.

Frozen model version: RandomForestClassifier-sprint5-v1-65e9834666ad19c5.
Artifact SHA-256 unchanged:
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
55-feature contract SHA-256 unchanged:
`a3adc02c91e1af0cf47d978c3c87d47b22f696edc7f797dc24a14ad246328efa`.
No frozen-model training/tuning, final evaluation or test-set prediction.
The requested contract validator inspects schema/split metadata only. Existing
unit tests use tiny synthetic model fixtures; they do not retrain the deployment
artifact or recompute reported metrics.

## UX and Acceptance

The four-step flow, Simple/Researcher modes, five-card pages, next/previous,
reset and stale-response protection remain. Switching modes uses the same
response, without analysis requests. Simple outcomes distinguish single-drug
Not applicable, Prediction available, Partial predictions available and
Prediction unavailable. Research details expose actual unsupported pairs,
missing IDs, mapping coverage, source/version and preserved graph/model evidence.
No CrC relation is presented as DDI evidence. Model Analysis metrics unchanged.

Manual review URLs:
- Frontend: http://127.0.0.1:3002
- ML liveness/model readiness: http://127.0.0.1:8000/health and /health/model
- Streamlit: http://127.0.0.1:8503

Follow [guided demo acceptance](../sprint6-guided-demo.md), then inspect a
single-drug and supported multi-drug candidate, the three unsupported default
pairs, and the alternative pair's aspirin-containing candidates. Compare modes;
confirm partial/insufficient rules are not green passed checks. For the larger
500-candidate diabetes response inspect the partial triple above through the
canonical API/detailed explanation. Reset during a request and after selection;
confirm no stale result reappears. Verify keyboard, mobile wrapping, contrast,
console and iframe interaction manually. Browser automation remains unavailable.

## Validation and Remaining Work

Local backend/frontend tests: 86 passed (including 37 frontend static/DOM tests).
ML tests: 105 passed, six dependency deprecation warnings. Source-only CI skips
the real-artifact integration test when the deployment artifact is absent;
mocked partial-pair contracts still run. Contract validator and release metadata
checks pass; all five script tests pass. JavaScript syntax, YAML parsing and diff
checks pass. Added tests
cover canonical normalization, verified positive category evidence, unknown
IDs, incomplete rules, merged optimizer rejection, partial predictions, real
missing IDs, model/inference/validation errors, API validation, explanation
status, mode consistency, escaping and no fabricated scores.

Both affected container images build and import the shared mapping successfully.
Live deployment smoke passes static assets, catalog, dependencies, model
comparison, ML/model health, Streamlit HTTP/health and the two-disease query.
The wrapper HTTP check does not establish visual iframe acceptance.

CI remains enabled, including this fix branch, with security gates unchanged.
Existing dependency advisories (including two high npm findings), unauthenticated
shared history, incomplete rule/clinical evidence and browser acceptance still
block public deployment. Combinatorial limits and per-process admission remain
prototype resource risks. Genuine graph/mapping gaps cannot be repaired by
substituting reassuring text or synthetic predictions.

## Changed Surfaces

- Shared rule evidence: data/rules/research_rule_mapping.json.
- Python rule/generation/optimization: ml_engine/app/services/safety_filter.py,
  candidate_generator.py, set_cover_optimizer.py.
- Pair availability: ml_engine/main.py, ml_engine/app/services/ddi_feature_builder.py,
  model_serving.py. Frozen artifact/data contract files are untouched.
- Backend validation/rules/explanation: backend/src/server.js,
  rules/contraindications.js, explainability/types.js, explainability/presentation.js.
- Frontend: frontend/app.js, explainability.js, index.html, styles.css.
- Tests: backend/tests/availability.test.js, contraindications.test.js,
  explainability.test.js, frontend-static.test.js; ml_engine/tests/test_availability.py
  and test_performance_contracts.py.
- Runtime packaging/CI: deploy/Dockerfile.backend, deploy/Dockerfile.ml,
  .github/workflows/ci.yml (branch trigger only; gates unchanged).
- Diagnosis/documentation: scripts/diagnose_availability.py, README.md, this audit.
