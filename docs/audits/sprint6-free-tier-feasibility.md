# Strict Zero-Cost Feasibility

Review: 2026-10-18. **FREE-TIER FEASIBILITY BLOCKED - RESOURCE LIMITS**.
Budget: $0.00. No resources provisioned, no uploads/imports, no merges, no
paid fallbacks. Existing academic-demo documents are preserved; their paid
architecture is superseded for this task, not silently relabeled free.

## Repository and Integrity

Fetched all branches. Working branch and HEAD:
`fix/pre-deployment-security-and-cloud`,
`cda2835863f1e1774bfb4b142f29a9cc2ab6e215`.
PR58 OPEN against integration `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`;
PR57 OPEN against main `2edcc39bfe83296b00020e9d7894aa3d95889754`.
Existing uncommitted academic assessment, operations guide and runbook changes
were reviewed and preserved. No new application commits or changes to scientific
code, UI, locks, model, paper or slides. No approved deployment main SHA exists.

Fresh regression: backend 125 passed; ML 133 passed, two existing dependency
warnings; scripts 13 passed. Contract, metadata and frontend syntax pass.
Frozen-runtime probe again matches all 313 rows/classes/probabilities exactly.
All five scenarios match complete candidates and optimizer metadata in a
resource-constrained Linux ML process and through constrained Fastify.
No held-out evaluation, training, model reserialization or golden replacement.
SHA256: `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.

Last hosted CI remains [39059460054](https://github.com/AshenDary/PolyMerge/actions/runs/39059460054):
regression/build/runtime checks passed; dependency/image security failed.
No new hosted run claimed for these documentation-only edits.

## Actual Resource Experiment

Existing `polymerge-ml:release-gates` ARM64 production image, Python 3.11,
sklearn 1.4.0, original model mounted read-only, swap disabled, dropped
capabilities, read-only filesystem, bounded tmpfs. Docker CPU quota approximates
entitlement, not Render hardware speed. Tests use the real local Neo4j graph;
Aura latency, remote downloads, host OS memory and registry pulls are excluded.
The harness imports the real FastAPI app, loads its singleton model, and submits
the five fixture requests with TestClient, asserting full output parity.
It records monotonic time, process high-water RSS, cgroup memory and CPU usage.
Local harness: `/tmp/polymerge-resource-probe.py`; observations retained in
`security-evidence/free-tier-resources.json`.

| Profile | Result |
|---|---|
| ML 512 MiB, 0.1 CPU, no swap | Kernel OOM, exit137, during original model load; no successful inference |
| ML 2 GiB, 1 CPU, no swap | All five scenarios pass exactly; exit0 |
| Fastify 512 MiB, 0.1 CPU | Five real upstream scenarios pass exactly; measured cgroup peak 61,681,664 bytes (58.8 MiB) |

First 512 MiB run: imports completed at 37.601s, process peak198,352 KiB;
container terminated after53.052s without reaching model-loaded stage.
Its inherited health helper also ran. A second run with health checks disabled
also OOM-killed during model load (exit137), after38.930s; imports completed
at28.502s. Removing the health helper did not resolve the memory failure.
Per-prediction and candidate timings at512 MiB are **unavailable**, not zero:
the model never became ready. A successful cold-start time does not exist there.

Measured 2 GiB/1 CPU stages (cgroup peaks include charged filesystem cache):

| Stage | Elapsed / request seconds | Process peak KiB | Cgroup peak bytes |
|---|---:|---:|---:|
| Python started | 0.000 | 14,048 | 9,781,248 |
| Imports complete | 1.140 | 198,724 | 147,365,888 |
| Model loaded | 4.190 | 689,860 | 903,950,336 |
| Hypertension | 1.446 request | 749,532 | 940,527,616 |
| Hypertension + diabetes | 1.180 request | 767,412 | 958,271,488 |
| Coronary + atherosclerosis | 0.796 request | 776,700 | 970,104,832 |
| Four diseases | 1.373 request | 793,032 | 990,486,528 |
| No coverage | 0.008 request | 793,032 | 990,486,528 |

Overall peak: 774.4 MiB process RSS; 944.6 MiB cgroup accounted memory.
CPU usage: 7.737 CPU-seconds over9.318 wall seconds; quota throttling observed.
Model-ready duration includes imports/checksum/deserialization from a local
mounted artifact, not a provider cold start. Pair inference is included in
candidate measurements; isolated pair-only peak was not separately instrumented.
Sequence effects matter: later rows include warmed caches and cumulative peaks.

Fastify listened after approximately3.541s from container start.
Fastify request times, with an unconstrained existing ML upstream:
2.162/2.709/1.866/2.108/0.073s respectively. This establishes frontend fit,
not an end-to-end512 MiB ML deployment. Docker-reported image sizes:
ML233,926,761 bytes; backend92,390,605; Streamlit180,102,080. The model is
external, not included. These are local Docker size fields, not guaranteed
registry transfer sizes or complete deployment disk usage.

## Provider Facts and Exclusions

### Render Free / Hobby

0.1 CPU/512 MB per free web instance; no free private service. Ephemeral disk,
no persistent disk/SSH, public ingress. 750 workspace instance-hours monthly;
sleeping instances do not consume hours. Fifteen-minute idle sleep, roughly
one-minute wake; application/model load is additional. Two always-running
instances require1,488 hours in a31-day month, exceeding750. A2-hour session
plus a15-minute idle tail on both consumes approximately4.5 instance-hours,
excluding other activity. Builds use a separate quota.

No payment method is essential for zero-cost enforcement: documented excess
bandwidth suspends services and excess build usage disables builds instead of
billing. With a payment method, overages can bill; a budget alert is not a cap.
Current Hobby allowance:5GB outbound and500 starter pipeline minutes; verify
account dashboard values. External database/artifact traffic may trigger
additional suspension. No finite ephemeral-disk guarantee verified.
Sources: [free limits](https://render.com/docs/free),
[compute](https://render.com/docs/compute-plans),
[bandwidth](https://render.com/docs/outbound-bandwidth),
[build pipeline](https://render.com/docs/build-pipeline).

### Oracle Always Free ARM Candidate

Current published allowance:1,500 OCPU-hours and9,000 GB-hours/month (2 OCPUs,
12GB equivalent),200GB boot/block storage,10TB outbound. Home-region capacity
is not guaranteed; idle instances can be reclaimed. Builds run on the VM.
Propose one1-OCPU/4GB VM,50GB included boot disk:744 CPU-hours and2,976GB-hours
in31 days, before other account resources. Local1CPU/2GiB ML evidence supports
further testing, not a verified VM deployment or exact host sizing.
[Resource limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

Signup normally needs phone/card verification; official policy says no billing
unless account upgraded. Use only a non-upgraded standard Free Tier account,
Always Free resources, no trial-credit dependency, marketplace images or PAYG.
Account/region eligibility, capacity, networking and all allowance consumption
remain unverified. Stop if zero-spend status cannot be established.
[Account policy](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm).

### Hugging Face Docker Spaces

CPU Basic lists2vCPU/16GB/50GB ephemeral disk at no hourly cost, but current
docs require a paid plan to create Docker/Gradio compute Spaces. Reject for
this new strict-$0 deployment. Outbound ports80/443/8080 also exclude ordinary
Neo4j Bolt7687. Private app embedding has access restrictions. No provisioning
or architecture rewrite attempted. [Official overview](https://huggingface.co/docs/hub/spaces-overview).

### Streamlit Community Cloud and AuraDB Free

Community Cloud remains the free wrapper, not the ML host. Its documentation
labels resource figures approximate and dated: CPU0.078-2 cores,
RAM690MB-2.7GB, disk up to50GB; no stable bandwidth/build-minute guarantee
established. Sleeps after12 idle hours; viewer can manually wake. GitHub account
and repository authorization required, no paid upgrade selected. No separate
non-Streamlit public backend assumed. [Resources](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app),
[free service](https://docs.streamlit.io/deploy/streamlit-community-cloud).

AuraDB Free:50,000 nodes/175,000 relationships, no card, no time limit,
no included backups, pauses after3 inactive days. Dedicated CPU/RAM/disk byte
entitlements and monthly transfer/query quotas were not established; graph
capacity is not a throughput guarantee. Existing3,415/16,230/299-compound
manifest fits. Use certificate-verified neo4j+s; no paid upgrade or import
approved. [Official limits](https://neo4j.com/free-graph-database/).

## Alternatives Ranked

1. **Oracle non-upgraded Always Free candidate:** best remaining cloud resource
   fit. Run Fastify and FastAPI as separately supervised containers on one VM,
   internal-only ML port. Store model privately on included disk. Free HTTPS
   hostname/certificate, audience authentication, capacity and account eligibility
   remain blocking; not selected as a deployment-ready system.
2. **Existing user-controlled machine:** demonstrated application fit; no new
   cloud compute bill. Power/internet costs and reliability are not universally
   zero. Requires explicit approval and a verified free secure access method;
   no public tunnel opened or unprotected endpoint exposed.
3. **Two Render Free services:** frontend fits; ML demonstrably fails memory.
   Public ML would need server-to-server authentication (not just CORS/Origin
   rejection), but adding auth does not solve the memory limit. Rejected.
4. **One combined Render Free service:** ML alone exceeds the common512 MiB
   budget, so combining Node cannot fit the unchanged runtime. Not built or
   represented as tested combined deployment. Rejected on measured lower bound.
5. **Hugging Face new Docker Space:** paid-plan eligibility and Bolt networking
   make this unsuitable for the specified strict-$0 architecture. Rejected.

## Artifact and Zero-Spend Boundary

Preferred candidate: explicit approved secure copy onto private VM boot disk;
owner-only permissions, read-only model mount, checksum verified before load.
No public repository/object URL and no external artifact service needed. Local
mounted-model tests succeed; remote transfer/reboot/disk replacement untested.
Read-only process restart retains disk model; deleting the VM volume does not.
External upload still requires destination approval.

HF free private repositories advertise100GB, but authenticated download/redirect
handling, permissions and transfer policy have not been validated against our
strict bootstrap. Not selected. [Storage limits](https://huggingface.co/docs/hub/storage-limits).
R2's allowance is metered, not a verified hard-zero cap; rejected here even if
the model would fit its free allowance. No public model image or paid registry.

| Proposed component | Accepted spending | Acceptance state |
|---|---:|---|
| Streamlit wrapper | $0.00 | Provider account/browser acceptance pending |
| Oracle Always Free compute/included disk | $0.00 only | Conditional; non-PAYG status/capacity/allowances unverified |
| AuraDB Free | $0.00 | Account/destination/import approval pending |
| Model on included private disk | $0.00 additional | Destination/upload approval pending |
| HTTPS/access mechanism | $0.00 only | Not selected/verified; no purchased domain/gateway |

Actual cloud spending this task:$0.00. **No complete guaranteed-$0 deployment
has been established.** Do not substitute a paid plan when any free limit fails.

## Remaining Gates

All15 OS CVEs and sklearn advisory remain documented in the
[security assessment](sprint6-final-release-gate-assessment.md); no risk acceptance
or scanner policy changes. No shared history, request limits, sanitized errors,
model integrity and scientific outputs remain intact. No provider security or
browser/iframe acceptance performed; no deployed URLs.

Next: verify eligible non-upgraded account/home region and resource capacity;
approve exact free architecture and destinations; implement/review zero-cost
HTTPS and audience access without origin bypass; obtain explicit risk decisions;
approve PR58 then validate integration and approve PR57; record verified main
SHA; separately authorize upload/import/exposure. Follow the
[zero-cost runbook](../deployment/FREE_TIER_ACADEMIC_DEMO.md). Never deploy old main.
