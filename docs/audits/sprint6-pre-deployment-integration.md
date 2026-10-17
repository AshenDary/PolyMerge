# Pre-Deployment Main Integration Review

Date: 2026-10-17 (Asia/Manila).

## Review Request and Release Gate

Please review preservation of the validated research implementation and approve
the integration only through the normal main-branch review process. This is
**not public-deployment approval**. Security failures must not be bypassed.
Main is not synchronized until an authorized maintainer merges this PR and the
resulting remote main SHA is fetched and verified. No deployment source SHA has
been approved. No cloud resources, graph imports, model uploads or public
services were provisioned by this integration task.

## Repository and Histories

- Audited remote main: `2edcc39bfe83296b00020e9d7894aa3d95889754`.
- Validated development: `e90fde81f81c1cd6846e2fcf9285f950f973756c` on
  `fix/simulation-navigation-and-mapping-coverage`.
- Original main...feature comparison: **1 main-only / 23 feature-only commits**.
- Merge base: `8adf539a0bbd2fe4dea7844130c19eb6b8fe22fd`.
- Main-only commit `2edcc39` is the merge of PR #56, bringing the earlier
  Sprint 6 frontend workflow into main. Its tree is identical to its second
  parent, the merge base; there is no additional main-only patch to resolve.
- Created `integration/pre-deployment-main-sync` from remote main, then a normal
  non-fast-forward merge of the validated feature branch. Merge commit:
  `f00a23c259dabdb10b3e36441f5c9bf96a093053`.
- **No conflicts.** Both histories are preserved. The merge tree is exactly
  equal to development HEAD; only this integration report is added afterward.
- Initial worktree was clean and there were no open PRs. Every other fetched
  remote development branch and every other local development branch was an
  ancestor of the selected feature HEAD. No unique work required cherry-picking.

Incorporated ancestry includes `fix/polymerge-availability-and-rule-mapping`,
`sprint6/jared/performance-guided-ux`, `sprint6/jared/final-audit-cicd`,
`sprint6/jared/frontend-flow-repair`, and earlier graph, model-serving,
explainability, final-model-freeze and integration branches. Old experimental
branches were audited, not indiscriminately merged.

## Preserved Implementation

- Home and Model Analysis; four-step guided simulation with persistent Analyze,
  explicit Review action, completed-step navigation and selection-gated Step 4.
- Five-card pagination, Simple/Researcher modes, candidate-specific explanations,
  deterministic Research Takeaway, reset and stale-response protection.
- Performance improvements: bounded candidate materialization, per-request
  feature/prediction reuse and admission-controlled threaded analysis.
- Real Neo4j CtD coverage, canonical drug/disease IDs, provenance and path IDs.
- Frozen Random Forest multiclass Major/Moderate/Minor classification, the
  55-feature contract, partial-pair predictions and single-drug not-applicable.
- Nine reviewed positive category mappings in v2, explicit unknown/partial
  applicability, canonical research-exclusion triggers and optimizer union checks.
- Existing CI, private-loopback staging templates and non-root Dockerfiles.

No ranking algorithm, mapping fact, graph relationship, feature contract,
model artifact, paper result or presentation was changed during integration.
No therapeutic synergy, clinical safety or formulation viability is asserted.

## Local Verification

- Backend: **114 passed**, including **64 frontend behavioral tests**.
- ML: **116 passed**, six existing dependency deprecation warnings.
- Sprint 4 contract validator: PASS; 55 features and three target classes.
- Release metadata: PASS; seven script unit tests: PASS.
- app.js and explainability.js syntax, git diff --check: PASS.
- Mapping provenance, canonical-ID, unknown-membership, runtime parity and
  optimizer-union checks are included in the passing suites.
- Live graph: all **299 compound IDs/names** agree with tracked CSV, all nine
  reviewed mappings resolve, **142 CtD** and **91 PCiC** edges retained.
- Frozen model SHA-256:
  `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
  No retraining, retuning or final-model reevaluation performed.
- Backend, ML and Streamlit Docker builds PASS locally (Linux ARM64); each
  container becomes healthy without production secrets/model mounts or public
  port bindings. Temporary test containers were removed. This tests liveness,
  not container model readiness or cloud capacity.

Live scenario comparisons against the validated feature snapshots:

| Scenario | Candidates | Candidates with pair predictions | Partial / not-evaluable rules |
|---|---:|---:|---:|
| Hypertension | 100 | 32 | 19 / 81 |
| Hypertension + type 2 diabetes | 100 | 93 | 22 / 78 |
| Coronary disease + atherosclerosis | 100 | 94 | 20 / 80 |
| Four diseases | 100 | 100 | 28 / 72 |
| No represented treatments | 0 | 0 | 0 / 0 |

Every candidate payload and optimizer payload is exactly equal to the feature
snapshot, including rank, rules, evidence and pair predictions. No candidates
were added or removed by integration. Fully evaluated/rejected returned counts
remain zero; four-disease ML availability remains 98 applied / 2 partial.
Local evidence: `/tmp/polymerge-integration`, compared with
`/tmp/polymerge-nav-after` using `scripts/audit_rule_coverage.py`.

Live HTTP plus frontend-state/renderer checks verify Analyze remains active,
explicit review/selection, revisiting steps, preserved pagination, mode equality,
Research Takeaway and reset. Existing local services run the byte-identical
validated implementation. Streamlit HTTP health and AppTest iframe source
checks pass. Browser discovery reports **No browser is available**: desktop,
mobile, keyboard and actual iframe-rendering acceptance remain manual.

## Security Review: Public Deployment Blocked

- Fresh npm production audit: **2 high-severity vulnerable packages**, Fastify
  and fast-uri. No audit suppression or forced dependency upgrade was applied.
- Fresh isolated Python 3.9 requirement audit: **39 advisories in 10 resolved
  packages**, including scikit-learn, dotenv, pytest, Streamlit, Pillow,
  requests, Starlette, anyio, urllib3 and pyarrow. Hosted Python 3.11 may resolve
  different transitive versions; its separate CI outcome must also be reviewed.
- `/api/history` and query/explain retrieval use a shared unbounded process Map,
  without authentication, ownership checks or TTL. Public access risks query
  disclosure and resource exhaustion. JWT configuration is not authentication.
- No application-level rate limiter. ML's one-request admission bound does not
  replace authenticated quotas, history limits or an edge rate policy.
- Backend CORS defaults to reflected origins; ML defaults to wildcard origin.
  Configure exact origins and a reviewed embedding/CSP policy before exposure.
- Legacy drug interaction endpoints still serve demo scores, and legacy search
  retains fallback data. Disable/isolate them for public deployment.
- Some client-facing errors contain upstream details. Redact external errors
  while retaining protected server diagnostics.
- Root development Compose must not be used for public hosting. Existing
  staging Compose uses loopback bindings/private graph/model configuration;
  deployment workflow remains a disabled template with approval gates.
- Model deserialization requires a trusted private artifact, checksum verification
  and compatible runtime. Python dependency remediation needs frozen-artifact
  compatibility review; a scanner's fix list is not permission to retrain.
- Unpinned transitive dependencies, Streamlit range and base-image tags limit
  reproducibility; reviewed locks/digests remain release work.

These are release blockers, distinct from research limitations such as incomplete
class mappings and graph coverage. Scanner findings require applicability review;
they are not proof that every listed advisory is exploitable in this application.

## Hosted CI and Next Checkpoint

The existing workflow is unchanged. Opening the PR to main triggers regression,
security, and backend/ML/Streamlit build-and-liveness jobs. Actual hosted results
are reported on the PR and in the final handoff; this document does not predict
a green security result. No failing check is bypassed.

After authorized review/merge: fetch origin, switch main, fast-forward only,
verify ancestry and exact reviewed main SHA, rerun relevant checks, and record
that SHA as the deployment source. Until then, deployment is blocked pending
main integration as well as security and browser acceptance.

Only afterward prepare the Streamlit Community Cloud / Render Fastify / private
Render FastAPI / Neo4j AuraDB handoff against that reviewed main SHA. Billable
services, graph import, model upload and public activation each require separate
explicit approval. Existing deployment guides are preserved, not activated.
