# Academic Demo Operations

Current budget is strictly$0. The [free-tier guide](FREE_TIER_ACADEMIC_DEMO.md)
supersedes paid provisioning steps below. Preserve these as historical context;
do not execute the paid sequence for the current request.

**Preparation only. No service is deployed or approved.** Read the
[demo risk/approval assessment](../audits/sprint6-academic-demo-assessment.md)
and [configuration runbook](STREAMLIT_RENDER_AURADB.md) first. Keep existing UI,
55-feature model contract, graph schema and scientific logic unchanged.

## Manual Dashboard Sequence After Approval

1. Record approved reviewer, audience, expiry, budget, destinations and exact
   verified main SHA. Confirm protected-branch policy is satisfied; never use
   an admin override without a separately authorized repository-policy decision.
2. In Neo4j Aura console select the approved organization, region and plan;
   create the dedicated database only after cost approval. Store its credentials
   in a secret manager. Confirm the exact neo4j+s host against the approved host.
3. After separate import approval, set AURA_NEO4J_* in a protected local
   environment. Run `scripts/migrate_aura.py --apply --approved-host <host>`
   followed by `--verify --approved-host <host>`, using the existing Python 3.11
   environment. Verify full identities, relationships, provenance, constraints
   and candidate parity, not just counts. Retire migration credentials afterward.
4. In the approved storage account create the private bucket/object and upload
   the unchanged model only after transfer approval. Leave public access off.
   Verify checksum; create the narrow, expiring download URL through authorized
   storage tooling. Never paste it into issues, logs or the Streamlit wrapper.
5. In Render select New > Private Service, approved repository/main revision,
   Dockerfile `deploy/Dockerfile.ml`, 1 CPU/2 GB, one instance in the approved
   region. Keep automatic deployment off. Supply private model/Neo4j variables
   from the configuration runbook; require model readiness and verified TLS.
   Check provider deployment commit equals the approved SHA. Confirm no public
   ML ingress. Test graph, rules, predictions, memory and restart inside the
   authorized private network before continuing.
6. Configure the approved authenticated gateway and origin-bypass prevention
   before exposure. In Render create the web service using
   `deploy/Dockerfile.backend`, 0.5 CPU/512 MB, same region and private ML URL.
   Set exact CORS/frame origins, workload limits and verified proxy configuration.
   Do not expose a permissive backend while waiting for the gateway to be ready.
7. In Streamlit Community Cloud choose repository AshenDary/PolyMerge, reviewed
   main, `streamlit_app.py`, Python 3.11. Set only the approved HTTPS frontend
   URL in wrapper configuration. Confirm the main SHA has not moved and approve
   source-update behavior explicitly before deploying.
8. Record actual URLs, deployment IDs, SHA, billable resources and operator.
   Perform all acceptance below; do not announce readiness based on health alone.

Provider access has not been established in this session. These steps describe
authorized operator actions, not completed provisioning. Check provider UI
labels and account quotes when executing.

## Pre-Demonstration Check

- Verify approved access expiry has not passed and all URLs reject uninvited
  visitors. Test direct Render-origin bypass, forged forwarded headers, quotas,
  input bounds and isolated explanation state. Stop on disclosure or secrets.
- Verify Streamlit health, Fastify readiness and private ML readiness from its
  private network. Confirm frozen model checksum/version, Aura TLS/connectivity
  and mapping provenance. Never print environment variables for troubleshooting.
- Run `scripts/deployment_smoke.py --help` and then the documented smoke checks
  with real URLs from the authorized network; use `--query` for actual inference.
  Adapt authentication through the approved mechanism without weakening it.
- Compare deployed results with the five saved local snapshots: hypertension;
  hypertension/type 2 diabetes; coronary disease/atherosclerosis; metabolic
  syndrome X/coronary artery disease/chronic kidney failure/hypertension; no
  represented coverage. Compare complete candidates, optimizer, rules, graph
  coverage, unavailable pairs, probabilities and Takeaway. Never replace goldens.
- Test desktop, mobile and keyboard in the actual Streamlit iframe, including
  fresh/expired sessions and third-party-cookie blocking. Check console/network
  for mixed content, framing failures and unintended public/private requests.

## Presentation Workflow

Open Home and Model Analysis; Select Diseases; Analyze. After completion, verify
Analyze remains active until the presenter explicitly advances. Review Candidates
with five-candidate pagination; open Understand Result in Simple and Researcher
views; inspect Research Takeaway, provenance, rules and pair predictions. Test
Reset/New Simulation and all backward/forward navigation without state leakage.
The Streamlit wrapper must embed the existing frontend, not replace its screens.

## Recovery

If ML is unavailable, inspect sanitized provider logs and memory/graph status.
Restart only the approved ML service on the same SHA; wait for complete model
and graph readiness, then retest Fastify and a known simulation. If the ephemeral
model cache is lost, renew an expired signed URL through the approved secret
store and verify download integrity before retrying. Never disable model checks.

For graph failures, check Aura state and verified TLS host with the authorized
account. Do not reimport or mutate data as a connectivity workaround. For iframe
failure, use the approved, equally authenticated Fastify fallback temporarily;
record embedding as failed, not as full acceptance. If output parity differs,
stop the demonstration and investigate instead of showing substituted results.

## Shutdown

At the approved end time, revoke gateway access/sessions and verify both iframe
and direct backend deny access. Disable Streamlit exposure and Render web ingress;
stop/delete demo compute according to approved retention policy. Confirm billing
stops in provider dashboards; stopping traffic alone does not stop charges.
Revoke model download/storage credentials and runtime/migration database access.
Retain or delete the private model object and Aura database only according to
explicit owner authorization; never destroy research source data automatically.
Keep audits and deployment IDs, record shutdown verification and final charges.
