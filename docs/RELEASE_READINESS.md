# Main Branch Release Readiness

Review date: 2026-10-18. This checklist is for the local academic demonstration.
The official demo baseline is the **post-merge main SHA**, which does not exist
yet. Use [Local Setup](LOCAL_SETUP.md) and [Final Demo Guide](FINAL_DEMO_GUIDE.md)
for operation. The [dated implementation audit](audits/local-demo-finalization.md)
contains the complete changed-file inventory and earlier verification.

## Current Branch Chain

| Item | Current state |
| --- | --- |
| PR #58: security/local demo into integration | Open; review-start head `caebc375498e5e08b23361db7bdbd98fa09ba766`; mergeable; no reviews |
| PR #57: integration into main | Open; head `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`; mergeable; no reviews |
| Main | `2edcc39bfe83296b00020e9d7894aa3d95889754`; finalization absent |
| Worktree | Clean at review start; final state requires a post-commit check |

PR #57 does not include PR #58's commits yet. Git history shows integration
contains the validated frontend and research work; PR #58 descends from it and
adds the local tooling, documentation, favicon and security changes. There is no
merge conflict reported for either PR. No merge has been performed.

## Release Criteria

| Criterion | Evidence or remaining action |
| --- | --- |
| Four-step simulation, views, pagination, takeaway, reset | Implemented; backend/frontend regression passed; browser visual acceptance pending |
| Fastify, FastAPI, Streamlit and Neo4j | Live loopback services reached readiness; actual two-disease analysis returned 100 graph-backed candidates |
| Frozen model and 55 features | SHA-256 `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`; 313-row parity passed again on the review branch |
| Five scenario parity | Exact full candidate/optimizer equality: 100/100/100/100/0; matching Research Takeaway for sampled candidates |
| macOS launch and shutdown | Terminal wrappers and cleanup passed; Finder/browser opening pending |
| Windows launch and shutdown | Native CI batch/path/process tests and both locked environments passed; real graph/model full stack pending |
| Favicon and static assets | SVG/ICO/PNG bytes and MIME types verified; visible browser favicon pending |
| Documentation | Root/component guides, architecture, setup and demo guide present; 81 Markdown files and 185 local links checked, zero broken |
| Repository hygiene | No tracked secret/model binary; verify clean tree after final commit |
| Regression | Backend 128, local ML 133, scripts 27 plus one Windows-only skip; hosted regression and Windows jobs passed at `caebc37` |
| Security | sklearn 1.4.0 advisory and container HIGH findings remain; scanner gates continue to fail |
| Main integration | Approval of #58 and #57, merges and post-merge validation pending |

## GitHub Policy and Security

The last CI run for PR #58 passed regression and native Windows launcher jobs.
The dependency audit failed on `PYSEC-2024-110` in both frozen ML locks. All
three container builds and runtime checks passed, while Trivy and Grype HIGH
policies failed. [CI evidence](https://github.com/AshenDary/PolyMerge/actions/runs/39115286727)
and historical package analysis remain visible; no finding has been suppressed.

GitHub reports both PRs as mergeable with an `UNSTABLE` check state. The classic
main protection endpoint returned no rule; the active named main ruleset reports
PR review and non-fast-forward rules but no required status-check rule in the
API response. Its ref include list is empty, so actual enforcement needs owner
confirmation. A failed CI job must still be presented to reviewers honestly;
API output alone does not establish whether GitHub will block the merge.

For a strictly local academic baseline, an owner may review a narrow release
decision that keeps all security jobs running and visible, records the frozen
runtime/container findings, prohibits public exposure, and accepts only the
verified local demo scope. This document proposes no CI change or automatic
exception. Security fixes or a documented owner decision remain review items.

## Exact Integration Order

1. Complete browser/iframe and real Windows acceptance, or record their explicit
   limits in the review. Inspect the latest CI and scientific parity evidence.
2. Review PR #58's full diff, findings and conversations; obtain explicit
   approval, then merge it into `integration/pre-deployment-main-sync`.
3. Confirm PR #57 now includes all PR #58 commits/files. Rerun PR #57 CI and
   review its complete diff against main, including any conflict resolution.
4. Obtain explicit approval for PR #57, then merge it into main. Do not push
   directly to main or bypass GitHub rules.
5. Fetch main, record the PR merge SHAs and exact new main SHA. On that commit,
   rerun regression, readiness, original model parity and the five scenarios.
   Verify no secrets, runtime logs, model binaries or temporary artifacts are
   tracked. Record the official presentation SHA only after those checks pass.

## Presentation Baseline Record

| Field | Value after approved integration |
| --- | --- |
| PR #58 merge SHA | Pending |
| PR #57 merge SHA | Pending |
| Official main SHA | Pending |
| Main regression and readiness | Pending |
| Browser/iframe acceptance | Pending |
| Windows full-stack acceptance | Pending |

The review candidate is the latest pushed head of PR #58. It is not a main
release SHA. Record its exact commit in the final handoff after the documentation
commit and hosted CI complete.
