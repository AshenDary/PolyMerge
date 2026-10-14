# Deployment guide

## Decision and authorization

No hosting account, billing, DNS, database exposure, model publication or public deployment was configured. This is a research prototype, not a clinical product. Fix the audit's public-exposure blockers before enabling external access.

Recommend a paid, always-on multi-service deployment with private ML and graph connectivity, plus an authenticated HTTPS frontend. Keep Streamlit optional. The checked-in Compose/SSH template targets an explicitly provisioned private staging host and does not assume a vendor. A managed container platform is operationally easier; a dedicated host gives direct control over private model mounts and long request timeouts. Jared must approve which tradeoff and budget to use.

## Hosting comparison (official documentation checked 2026-10-15)

| Option | Practical architecture | Resources, persistence and limitations | Cost evidence |
| --- | --- | --- | --- |
| A: Streamlit Community Cloud + paid Render services | Community Cloud only wraps HTTPS Fastify; Fastify reaches a paid private FastAPI service; Neo4j is separately provisioned privately or managed with TLS; MySQL only if persistence is implemented | Multiple providers and iframe authentication complicate debugging. Render private services are not public endpoints; disk-backed model storage requires paid service. Free web services sleep after 15 minutes, have ephemeral filesystems and cannot attach persistent disks. Poor fit for reliable long inference demos | Render's dynamic pricing page did not expose a reliable current compute quote in this audit. Confirm paid CPU/RAM/disk, bandwidth and graph pricing in dashboard before approval; no invented total |
| B: Railway multi-service project | Public HTTPS Fastify and optional Streamlit; private FastAPI and privately provisioned Neo4j; model on persistent volume; MySQL optional | Fewer provider boundaries, separate service sizing, usage metering. Volume backup, restart behavior, region, private graph connectivity and account-specific limits must be verified before provisioning. A self-hosted Neo4j container is not automatically a managed DB | Hobby minimum $5/month includes $5 usage; RAM $10/GB-month, CPU $20/vCPU-month, volume $0.15/GB-month, egress $0.05/GB. Not an all-inclusive $5 stack |
| C: dedicated container host | Checked-in Compose behind approved authenticated TLS reverse proxy; private graph dependency; optional Streamlit | Most reproducible private file mount; operator owns patching, backups, monitoring and TLS. Single-host failure domain. Only loopback application ports published by template; no DB ports | Provider not selected, quote required. Do not imply this is free |

Sources: [Render free-tier limits](https://render.com/docs/free), [private services](https://render.com/docs/private-services), [persistent disks](https://render.com/docs/disks), [Render pricing](https://render.com/pricing), [Railway pricing](https://docs.railway.com/pricing), [Railway HTTPS networking](https://docs.railway.com/networking/public-networking).

Community Cloud documentation lists approximate, explicitly changeable limits dated February 2024: 690 MB-2.7 GB memory and up to 50 GB storage. It hibernates after 12 hours without traffic. These are not a current guaranteed reservation. Host only the lightweight wrapper there, not the model/backend/Neo4j stack. [Streamlit resource guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)

Capacity recommendation, not a measured peak guarantee: begin load qualification with at least 2 GB RAM for one ML worker, reserve extra graph RAM separately, and monitor peak RSS during two-disease queries. Local queries took ~20/~58 seconds; multiple workers duplicate model memory. The 251,404,304-byte file is not the loaded-process footprint. A 1 GB private model volume fits the file and a second copy, but OS/image/data/log space is additional. Example Railway memory usage of 2 GB continuously alone costs about $20/month before CPU, graph, frontend and storage. Confirm all account limits and a spend ceiling. Avoid sleep-to-zero for timed demos.

## Runtime layout and startup

1. Provision the reviewed Hetionet fragment privately with a read-only runtime Neo4j user. Preserve node IDs and compare counts against the audit. Back up its volume/snapshot. Loading/importing a graph is a separate authorized operation.
2. Provision the frozen artifact and exact runtime mapping/metadata files. Start FastAPI and verify `/health/model` plus disease catalog, not liveness alone.
3. Start Fastify with private `ML_SERVICE_URL`; it serves the actual frontend and same-origin API. Check `/health/dependencies` and `/api/diseases`.
4. Optionally start Streamlit pointing to the browser-reachable HTTPS Fastify URL. Configure TLS/access gateway with request timeouts above the application's 150-second limit.

Defaults: Fastify 3000, FastAPI 8000, Streamlit 8501, Neo4j Bolt 7687/browser 7474, MySQL 3306. Deployment template exposes application ports on host loopback only. Never use the root development `docker-compose.yml` as public deployment configuration; it contains weak development credentials and wildcard DB bindings. No DB container is created by the staging template. Containers cannot use host `localhost` for an external graph: configure a reachable private hostname/network explicitly.

The canonical runtime does not currently use Prisma/MySQL. `backend/prisma/schema.prisma` and migrations exist but query history is an in-memory map, not SQL persistence. Do not provision/migrate a database merely to make an architecture diagram look complete. If SQL-backed features are enabled later, provision private MySQL and review migration/backup separately.

## Environment and secrets

| Consumer | Names | Placement |
| --- | --- | --- |
| Fastify | `HOST`, `PORT`, `NODE_ENV`, `LOG_LEVEL`, `CORS_ORIGIN`, `ML_SERVICE_URL`, `ML_SERVICE_TIMEOUT_MS`, `ML_CATALOG_TIMEOUT_MS`, `ML_HEALTH_TIMEOUT_MS`, `ML_CANDIDATE_TIMEOUT_MS` | Host/container configuration; explicit HTTPS origin, private ML address |
| ML | `NEO4J_URI`, `NEO4J_USER` (alias `NEO4J_USERNAME`), `NEO4J_PASSWORD`, `POLYMERGE_DDI_MODEL_PATH`, container `PORT` | Secret manager or owner-only staging env file; TLS graph URI where supported |
| Streamlit | `POLYMERGE_FRONTEND_URL` (legacy fallback `POLYMERGE_API_URL`), container `PORT` | Set real HTTPS frontend URL, never remote localhost |
| Optional Prisma tooling | `DATABASE_URL`, `SHADOW_DATABASE_URL`; local Compose `MYSQL_PORT` | Private SQL credentials only when needed; never run shadow migrations against production |
| Existing example only | `JWT_SECRET` | Not implemented authentication; setting this does not secure endpoints |
| Compose | `RELEASE_SHA`, `FRONTEND_ORIGIN`, `MODEL_DIRECTORY` | Reviewed SHA, browser-facing origin, existing trusted absolute host directory |
| GitHub staging | `STAGING_SSH_KEY`, `STAGING_KNOWN_HOSTS`, `STAGING_SSH_HOST`, `STAGING_DEPLOY_ENABLED` | Protected Environment as described in CI_CD.md |

Never log expanded env/config or commit a real secret. `.dockerignore` excludes env files, models, caches and datasets not explicitly needed. Dockerfiles copy only runtime code, reviewed metadata/mappings and UI reports. They use non-root users. Python dependencies include research/test packages today; splitting runtime dependencies and generating a reviewed transitive lock are follow-ups. Do not upgrade scikit-learn around a serialized model without compatibility validation and artifact governance.

## Model distribution

Use an authenticated private transfer or private object-store download into an operator-provisioned volume. Do not add a public URL or bake the joblib into images. The template mounts an existing directory read-only at `/model`; UID 10001 needs read/traverse access. Provision enough disk for atomic replacement and rollback, with no world-writable model directory.

Expected file: `random_forest_ddi_pipeline.joblib`; size `251404304` bytes; SHA-256 `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`; version `RandomForestClassifier-sprint5-v1-65e9834666ad19c5`.

Verify before load with `sha256sum` (macOS: `shasum -a 256`) and file size. The application rechecks hash, size, feature-contract hash, version and pipeline shape. Checksums establish integrity relative to trusted metadata, not a digital signature; joblib deserialization requires a trusted source. Keep rollback copies private and immutable.

Required image data: `data/interim/sprint3/ddinter_hetionet_mapping.csv`, `ddinter_pubchem_mapping.csv`, `data/processed/fragment_edges.csv`, `data/interim/sprint4/feature_contract.json`, `data/interim/sprint5/final_model_evaluation.json`. Confirm redistribution permissions before publishing any image containing mappings/data; CI builds but never uploads images.

## Smoke and iframe acceptance

From inside the deployment network or a secure tunnel:

```sh
python3 scripts/deployment_smoke.py --frontend http://127.0.0.1:3000 --ml http://127.0.0.1:8000 --streamlit http://127.0.0.1:8501
# Only on an approved, provisioned staging environment:
python3 scripts/deployment_smoke.py --frontend http://127.0.0.1:3000 --ml http://127.0.0.1:8000 --streamlit http://127.0.0.1:8501 --query
```

The optional query checks real_graph, nonempty candidates, deterministic path identities/provenance, known relationship types, distinct rule status and actual frozen-model pair severity, and rejects confidence/probability/safety-score fields. Null legacy fields are permitted. It does not establish clinical validity or graph database authenticity solely from returned metadata.

Also run Streamlit AppTest with `POLYMERGE_FRONTEND_URL` and assert its iframe `src` equals the approved URL. A server-rendered Streamlit shell does not expose the websocket-delivered iframe DOM to a simple HTTP fetch. Browser acceptance must inspect the rendered iframe, network/console, HTTPS, no mixed content, responsive desktop/mobile layout, search/reset during an in-flight request, keyboard focus and Model Analysis assets. Record screenshots and exact deployment SHA. Until then visual acceptance is NOT TESTED.

Configure `Content-Security-Policy: frame-ancestors` to permit only the approved wrapper origin; avoid `X-Frame-Options: DENY/SAMEORIGIN` when intentionally framing across origins. Validate actual embedding before enforcing policy. Same-origin API calls inside the iframe do not need permissive CORS. Access control must cover both wrapper and embedded app; third-party cookies/login redirects can break an iframe. The current app lacks authentication/rate limits, so restrict the gateway to authorized demo users and block legacy/history routes until fixed.

## Failure and rollback

Failure signals: nonzero deployment/smoke exit, unhealthy/restarting container, 503 dependencies/model, missing catalog/evidence, no applied inference, blank iframe, advisory gate failure. Inspect `docker compose --project-name polymerge-staging --env-file /srv/polymerge/staging.env -f deploy/compose.staging.yml logs --tail=200` locally, redact sensitive details before sharing. During long inference, health can stall; do not automatically scale/restart-loop based on liveness without resolving blocking work.

Retain previous application images and release directory. To roll back, go to that directory, export its exact `RELEASE_SHA`, and run the same Compose command with `up -d --no-build --wait`. Verify the image IDs match the recorded successful release, mounted model hash/version and graph snapshot; run smoke and browser checks again. This replaces application containers only. Never run `down -v`, database reset/drop, development migrations or automatic graph reload. Restore a DB backup only under a separate reviewed recovery plan. The in-memory query history is lost on restart; warn demo users.
