# Strict $0 Academic Demo

**Not deployed. Free-tier feasibility remains blocked.**
The [measured assessment](../audits/sprint6-free-tier-feasibility.md) supersedes
paid options in earlier runbooks. Do not activate the paid Render blueprint,
R2 billing, Aura Professional, paid gateways/domains/disks or trial-only compute.

## Candidate Architecture, Not Approval

Streamlit Community Cloud embeds the unchanged Fastify frontend over HTTPS.
Candidate backend host: non-upgraded Oracle Always Free ARM VM, one OCPU/4GB,
included50GB boot disk. Run existing Fastify and FastAPI containers separately,
with only authenticated frontend ingress and an internal-only ML port. Connect
to AuraDB Free using neo4j+s. Keep the unchanged model on private included disk.
This candidate has not been provisioned or accepted; free hostname/TLS/access
and account availability must be resolved before resource creation.

Do not put an API key in Streamlit/frontend JavaScript, expose ML port8000,
or assume iframe privacy protects a direct URL. Any public ML alternative
requires authenticated server-to-server access and workload controls before
exposure. Retain exact CORS/CSP and test actual iframe login, expiry and logout
with third-party cookies disabled. A fallback URL needs the same access controls.

## Approval Checklist

1. Verify account is standard Free Tier, never upgraded to PAYG; confirm actual
   home-region capacity, Always Free labels, aggregate usage and zero-spend
   behavior. No reliance on30-day credits. Stop if any component can bill.
2. Approve account/region, plan, included volume, Aura host, private model path,
   zero-cost hostname/access provider, audience and expiry. No secrets in chat.
3. Review retained CVEs and document named, time-bounded risk decisions. Do not
   make required security checks green by removing them or hiding findings.
4. Approve PR58 integration, validate combined source, approve PR57 main merge,
   and capture exact reviewed main SHA. No deployment from outdated main.
5. Separately approve cloud resource creation, model upload, graph import and
   restricted public exposure. No provisioning has been authorized by this file.

## After Approval Only

- In approved OCI console, select an Always Free ARM shape/image in the home
  region and the exact reviewed resource allocation. Confirm no paid extras,
  marketplace licensing, disks beyond quota or account upgrade. On capacity
  failure, stop or wait; never switch to paid compute.
- Build exact main revision using existing Dockerfiles on the approved host
  (build resources also consume quotas). Use separate supervised containers
  with health checks, clean shutdown, one ML worker, bounded memory and logs.
  Keep raw backend/ML ports private behind the approved HTTPS/access layer.
- Secure-copy the original model only to the approved private path; hash must
  equal2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d.
  Mount it read-only at POLYMERGE_DDI_MODEL_PATH; set POLYMERGE_REQUIRE_MODEL=true.
  Do not publish artifacts or bake secrets/model into a public image.
- Create only AuraDB Free at the approved destination. Use existing
  `scripts/migrate_aura.py --apply --approved-host <host>` and then `--verify`
  with the same approved-host argument after import approval. Verify full node,
  edge, ID, provenance, constraint and scenario parity; never replace source data.
- Supply NEO4J_URI/USER/PASSWORD/DATABASE in protected runtime configuration,
  POLYMERGE_REQUIRE_NEO4J_TLS=true, and Fastify ML_SERVICE_URL pointing solely
  to the private container network. Configure exact CORS_ORIGIN/STREAMLIT_ORIGIN,
  reviewed proxy trust and existing workload bounds. No plaintext cloud graph.
- In Community Cloud select the reviewed repository/main, streamlit_app.py and
  Python3.11. Set POLYMERGE_FRONTEND_URL to the approved HTTPS frontend only.
  Approve source-update behavior and ensure main still matches the recorded SHA.
  Do not change the wrapper into a simplified simulation UI.

## Acceptance

Record actual URLs, SHA, provider plan IDs and zero-spend account evidence.
Measure cold starts including downloads, graph latency, cgroup peak memory,
one/two/four-disease latency, CPU and bandwidth on the real host. Local tests are
not provider benchmarks. Retest restart and full model readiness; fail closed
if the model, graph or mappings are unavailable. No fake/cached substitute results.

Compare all313 prediction probes and five saved scenario outputs exactly.
Verify Home/Model Analysis, Select Diseases, Analyze (remain active after
completion), explicit advance, Review Candidates with five-item pages,
Understand Result, Simple/Researcher views, evidence, rules, Takeaway and Reset.
Run actual desktop/mobile/keyboard and iframe tests, including denied users,
expired sessions, origin bypass, oversized input and concurrent analysis.
Do not claim success solely from health endpoints or a working fallback.

## Start and Shutdown

Before the defense, manually resume Aura if paused, check host availability,
start supervised services and wait for model/graph readiness. Visit Streamlit
and wake it if sleeping; run one real known scenario and check access expiry.
No periodic artificial pings or synthetic load to avoid idle reclamation.
If free capacity is unavailable or limits are exhausted, stop; no paid fallback.

At end, revoke audience access and sessions, disable frontend ingress, remove
Streamlit exposure and stop demo processes. Confirm direct URLs deny access.
Revoke transfer/runtime credentials as approved. Retain or delete VM volume,
private model and Aura graph only under explicit owner retention instructions.
Verify provider account remains non-upgraded and actual charges are$0.00;
record shutdown and quota usage. Keep research sources and audit evidence.
