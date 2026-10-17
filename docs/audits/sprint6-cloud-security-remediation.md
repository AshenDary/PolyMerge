# Cloud Security Remediation

Review date: 2026-10-18, Asia/Manila. Status: **release blocked**.

## Final Container Follow-up

The subsequent review at code commit `3b5a355` is documented in
[Final Container Security Review](sprint6-final-container-security-review.md).
Pinned Trixie bases replace Bookworm without changing Python/Node major versions
or scientific dependencies. Current local scan counts are 43 HIGH / 0 CRITICAL
for backend and 44 HIGH / 0 CRITICAL each for ML/Streamlit, down from 57/63/63.
Those remaining findings are not waived, and scanner DB freshness has a documented
limitation. Exact package evidence is in the linked report and CSV.

Patched sklearn 1.5.2 matches 313 numerical probe rows exactly but has estimator
version warnings and a concrete ColumnTransformer API incompatibility. Production
remains 1.4.0; its advisory is unresolved. Backend tests now total 122; script tests
13; local ML remains 127. Hardened read-only/non-root restart checks were added.
The original investigation below is retained as historical evidence, not current
container counts. No merge or cloud action occurred.

## Starting Point

PR #57 remains open against main. Main was verified at
`2edcc39bfe83296b00020e9d7894aa3d95889754`; integration HEAD was
`d0a8df3b50d460ef5fd7cb59851338172e9c15ee` (25 ahead / 0 behind).
The clean integration branch was used to create
`fix/pre-deployment-security-and-cloud`. No prior implementation was discarded.
No main merge, cloud provisioning, external artifact upload or graph import occurred.

## Changes

- Fastify 5.12.1 -> 5.12.7; fast-uri transitive patches; rate-limit 11.2.1.
  Fresh npm production audit: zero findings. No forced dependency upgrades.
- FastAPI 0.109.2 -> 0.143.3, Starlette 0.36.3 -> 1.8.0,
  dotenv 1.0.1 -> 1.2.2, Pydantic 2.6.1 -> 2.12.5,
  pytest 8.3.4 -> 9.0.3 (development only). NumPy is pinned at 1.26.4.
- Streamlit is pinned at 1.66.0 in its independent environment. Runtime,
  development and wrapper dependency sets have hash-locked resolutions.
- Shared history storage is removed entirely, in every environment. History,
  query-ID retrieval and explanation-ID retrieval return 404. There is no history
  collection to grow, expire or disclose. Current simulation explanations,
  graph visualization and Research Takeaway are computed from browser state.
- Anonymous research-demo architecture: no browser-visible API key, no cookies,
  no login/session claims. Only catalog/model-report and bounded canonical
  candidate analysis are intended as public research APIs. CORS is not authentication.
- Default limits: 120 requests/minute/client, six analyses/minute/client,
  one active analysis per backend, 32 KiB body, 15-second request reception,
  bounded upstream timeouts. ML retains admission until computation ends.
  Rate caches are bounded; deployment stays at one instance. Distributed limits
  and edge abuse protection need review before scaling or high-traffic exposure.
- Public demo candidate settings are capped at three drugs / 100 returned sets.
  A 250,000-combination work budget rejects oversized searches before enumeration;
  it never silently truncates or changes the order of supported requests.
- Forwarded IP headers are not trusted by default. `TRUST_PROXY_CIDRS` must
  contain only provider-confirmed proxy CIDRs if enabled. Until verified, quotas
  may conservatively aggregate visitors behind the proxy. Never set trust-all.
- Exact CORS origins, no credentials or reflection; production origins require
  HTTPS. CSP defaults to self, disables scripts from other origins and object
  embedding, and permits framing only by `STREAMLIT_ORIGIN`; unset means none.
  No third-party authentication cookie is required. Actual browser embedding is pending.
- Production blocks legacy catalog/demo interaction/search and raw DDI proxy
  routes even if `POLYMERGE_ENABLE_LEGACY=true`. Legacy tests opt in only outside
  production; canonical `/api/candidate-sets/search` remains graph-backed.
- Upstream failures and model availability errors no longer disclose model paths
  or raw exceptions. Backend diagnostics use error codes/request IDs, not raw
  upstream messages. Private ML rejects browser origins and has no Swagger routes.
- `/ready` verifies model/graph readiness separately from `/health` liveness.
  ML must be a Render private service, not a public service with CORS restrictions.
- Images pin base digests, run as non-root and do not contain the model. Backend
  Perl was patched to `5.36.0-7+deb12u4`; unused npm/Corepack/Yarn and Python
  packaging tools are removed from runtime images after installation.
- CI now runs for PRs targeting the integration branch and separately audits
  each Python environment. Runtime container vulnerability scans were added;
  failures are not ignored and no advisory suppression list was introduced.

## Frozen Model Decision

Artifact SHA-256 remains
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
Original provenance: Python 3.9.6, scikit-learn 1.4.0, 55 features.
No retraining, tuning, replacement or final held-out evaluation occurred.

Seven deterministic inference probes (five graph-derived pairs, zero and missing
feature rows) have exactly matching classes and probability arrays on the old
environment, updated Python 3.11 environment and Linux ARM64 image. The probes do
not read held-out test rows. The five live scenarios preserve all candidate and
optimizer payloads exactly, including 473 Moderate, six Minor and six Major
returned pair predictions across the four nonempty scenarios (not unique pairs).

An isolated scikit-learn 1.5.0 attempt raises `InconsistentVersionWarning` while
loading the frozen SimpleImputer. The compatibility probe treats that warning as
an error. This does not prove every prediction would differ, but compatibility is
not established. Runtime now fails closed on a provenance-version mismatch.

`PYSEC-2024-110` / `CVE-2024-5206` remains in ML and development audits.
It concerns token retention in TfidfVectorizer, not Random Forest inference.
The frozen pipeline uses numeric imputation/scaling and Random Forest, with no
TF-IDF estimator, text-training route, model upload endpoint or artifact download
endpoint. Trusted checksum-verified loading and private-network deployment are
compensating controls, not a claim that the vulnerable package was patched.
**Reviewer approval is required for any scoped acceptance; CI still fails.**

Sources: [advisory](https://github.com/advisories/GHSA-jw8x-6495-233v),
[unsupported cross-version persistence](https://scikit-learn.org/stable/model_persistence.html).

## Container Findings

Docker Scout was unavailable without login. Local Trivy 0.76 scans ran against
actual runtime images, with HIGH/CRITICAL findings retained, including unfixed
findings. Reports are in `/tmp/polymerge-container-security/*-final.json`.
The backend was reduced from 75 package/advisory occurrences to 57 (12 unique
CVEs; one critical occurrence). ML initially had 65, reduced to 63 (16 unique
CVEs; two critical occurrences); Streamlit also has 63 / 16 / two respectively.
These counts are scanner occurrences, not proof
of remote exploitability. Remaining findings have no reported fixed version in
the scanned distribution. They require explicit applicability review or a
reviewed alternative runtime base; no blanket exception is approved.

This is distinct from ordinary scientific limitations: incomplete graph and
category mappings, partial predictions, and lack of clinical validation remain
explicit and unchanged. No clinical safety or therapeutic synergy is asserted.

## Audit Commands

Use Python 3.11 and `pip-audit==2.9.0`:

```sh
npm --prefix backend audit --omit=dev
pip-audit -r ml_engine/requirements.lock
pip-audit -r ml_engine/requirements-dev.lock
pip-audit -r requirements-streamlit.lock
```

The original combined `pip-audit -r ml_engine/requirements.txt -r
requirements-streamlit.txt` was also attempted. It cannot resolve the ML-pinned
Uvicorn and Streamlit's newer Uvicorn constraint together. They run in separate
containers, so separate audits accurately represent deployment, rather than
silencing an audit. ML/development each report the one scikit-learn advisory;
Streamlit reports zero. Historical Python 3.9 resolution had 39 advisories in
ten packages; Python 3.9 is not the proposed deployment runtime.
