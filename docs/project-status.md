# Project Status

As of 2026-10-18, PolyMerge is being finalized for a local academic demonstration.
No public cloud deployment is claimed or required.

## Implemented on the Review Branch

The four-step simulation, explicit Analyze-to-Review navigation, Research
Takeaway, verified rule mappings, supported-pair Random Forest inference,
security hardening, loopback local supervisor and favicon are implemented.
The graph, 55-feature contract, model binary and preserved research results
are unchanged. Graph evidence, configured rules and ML remain distinct.

## Review and Acceptance

PR #58 (`fix/pre-deployment-security-and-cloud`) targets
`integration/pre-deployment-main-sync`. PR #57 targets main.
Neither integration nor main should be merged without explicit approval.
The same PR chain keeps all finalization work reviewable without another dependency.

Native Windows full-stack acceptance and browser/iframe visual acceptance are
separate from unit and HTTP checks. Consult the dated
[finalization audit](audits/local-demo-finalization.md) for exact results and gaps;
do not infer readiness from historical test totals.

Public-deployment vulnerability gates remain unchanged. Known frozen-runtime
and container findings are not waived by the local-demo decision.
Historical deployment studies are indexed in [documentation](README.md).

## Demonstration

Use [Local Setup](LOCAL_SETUP.md), [Final Demo Guide](FINAL_DEMO_GUIDE.md) and
[UI acceptance](sprint6-guided-demo.md). The launcher verifies the original model
checksum and complete source graph identity and does not provision data.
An official main presentation SHA can be recorded only after approved merges
and final verification.
