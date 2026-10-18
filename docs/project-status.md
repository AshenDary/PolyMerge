# Project Status

As of 2026-10-19, PolyMerge is finalized on main for a local academic
demonstration. The verified application baseline is
`7fb6c0accad92790e63d5203aa8b73bb05bb1ec2`. Later documentation-only
commits do not change that application baseline. No public cloud deployment is
claimed or required.

## Implemented on Main

The four-step simulation, explicit Analyze-to-Review navigation, Research
Takeaway, verified rule mappings, supported-pair Random Forest inference,
security hardening, loopback local supervisor and favicon are implemented.
The graph, 55-feature contract, model binary and preserved research results
are unchanged. Graph evidence, configured rules and ML remain distinct.

## Integration and Acceptance

PR #58 merged into `integration/pre-deployment-main-sync` as
`3fa24b814994ed5234f857dfa1b9bbbb67293b7d`.
PR #57 merged that integration branch into main as
`7fb6c0accad92790e63d5203aa8b73bb05bb1ec2`.
The pre-merge and final-demo backup branches remain on GitHub. See the
[release record](RELEASE_READINESS.md) for verification details.

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
Use the verified application baseline above for the local presentation;
browser/iframe visuals and a complete native Windows graph/model run still
require manual acceptance.
