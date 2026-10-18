# Streamlit, Render and AuraDB Deployment

**Current strict-$0 request supersedes this document's paid proposals.** Use the
[free-tier runbook](FREE_TIER_ACADEMIC_DEMO.md); do not provision the paid Render
blueprint, Aura Professional or metered storage under the zero-cost task.

Temporary academic demonstration: see the separate [risk approval checkpoint](../audits/sprint6-academic-demo-assessment.md)
and [operations guide](ACADEMIC_DEMO.md). Academic scope does not automatically
waive security findings, authorize merges or approve external transfers.

Latest release gate: [assessment](../audits/sprint6-final-release-gate-assessment.md).
The private ML template requires `POLYMERGE_REQUIRE_NEO4J_TLS=true` and a
certificate-verified `neo4j+s` URI without embedded credentials. The shared
driver has a 10-connection maximum **per process**; account for every worker
and replica when reviewing Aura limits. Connection/acquisition timeout is
5 seconds, query timeout 30 seconds, connection lifetime 300 seconds.
Shutdown closes the shared driver; individual queries retain private sessions.

Render private addressing is not backend-only authorization: other eligible
same-workspace/region services may reach the ML service. Review workspace
isolation and service authentication before provisioning. Local proxy tests
verify quota spoof resistance only for the configured test chain. Establish
Render's actual proxy source ranges and header behavior before setting trust;
provider TLS, forwarded headers, iframe/browser behavior and live graph
connectivity still require separately authorized acceptance testing.

Prepared 2026-10-18 (Asia/Manila). **Not deployed; no approved release SHA.**
Security acceptance, main merge, provider accounts and explicit cloud approvals
are required. `deploy/render.blueprint.yaml.disabled` is a review template, not
an activated Blueprint. Do not provision it merely to test its syntax.

## Architecture and Costs

| Component | Proposed provider/size | Estimated monthly USD |
| --- | --- | ---: |
| Presentation | Streamlit Community Cloud | 0 |
| Fastify public frontend/API | Render 0.5 CPU / 512 MiB | 7 |
| Private FastAPI ML | Render 1 CPU / 2 GiB | 25 |
| Graph, low-cost demo | AuraDB Free | 0 |
| Graph, live-defense alternative | AuraDB Professional 1 GiB | about 65.70 |
| Private model, proposed only | Cloudflare R2 Standard, about 240 MB | 0 within account free allowance |

Indicative total: **$32/month** with Aura Free; **$97.70/month** with the
1 GiB Professional baseline, before tax, region differences, bandwidth/build
overages, optional disks, backups and other account usage. A more CPU-intensive
2 CPU / 4 GiB Render ML service is $85/month, not assumed necessary here.
Confirm the account/region quote before approval; no spending cap is enforced by
this document. No destination or account has been approved.

Official sources checked during preparation:
[Render pricing](https://render.com/pricing),
[compute plan IDs](https://render.com/docs/compute-plans),
[Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud),
[Aura pricing](https://neo4j.com/pricing/),
[Aura Free limits](https://neo4j.com/free-graph-database/),
[R2 pricing](https://developers.cloudflare.com/r2/pricing/).

Aura Free supports 50,000 nodes / 175,000 relationships; the reviewed graph is
3,415 / 16,230, comfortably within size limits, but cloud query latency/capacity
still needs measurement. Free has no backups and pauses after three inactive
days. Professional pricing starts at $0.09/GB/hour; the estimate uses 730 hours.
Render private services have no free instance. A free public service introduces
idle cold starts and is not the live-defense recommendation. No keep-alive
traffic is proposed to evade free-tier restrictions.

R2 includes 10 GB-month storage, one million Class A and ten million Class B
operations in its Standard free allowance, with no egress charge. Above that,
Standard storage is $0.015/GB-month, A $4.50/million and B $0.36/million.
Do not enable public bucket access. This is a proposed private destination only.

## Measured Resources

Linux ARM64 frozen-model inference probe: 643,196 KiB peak RSS (about 628 MiB),
including model load and feature building. Updated macOS Python 3.11 four-disease
pipeline: 641,138,688 bytes peak RSS and 1.661 seconds for 100 candidates locally.
These measurements rule out claiming that 512 MiB is sufficient. Start evaluation
at 2 GiB, one worker, one analysis slot; cloud AMD64 latency, peak concurrency,
graph network time and restart behavior remain acceptance work. Local timing is
not a cloud SLA. Hash-locked dependencies and pinned base digests reduce drift.

## Approval Checklist

1. Review security PR and explicitly accept or resolve remaining advisories.
2. Approve merging remediation into integration and PR #57 into main.
3. Fetch main with fast-forward only and record the exact reviewed main SHA.
4. Approve provider accounts, region, plans, monthly budget and exact Aura host.
5. Approve private bucket/object destination and external model upload.
6. Approve graph transfer, public exposure and exact HTTPS origins separately.
7. Decide automatic deployment policy. Render is manual (`autoDeployTrigger: off`).
   Streamlit Community Cloud updates on tracked source changes; enabling that
   behavior needs explicit approval, not an assumption hidden in initial setup.

No deployment may use the unmerged security branch. Never bypass required checks.

## Configuration

Streamlit needs only `POLYMERGE_FRONTEND_URL`, the approved HTTPS Fastify origin.
Set it as an environment variable in the wrapper runtime. Community Cloud's
root-level TOML secrets can expose that setting as an environment variable;
do not place Neo4j credentials, signed model URLs or storage credentials there.
Use Python 3.11, repository root `streamlit_app.py`, and root `requirements.txt`.
The wrapper validates the URL and uses the native iframe API; HTTP is accepted
only for loopback development. Health check: `/_stcore/health`.

Fastify variables:

- `NODE_ENV=production`, `HOST=0.0.0.0`, `PORT=3000` (or provider port).
- `ML_SERVICE_URL=http://<Render-private-host>:8000`; copy the actual private
  address after ML creation. Never point to localhost or a public ML URL.
- `CORS_ORIGIN=https://<approved-fastify-host>`; comma-separated exact origins
  only when actually necessary. The iframe executes at Fastify's origin.
- `STREAMLIT_ORIGIN=https://<approved-app>.streamlit.app` for CSP frame ancestors.
- `RATE_LIMIT_MAX=120`, `ANALYSIS_RATE_LIMIT_MAX=6`,
  `ML_CANDIDATE_TIMEOUT_MS=120000`; one instance only.
- Optional `TRUST_PROXY_CIDRS`: explicit IP/CIDR entries only; universal networks,
  symbolic aliases and malformed values fail startup. Only verified provider proxy ranges. Test spoofed
  forwarding headers before enabling. Default false is safe but can aggregate
  quotas behind the provider proxy; resolving this is a launch acceptance item.

Private ML variables:

- `PORT=8000`; one Uvicorn worker. No public ingress/custom domain.
- `NEO4J_URI=neo4j+s://<approved-host>`, `NEO4J_USER`, `NEO4J_PASSWORD`,
  `NEO4J_DATABASE=neo4j`. Use a read-only runtime graph identity where supported;
  do not retain migration credentials in the application.
- `POLYMERGE_REQUIRE_MODEL=true` and
  `POLYMERGE_DDI_MODEL_PATH=/home/app/model/random_forest_ddi_pipeline.joblib`.
- `POLYMERGE_MODEL_DOWNLOAD_HOST=<approved-private-storage-host>` and
  `POLYMERGE_MODEL_DOWNLOAD_URL=<secret-presigned-HTTPS-GET-URL>`.

The approved checksum and size come from tracked frozen metadata, not a
browser-supplied value. Bootstrap rejects redirects, wrong hosts, excess size,
invalid checksums and failed downloads; it publishes the local file atomically
with owner-only permissions. Verified cache is reused on restart. An ephemeral
instance replacement needs a fresh download; expired signed URLs must be renewed
before replacement. Never log or paste signed URLs into issues. Restricted
read-only object access and short-lived signed GET URLs are proposed; upload and
bucket setup still require approval. See [R2 presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/).

## Graph Migration

Read-only offline manifest:

```sh
python scripts/migrate_aura.py
```

It verifies 299 compounds and nine mappings against canonical IDs. Source hashes:

- nodes: `7b8b0d83067b333d10fb1446b50687b73b039c05e3ad2098b720b87690308e06`
- edges: `4e7b459c93743548041cb370e43ddfc1c7f4d495e71447de3d74b1e58ae9e1c1`

Expected nodes: Compound 299, Disease 25, Gene 1,411, Pharmacologic Class 37,
Side Effect 1,643. Relationships: CtD 142, PCiC 91, CbG 1,010, CuG 977,
CdG 1,484, CcSE 11,987, CrC 519, CpD 20.
The local graph exactly matches; it currently has only two lookup indexes and no
constraints. The migration adds a unique PolyMergeNode ID constraint and records
source/version provenance. It does not delete data. It refuses foreign IDs,
conflicting records or duplicate identities before mutation, supports retrying
partial imports and verifies full identity/edge parity afterward.

Only after target approval, supply `AURA_NEO4J_URI`, `AURA_NEO4J_USER`,
`AURA_NEO4J_PASSWORD`, `AURA_NEO4J_DATABASE` via a protected local environment:

```sh
python scripts/migrate_aura.py --apply --approved-host <approved-host>
python scripts/migrate_aura.py --verify --approved-host <approved-host>
```

Use a dedicated empty database or verified partial import. Block concurrent
writers during migration. Then test CtD, pharmacologic classes, rule identity
resolution and five candidate scenarios against local snapshots. No import has run.

## Deployment Order

After all gates: create approved Aura target, migrate/verify graph, upload the
approved private model, create Render private ML, require `/ready` success,
create Render web service, validate private upstream and quotas, then configure
Streamlit and approved embedding. Use provider dashboards or connected tools;
no Render/Aura/storage provider connector is currently available in this session.
Account login and credentials must stay in provider secret stores, not chat.

For Render, choose the exact reviewed main commit with automatic deployments
disabled. The disabled Blueprint describes both Docker services in one region.
Select private service (`pserv`) for ML, not web. Confirm no public ML hostname.
For Community Cloud, select repository `AshenDary/PolyMerge`, reviewed `main`,
entrypoint `streamlit_app.py`, Python 3.11 and approved public frontend URL.
Do not click Deploy until public exposure and source-update behavior are approved.

## Acceptance and Rollback

Run `scripts/deployment_smoke.py` from the private deployment network with real
frontend/private-ML/Streamlit URLs and `--query`. Check `/ready`, signed-artifact
expiry/replacement, network isolation and actual deployed SHA. Re-run the five
scenario audit against deployed Fastify. HTTP 200 is not full acceptance.
Desktop/mobile/keyboard tests must verify the embedded four-step workflow,
selection, pagination, both views, Takeaway, Model Analysis, reset and navigation.
Test blocked history, oversize/invalid inputs, quotas, disallowed origins,
spoofed forwarding headers, no raw private ML proxy and no credential exposure.
Exercise service restart, cache reuse and redeploy with an expired artifact URL.

Rollback only to a previously reviewed secure main commit, manually on Render;
keep automatic deployment off. If there is no prior secure release, take the
public service offline rather than restoring an insecure branch. Revert source
through a reviewed PR; do not reset main. Preserve the verified graph and model;
revoke any leaked signed URL and rotate affected secrets. No destructive graph
rollback is automated. Record provider deployment IDs and logs in the release audit.
