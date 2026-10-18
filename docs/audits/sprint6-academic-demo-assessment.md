# Academic Demo Assessment

Superseded cost scope: the current request is strictly$0. See the
[free-tier assessment](sprint6-free-tier-feasibility.md). Paid proposals below
are historical alternatives, not authorized plans for the current task.

Date: 2026-10-18. **ACADEMIC DEMO BLOCKED - FUNCTIONAL OR SECURITY ISSUE**.
Temporary academic use is distinct from production readiness; it is not an
automatic acceptance of vulnerabilities or authorization for public exposure.

## Source and Authorization

Started clean on `fix/pre-deployment-security-and-cloud` at
`cda2835863f1e1774bfb4b142f29a9cc2ab6e215`. Fetched all branches.
PR58 remains OPEN against integration; PR57 remains OPEN against main.
Integration: `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`.
Main: `2edcc39bfe83296b00020e9d7894aa3d95889754`.
No merge, policy bypass, provisioning, external upload or graph import occurred.
**No proposed deployable main SHA exists yet.** The reviewed security candidate
is cda2835, not authorization to deploy that unmerged branch. Record the actual
post-merge main SHA and rerun acceptance before selecting a deployment commit.

## Verification Status

Fresh local tests: backend 125 passed; ML 133 passed with two existing dependency
warnings; scripts 13 passed; contract and release metadata checks pass.
Offline graph manifest again matches 3,415 nodes, 16,230 relationships and
299 compounds, with unchanged source hashes. This is not Aura verification.

The [last hosted run](https://github.com/AshenDary/PolyMerge/actions/runs/39059460054)
on unchanged application source passed regression, three image builds and
hardened startup/restart checks. Dependency and image security policies failed.
Fresh production-runtime probes again pass exact 313-row numerical parity and
five complete local candidate/optimizer snapshot matches (100/100/100/100/0
candidates). All three existing release-gates images passed hardened runtime
and restart tests again; images were not rebuilt in this documentation-only
checkpoint. No model, runtime, frontend,
research rule, optimizer, mapping, fixture, or scientific result changed here.
The model SHA remains
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
No held-out evaluation rerun.

Cloud ML, Fastify, Streamlit, Aura import, provider ingress, and live scenario
acceptance: **not performed**. No actual deployment URLs exist from this work.
Browser discovery returned no connected browsers; desktop, mobile, keyboard,
iframe authentication and cookie restrictions remain unverified.

## Temporary Risk Register

See the [complete CVE assessment](sprint6-final-release-gate-assessment.md) and
[package inventory](security-evidence/release-gate-scanner-inventory.json).
Trivy HIGH counts backend/ML/Streamlit: 43/44/44; Grype: 54/55/55; both zero
CRITICAL. Union 15 OS CVEs; sklearn PYSEC-2024-110 also remains. No compatible
patched scientific runtime was established. No scanner evidence was removed.

| Risk | Demo control proposed | Decision / approver / expiry |
|---|---|---|
| Privileged OS tools and absent components | Non-root, narrow runtime, reviewed component evidence | Pending / none / unset |
| glibc, GCC and disputed zlib native reachability | Finish native-path review; restricted audience is not a library fix | Pending; unresolved / none / unset |
| sklearn TF-IDF advisory | Fixed numeric inference, no user model loading or training; checksum/provenance guard | Pending narrow review / none / unset |
| Independently reachable anonymous backend | Approved authenticated gateway covering every application/API path and origin bypass | Not implemented / none / unset |
| Cross-site iframe authentication | Actual browser tests with third-party cookies blocked and fresh/expired sessions | Not verified / none / unset |
| Private service and graph boundary | Private Render service, verified Aura TLS, least-privilege runtime identity | Provider verification pending / none / unset |

**Accepted temporary risks: none.** Name an authorized reviewer and document
each accepted CVE, rationale, audience, expiry, compensating control and owner.
Do not record a generic request to deploy as informed risk acceptance. Do not
silently change branch protection; request separate repository-owner review for
any policy adjustment. Security checks must continue reporting their real result.

## Access Design Checkpoint

Prefer an approved identity-aware gateway with an explicit invitee allowlist,
short session lifetime and demo expiry. Provider/domain/audience are undecided.
The Streamlit wrapper must never contain a shared gateway/service credential,
and URLs must never carry bearer secrets. A private Streamlit app alone does not
protect the public Fastify origin.

Gateway setup is incomplete unless the original onrender.com endpoint and all
alternate hostnames reject unauthorized application/API access. Use verified
origin authentication or provider-supported origin restriction, not a client-
supplied header merely claiming authentication. Review issuer, audience,
signature, expiry and key rotation if application JWT validation is selected.
Do not implement a guessed provider contract before provider selection.

Test both iframe and direct fallback with fresh sessions, blocked third-party
cookies, expiry, logout, uninvited users, forged tokens and direct-origin bypass.
A top-level login can be offered only after testing; it does not guarantee
cross-site cookie availability. If embedding cannot authenticate reliably, do
not approve the requested Streamlit-first experience merely because fallback
works. Never relax CSP or remove authentication to make the frame load.

## Cost and Destination Approval

| Service | Proposed resources | Monthly estimate USD | Destination approval |
|---|---|---:|---|
| Streamlit Community Cloud | Existing wrapper, Python 3.11 | 0 | Account/app unset |
| Render web | 0.5 CPU, 512 MB, one instance | 7 | Workspace/region unset |
| Render private ML | 1 CPU, 2 GB, one worker/instance | 25 | Same workspace/region unset |
| AuraDB Free | 3,415 nodes / 16,230 relationships | 0 | Dedicated database host unset |
| Private R2 Standard | About 240 MB model, no public bucket | 0 within free allowance | Account/bucket/object unset |
| Auth gateway/domain | Invitee allowlist, expiring access | TBD | Provider/domain unset |

Baseline **$32/month plus gateway/domain, taxes and overages**, not a spending
cap or complete approved quote. Prior paid Aura alternative adds about $65.70
per month. Confirm current account quote, quotas and inactivity behavior before
approval. Current Render documentation confirms 0.5c-512mb and 1c-2g plan specs;
the dynamically rendered pricing page did not expose numeric prices during this
recheck, so $7/$25 remain estimates from the preceding review, not a new quote.
Sources: [Render plans](https://render.com/docs/compute-plans),
[Render pricing](https://render.com/pricing/), [Aura](https://neo4j.com/pricing/),
[R2](https://developers.cloudflare.com/r2/pricing/).

Local measured model memory exceeds 600 MiB; do not choose 512 MB for ML.
Cloud CPU/memory/concurrency acceptance still required. The private model and
biomedical graph are separate external transfers requiring explicit approval.

## Decisions Needed Before Proceeding

1. Specify demo date/end time, responsible operator, authorized audience and
   authentication provider/domain. Approve implementing that access mechanism.
2. Obtain explicit per-risk decisions; resolve unknown native exposure or supply
   sufficient evidence for authorized, bounded review. Approve any necessary
   repository-policy change separately; do not forge passing checks.
3. Authorize PR58 integration, validate combined source, then separately
   authorize PR57 main merge and record the exact main SHA.
4. Approve exact provider accounts/region/plans and budget, model bucket/object,
   Aura destination, uploads/import, public exposure and shutdown deadline.
5. Provide authorized provider access through tools/dashboard sessions, not
   credentials in chat. Follow the manual runbook if no connector is available.
6. Complete real cloud, browser and five-scenario acceptance before demo approval.

Production readiness remains blocked independently of any future temporary
academic approval. Operations and shutdown: [demo guide](../deployment/ACADEMIC_DEMO.md).
