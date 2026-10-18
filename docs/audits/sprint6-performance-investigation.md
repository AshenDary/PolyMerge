# Sprint 6 Performance and Guided UX Follow-up

Date: 2026-10-15. Local research prototype; not a public-release approval.
Started clean on `sprint6/jared/final-audit-cicd` at
`73a2925a7a795c2409cdd1fa26590e365ceb2e4a`; origin/main was
`2edcc39bfe83296b00020e9d7894aa3d95889754`.
Work branch: `sprint6/jared/performance-guided-ux`. No merge, PR or deployment.

## Method

Measured the actual canonical POST /api/candidate-sets/search through Fastify,
using local Neo4j and the frozen model. Three sequential runs each of catalog,
hypertension (Disease::DOID:10763), and hypertension plus type 2 diabetes
(Disease::DOID:9352), before and after on the same machine and dataset.
Repeated two-disease runs cover repeat-request behavior; no response cache added.
`scripts/benchmark_candidate_api.py` records monotonic HTTP durations and real
responses. `scripts/profile_ml_service.py` is an opt-in localhost profiler with
UUID request-scoped ContextVar records, monotonic stage durations and counts.
It does not log configuration or response payloads. Nested stage timings are
inclusive and must not be added together.

Raw local evidence: /tmp/polymerge-perf-before, /tmp/polymerge-perf-after,
/tmp/polymerge-baseline-stages.jsonl, /tmp/polymerge-optimized-stages.jsonl,
and /tmp/polymerge-query-plans.json. These temporary files are not committed.
Use the first six candidate requests per profile for the matched comparison;
later requests are responsiveness experiments. Startup-not-ready attempts were
excluded from steady-state measurements. Baseline peak RSS was not captured;
no measured peak-memory reduction is claimed. Browser render/paint latency was
not measurable without an available browser. Backend/transfer overhead below
is a residual, not an isolated JSON serialization or network measurement.

## End-to-end Results

| Scenario | Before min / median / max ms | After min / median / max ms | Median reduction |
| --- | --- | --- | --- |
| Catalog | 10.349 / 13.663 / 79.514 | 5.440 / 5.929 / 43.933 | Cache/runtime variation; not attributed |
| One disease | 19541.081 / 20147.848 / 20190.121 | 847.266 / 925.607 / 1082.046 | 95.406% |
| Two diseases | 57883.215 / 57893.834 / 58628.046 | 1042.601 / 1051.950 / 1079.505 | 98.183% |

All local latency targets were met. These are observations, not production SLAs.

## Stage Comparison

Matched median milliseconds; B/A means before/after. Delta uses two-disease case.
All scientific-output comparisons passed, including graph paths and pair classes.

| Stage | One disease B/A | Two diseases B/A | Two-disease change | Correctness |
| --- | --- | --- | --- | --- |
| Neo4j + graph construction | 131.949 / 101.224 | 126.533 / 117.198 | -9.335 | Exact |
| Candidate generation | 1344.124 / 92.383 | 2793.014 / 152.625 | -2640.389 | Exact |
| Greedy optimization | 0.127 / 0.132 | 0.139 / 0.139 | 0.000 | Exact |
| Feature builder initialization | 18064.393 / 566.135 | 54622.987 / 553.592 | -54069.395 | Exact |
| Pair vector assembly | 1.860 / 1.324 | 5.779 / 3.704 | -2.075 | Exact |
| RF classifier prediction | 39.571 / 31.897 | 114.517 / 96.062 | -18.455 | Exact |
| Validated inference, inclusive | 79.369 / 61.539 | 228.264 / 180.105 | -48.159 | Exact |
| HTTP minus ML request residual | 29.668 / 15.147 | 46.671 / 17.127 | -29.544 | Exact |
| Total HTTP | 20147.848 / 925.607 | 57893.834 / 1051.950 | -56841.884 | Exact |

Additional inclusive stage medians (one B/A; two B/A), milliseconds:

| Stage | One | Two |
| --- | --- | --- |
| Disease validation | 5.166 / 3.678 | 4.469 / 4.936 |
| Treatment retrieval | 11.896 / 4.984 | 6.961 / 5.664 |
| Gene context | 49.722 / 44.797 | 56.679 / 53.784 |
| Side-effect context | 46.294 / 43.491 | 54.807 / 49.295 |
| Initial graph path aggregation | 2.573 / 2.735 | 3.508 / 3.334 |
| Candidate path aggregation | 379.726 / 0.231 | 896.600 / 0.344 |
| Rules | 32.542 / 27.807 | 65.503 / 56.546 |
| Ranking | 0.111 / 0.061 | 0.195 / 0.057 |
| ID mapping load | 78.519 / 2.856 | 219.859 / 2.538 |
| Structure mapping load | 315.237 / 10.266 | 959.969 / 9.733 |
| Graph feature lookup build | 17521.872 / 541.774 | 53018.547 / 537.009 |
| Pair graph features | 0.947 / 0.732 | 2.774 / 2.018 |
| Pair molecular descriptors | 0.275 / 0.126 | 0.945 / 0.351 |
| Preprocessing | 23.783 / 17.169 | 69.502 / 48.775 |
| Prediction pipeline | 64.105 / 49.111 | 185.144 / 144.669 |
| ML framework/validation residual | 12.716 / 13.622 | 20.481 / 17.836 |

## Bottlenecks and Changes

Repeated PairFeatureBuilder initialization dominated: 32 and 93 initializations
rebuilt the same graph feature lookup. One request-local builder now serves all
supported pairs. Successful predictions are reused by unordered pair within
that request only. The measured scenarios have 32/93 unique pairs, so pair-cache
hits do not explain their speedup. No cross-request cache or stale-version reuse
was introduced. Model, graph and mapping inputs are assumed immutable during a
single request. Unsupported candidates retain existing all-or-nothing behavior.
Existing molecular descriptor caching is unchanged. Inference is still validated
one pair at a time; batching was not justified by the small measured inference
cost and would require a separate validated contract.

Candidate generation previously materialized and sorted every combination.
An exact nsmallest top-K selection now scans all combinations using the same
rule/coverage/size/ID ordering and materializes evidence only for winners.
There is no random cutoff, input truncation, approximate pruning or reranking.
Memory retained for selection is bounded by K; CPU enumeration is still
combinatorial and high configuration limits remain a resource-exhaustion risk.

| Counts, unchanged before/after | One disease | Two diseases |
| --- | --- | --- |
| Compounds | 68 | 86 |
| Combinations considered | 52462 | 106081 |
| Returned candidates | 100 | 100 |
| Applied pair occurrences | 32 | 93 |
| Fully materialized before/after | 52462 / 100 | 106081 / 100 |
| Feature builder initializations before/after | 32 / 1 | 93 / 1 |
| Response bytes | 1362206 | 2099036 |

The synchronous pipeline blocked FastAPI's event loop. It now runs in a worker
thread behind a nonwaiting process-local semaphore admitting one analysis.
Canonical and legacy analyses share this guard. Excess requests receive 503
and Retry-After: 2; Fastify preserves this as busy, not missing graph evidence.
The slot releases when work finishes, including exceptions and client aborts.
No unlimited queue, new model copies, distributed queue or fake cancellation.
Multiple deployment processes would each have their own slot and model memory.

## Neo4j Findings

`scripts/profile_graph_queries.py` uses parameterized read-only queries,
EXPLAIN and bounded PROFILE (5-second timeout), plus schema inspection.
Only two token lookup indexes existed; no property indexes or constraints.
Representative first-template plans (not whole-request totals):

| Query | Calls (two diseases) | PROFILE rows | DB hits | Available / consumed ms | Plan |
| --- | --- | --- | --- | --- | --- |
| Disease resolve | 2 | 1 | 7 | 35 / 7 | Label scan, filter, limit |
| Treatments | 1 | 86 | 776 | 16 / 4 | Label scan, expand, filter, aggregation, sort |
| Gene context | 86 | 5 | 1202 | 12 / 2 | Compound label scan, expand/filter, top |
| Side effects | 86 | 5 | 1341 | 22 / 0 | Compound label scan, CcSE expand, top |

Context is fetched twice per compound, never once per candidate combination.
Each context output is limited to five; neighboring rows still require sorting.
Treatment aggregation and path deduplication preserve represented relationships.
The request constructs a GraphService/driver and query sessions; connection
lifecycle/reuse was not optimized here. Graph query time did not dominate.
No graph mutation occurred. See the separate
[index review plan](../deployment/NEO4J_INDEX_REVIEW.md) before any schema change.

## Correctness and Model Integrity

Compared all three after responses in each disease scenario recursively with
the corresponding baseline, excluding only queryId and timestamp. All remaining
fields matched: candidate IDs, ranks, coverage, reasons, graph provenance/paths,
optimizer choice, supported pair classes, statuses and model version.
Seeded fixture tests also compare exact heap output with exhaustive enumeration
and optimizer results, including configured rule rejections and duplicate IDs.
Real feature vectors match independent builder vectors in both pair directions.
Cache tests cover deduplication, unsupported pairs and fresh request isolation.

Frozen 55-feature contract unchanged. No training, tuning, final evaluation,
test-set prediction, new scores or drug-class mappings were performed. The
requested contract validator inspected split/schema metadata, not final model
evaluation. Model version: RandomForestClassifier-sprint5-v1-65e9834666ad19c5.
Artifact SHA-256 before and after:
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.

## Health and Reset

Before: dependency health timed out with 503 after 5004.506 ms during analysis;
after client abort it similarly failed after 5011.345 ms until work completed.
After: during a two-disease request, /health 200 in 5.933 ms,
/health/model 200 in 2.632 ms and /api/diseases 200 in 6.947 ms.
Abort after 100 ms produced client AbortError; health stayed 200 in 5.607 ms,
and another analysis received 503 while abandoned server work continued.
Health was still 200 after completion. Liveness does not assert dependency
readiness; dependency and model readiness remain separately exposed.

Reset aborts the browser request, invalidates stale success/errors, clears all
selection/results/evidence/timers and returns to step 1. Display mode persists.
It does not claim to cancel Python/Neo4j work already running.

## Guided UX

Four steps: Select Diseases, Analyze, Review Candidates, Understand Result.
Default Simple View uses a compact summary, five ranked candidates per page,
next/previous five, human names, a four-sentence grounded explanation and CtD
treatment connections. Researcher View reuses the same response and selection,
revealing technical pipeline, IDs, provenance, graphVersion, supported context
relations, pair predictions, model version and optional all-results display.
Failures remain visible outside collapsed details. No CrC-as-DDI evidence.
The rule-ID limitation stays visible; untriggered rules do not imply safety.
Model Analysis retains all original metrics/assets with shorter default copy.
Focus semantics, keyboard buttons and long-ID wrapping are implemented; actual
contrast, responsive layout, rendering and iframe acceptance remain unverified.

## Validation and Remaining Blockers

- Backend: 81 tests passed, including 35 frontend static/DOM tests.
- ML: 89 passed, five existing httpx deprecation warnings.
- Sprint 4 contract validator: PASS; release metadata: PASS; script tests: 5 PASS.
- JavaScript syntax checks: PASS. CI trigger includes this branch; security
  checks are unchanged. Local actionlint is unavailable; remote CI is authoritative.
- Restarted local deployment smoke: all assets, health, catalog, model comparison,
  Streamlit HTTP/health and real two-disease query PASS (query 1381 ms).
- Subsequent sequential canonical smoke: one disease 832.381 ms, two diseases
  1110.520 ms, both 100 candidates and respectively 32/93 applied pairs. An
  overlapping smoke attempt received the expected busy 503 and was retried
  sequentially; it is not included in steady-state performance measurements.
- Browser tool: no browser available. Desktop/laptop/tablet/mobile screenshots,
  contrast, console and actual iframe interaction are PENDING manual review.

Existing unauthenticated shared history, dependency advisories and rule-ID mapping
remain unresolved. No clinically reviewed class mapping was introduced. Moving
analysis off the event loop resolves the demonstrated health starvation, not all
CPU/DoS risks. Large evidence responses, graph N+1 queries, driver lifecycle and
high combinatorial limits remain future engineering work. Public release stays
blocked. Follow [manual acceptance](../sprint6-guided-demo.md) before UX approval.
