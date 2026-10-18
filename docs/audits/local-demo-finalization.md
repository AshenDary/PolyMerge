# Local Demo Finalization Audit

Date: 2026-10-18. Scope: local academic demonstration, not public deployment.
No model training, final held-out reevaluation, scientific-data changes, paid
resources, cloud provisioning, paper edits or presentation edits were performed.

## Branch Review

- Starting branch: `fix/pre-deployment-security-and-cloud`.
- Starting SHA: `cda2835863f1e1774bfb4b142f29a9cc2ab6e215`.
- Main: `2edcc39bfe83296b00020e9d7894aa3d95889754`.
- Integration: `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`.
- [PR #58](https://github.com/AshenDary/PolyMerge/pull/58): OPEN, targets
  `integration/pre-deployment-main-sync`.
- [PR #57](https://github.com/AshenDary/PolyMerge/pull/57): OPEN, targets main.
- No duplicate finalization PR, merge, force-push or branch deletion.
- Finalization stays on PR #58 because it already contains the integrated
  features/security work; this avoids another dependent review chain.
- Earlier uncommitted academic/free-tier evidence was preserved in commit
  `01792ae`. Launcher: `22db646`; branding: `f7e0ced`;
  native batch-entry test: `befb727`. Subsequent documentation commits are
  visible in the same PR history; use the final pushed branch HEAD for review.

Main does not yet include this finalization. No official main presentation SHA
is declared. After explicit approval, merge #58 into integration, verify #57's
diff and checks, obtain main approval, merge #57 and verify/record the resulting
main SHA. Do not bypass failing checks or equate local success with public release.

The classic protection endpoint reports no branch protection. The repository
ruleset named main is active and describes PR review/non-fast-forward/deletion
rules, but its returned ref include list is empty. No required status-check rule
was returned. Thus scanner failures are reported as failed release checks, not
asserted to be a confirmed branch-protection merge block.

## Implementation

Six thin Setup/Start/Stop wrappers call one standard-library Python supervisor.
Setup requires confirmation, Python 3.11 and npm, creates separate hash-locked
ML/UI environments and leaves existing environments untouched. Daily startup
never reinstalls. ML uses scikit-learn 1.4.0 and NumPy 1.26.4; UI uses Streamlit
1.66.0. The backend package contract is Node >=20 with Node 22 as baseline.

The supervisor validates source graph identity and model checksum before
starting one Uvicorn worker, Fastify and Streamlit on matching loopback ports.
It supports explicit startup of the existing Compose Neo4j service and never
creates/imports/reset data. Native Neo4j must already be started.
Authenticated local shutdown contains only managed application children.
POSIX groups and Windows Job Objects are used; Neo4j is left running.

Readiness checks dependencies, original model/metadata, graph identities,
ML/backend readiness, Streamlit health, frontend identity and exact served
favicon bytes. Logs and control state remain ignored under `.polymerge/`.
The local production-mode HTTP exception requires HOST=127.0.0.1; production
limits and disabled history/demo/raw prediction proxy routes remain enforced.

Favicon SVG/ICO/180px PNG are integrated into Fastify HTML and Streamlit,
including the existing Streamlit image build. Binary response bytes and MIME
types are tested. No dashboard redesign was performed.

## Local Verification

| Check | Result |
| --- | --- |
| First-time isolated setup | PASS, both locked environments and npm installed |
| Backend regression | 128 passed |
| ML regression with private artifact | 133 passed; two dependency deprecation warnings |
| Script regression before native-only batch test | 26 passed |
| Sprint 4 feature contract | PASS, 55 features; no cross-split pair leakage |
| Release metadata | PASS |
| JavaScript syntax and whitespace | PASS |
| Frozen golden inference | PASS, 313 rows, exact labels/probabilities/features |
| Five real scenarios | Exact candidate and optimization equality |
| macOS terminal Start/Stop wrappers | PASS, all three readiness endpoints, clean shutdown |
| Real checkout path containing spaces | PASS using explicit isolated interpreters/model |
| Streamlit AppTest | PASS, no script exceptions and correct iframe source |
| Browser automation | Unavailable: connected browser list empty |
| Finder double-click/default browser | Not verified |
| Windows full stack on Windows 10/11 | Pending native acceptance |

The native-only batch test is skipped on macOS; hosted Windows CI executes it.
The earlier hosted run at application commit `f7e0ced` passed native Windows
process-containment/path unit checks and Linux regression. Package-install and
container jobs were still running when this audit was drafted; consult the PR
checks and final review comment for the final CI outcome. Do not infer a complete
Windows demo from unit/package checks.

The path-with-spaces test used a real repository copy under a private temporary
directory, shared installed dependencies and the original model. It exposed an
interpreter symlink-resolution bug, fixed before commit: an explicit venv Python
must not be resolved to its base interpreter. A regression test covers this.

The first Streamlit AppTest exceeded its default three-second timeout; it passed
with a bounded 30-second allowance. AppTest checks Python execution and iframe
configuration, not actual browser rendering. No fake screenshots or browser
acceptance claims are included. See [manual checklist](../sprint6-guided-demo.md).

## Scientific Parity

Artifact SHA-256:
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.

Size: 251,404,304 bytes. Model:
`RandomForestClassifier-sprint5-v1-65e9834666ad19c5`.

The preserved baseline `/tmp/polymerge-final-security/frozen-1.4.0.json` and
five owner-provided fixtures in `/tmp/polymerge-integration/` were read only;
no fixture was regenerated. New probe output:
`/tmp/polymerge-local-final-frozen.json` (local evidence, not a runtime asset).

| Scenario | Exact returned candidates |
| --- | ---: |
| hypertension | 100 |
| hypertension + diabetes | 100 |
| coronary + atherosclerosis | 100 |
| four diseases | 100 |
| no treatments | 0 |

Equality includes full candidates, ranks, graph evidence, rule outcomes, mapping
coverage and pair prediction payloads, plus optimization metadata. Query IDs and
timestamps are not scientific parity targets. The source graph has 3,415 nodes
and 16,230 edges. Nine positive canonical rule mappings remain incomplete.
Existing frontend tests cover Research Takeaway, reset and stale responses.

The feature-contract validator audits split structure, not final-model test
performance. The held-out final evaluation was not rerun.

## Documentation Review

The root README now documents the real iframe architecture, local-only setup,
separate runtimes, frozen model, explicit Analyze-to-Review flow, limitations,
tests, team and review status. Component guides are concise and link to the shared
setup rather than duplicating instructions. Current API scope distinguishes
disabled legacy routes. Graph/algorithm docs no longer deny existing pair inference.

[Documentation inventory](../README.md) classifies every Markdown file.
Historical sprint plans, audits and deployment studies retain their dated
findings. Relative file links are checked; external URLs and all historical
heading anchors are not claimed as verified. Architecture and final demo guides
include actual fallback/recovery steps and a fixture-supported multi-drug example.

## Security and Outstanding Acceptance

Local function and public-deployment security are separate decisions.
The existing frozen scikit-learn PYSEC-2024-110 finding and high-severity container
findings remain unresolved. No suppressions, scanner threshold changes or
replacement model were introduced. The previous full run is
[39059460054](https://github.com/AshenDary/PolyMerge/actions/runs/39059460054);
new finalization checks run on the same PR. Do not claim CI is green.

Outstanding: native full-stack Windows 10/11 acceptance, Finder/browser launch,
desktop/mobile visuals, keyboard/console checks, visible favicon and actual
Streamlit iframe rendering. Follow [Local Setup](../LOCAL_SETUP.md) and
[Final Demo Guide](../FINAL_DEMO_GUIDE.md). Main review/approval also remains open.

The finalization is partial until those acceptance checks are completed.

## Complete Changed-File Inventory

- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `README.md`
- `Setup-PolyMerge.bat`
- `Setup-PolyMerge.command`
- `Start-PolyMerge.bat`
- `Start-PolyMerge.command`
- `Stop-PolyMerge.bat`
- `Stop-PolyMerge.command`
- `TEAM.md`
- `backend/README.md`
- `backend/src/explainability/README.md`
- `backend/src/security.js`
- `backend/src/server.js`
- `backend/tests/local-demo-security.test.js`
- `backend/tests/model-comparison.test.js`
- `data/README.md`
- `deploy/Dockerfile.streamlit`
- `docs/ARCHITECTURE.md`
- `docs/FINAL_DEMO_GUIDE.md`
- `docs/LOCAL_SETUP.md`
- `docs/README.md`
- `docs/algorithm-limitations.md`
- `docs/api.md`
- `docs/audits/local-demo-finalization.md`
- `docs/audits/security-evidence/free-tier-resources.json`
- `docs/audits/sprint6-academic-demo-assessment.md`
- `docs/audits/sprint6-free-tier-feasibility.md`
- `docs/deployment/ACADEMIC_DEMO.md`
- `docs/deployment/FREE_TIER_ACADEMIC_DEMO.md`
- `docs/deployment/README.md`
- `docs/deployment/STREAMLIT_RENDER_AURADB.md`
- `docs/knowledge-graph-schema.md`
- `docs/project-status.md`
- `docs/sprint6-guided-demo.md`
- `frontend/README.md`
- `frontend/apple-touch-icon.png`
- `frontend/favicon.ico`
- `frontend/favicon.svg`
- `frontend/index.html`
- `ml_engine/README.md`
- `ml_engine/scripts/README_sprint4.md`
- `scripts/README.md`
- `scripts/check_demo_readiness.py`
- `scripts/demo_preflight.py`
- `scripts/local_demo.py`
- `scripts/tests/test_local_demo.py`
- `streamlit_app.py`
