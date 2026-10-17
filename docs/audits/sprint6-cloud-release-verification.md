# Cloud Release Verification

Date: 2026-10-18 (Asia/Manila). **DEPLOYMENT BLOCKED; NOT LIVE.**

## Source and Approval State

- Main: `2edcc39bfe83296b00020e9d7894aa3d95889754`, not synchronized.
- Integration PR: [#57](https://github.com/AshenDary/PolyMerge/pull/57), open.
- Security work: `fix/pre-deployment-security-and-cloud`, based on integration
  `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`.
- Security PR URL and final hosted checks are recorded in the PR handoff once run.
- Approved deployment SHA: **none**. Main merge approval: **not granted**.
- Cloud accounts/budgets, model destination/upload, graph target/import,
  public exposure and continuous deployment approvals: **not granted**.

## Verified Locally

| Check | Result |
| --- | --- |
| Backend and frontend behavior | 120 passed |
| Updated Python 3.11 ML suite | 127 passed, two dependency warnings retained |
| Script tests | 10 passed |
| Feature contract, metadata, frontend syntax, diff whitespace | PASS |
| Frozen artifact | Required SHA-256 verified; unchanged |
| Runtime parity | Exact classes/probabilities across old, updated and Linux runtimes |
| Five live scenarios | Exact candidate and optimizer payload equality |
| All three Docker builds | PASS, Linux ARM64 |
| All three isolated container liveness checks | Healthy; temporary containers removed |
| Live graph identities and edges | Exact 3,415-node / 16,230-edge CSV parity |
| Streamlit AppTest | HTTPS iframe-source check passed |
| Browser discovery | No browser available; visual/keyboard/mobile acceptance pending |
| npm production audit | Zero findings |
| ML/development audit | One unresolved scikit-learn advisory each |
| Streamlit dependency audit | Zero findings |
| Runtime-image scan | Remaining HIGH/CRITICAL OS findings; not accepted |

Local hardened services were exercised on loopback ports 3004/8004, not published
to a cloud provider. Original local services were left untouched. Evidence:
`/tmp/polymerge-security-live`, `/tmp/polymerge-integration`,
`/tmp/polymerge-frozen-baseline.json`, `/tmp/polymerge-frozen-py311.json`,
`/tmp/polymerge-container-security`. These machine-local files are not cloud
acceptance records. No held-out model evaluation was run.

## Provider State

| Component | Status | Live URL |
| --- | --- | --- |
| Streamlit Community Cloud | Not created/changed | None |
| Render public Fastify | Not created/changed | None |
| Render private FastAPI | Not created/changed | None |
| Neo4j AuraDB | No target approved; no import | None |
| Private model storage | R2 proposed; not approved/uploaded | None |

## Release Gates

Resolve or explicitly review remaining scikit-learn and container advisories;
do not bypass failing CI. Complete browser embedding acceptance and trusted-proxy
quota verification. Obtain authorized PR merge, verify reviewed main SHA, approve
costs and exact transfer destinations, then proceed with the ordered deployment
in [the runbook](../deployment/STREAMLIT_RENDER_AURADB.md). The estimated baseline
is $32/month; the Professional Aura alternative is about $97.70/month, with
variable costs excluded. These are estimates, not approved charges.

The full security evidence and limitations are in
[the remediation audit](sprint6-cloud-security-remediation.md). Scientific
coverage limitations and lack of clinical validation remain unchanged.
