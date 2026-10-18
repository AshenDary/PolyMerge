# Main Branch Release Record

Verified 2026-10-19 for the **local academic demonstration**. The application
baseline is the main merge commit below. A later documentation-only commit does
not replace the frozen model, graph or application baseline. No public deployment
or clinical readiness is claimed.

## Integration Record

| Item | Confirmed state |
| --- | --- |
| Original main | `2edcc39bfe83296b00020e9d7894aa3d95889754` |
| Pre-merge backup | [`backup/pre-polymerge-final-demo`](https://github.com/AshenDary/PolyMerge/tree/backup/pre-polymerge-final-demo), same original-main SHA |
| [PR #58](https://github.com/AshenDary/PolyMerge/pull/58) | Merged into integration as `3fa24b814994ed5234f857dfa1b9bbbb67293b7d` |
| [PR #57](https://github.com/AshenDary/PolyMerge/pull/57) | Merged into main as `7fb6c0accad92790e63d5203aa8b73bb05bb1ec2` |
| Final-demo backup | [`backup/polymerge-final-local-demo`](https://github.com/AshenDary/PolyMerge/tree/backup/polymerge-final-local-demo), same final-main SHA |
| Release tag | None; no existing repository tag convention |

Both merges used GitHub's normal merge-commit path with expected PR head SHAs;
no administrator bypass or force-push was used. Main's file tree matched the
reviewed integration tree. The two backup branches preserve distinct recovery
points. The [pre-merge finalization audit](audits/local-demo-finalization.md)
retains its original dates and branch-state evidence rather than being rewritten.

## Final-Main Verification

| Criterion | Recorded result |
| --- | --- |
| Guided simulation, views, pagination, Research Takeaway and reset | Implemented; backend/frontend regression passed; browser visual acceptance remains pending |
| Local stack | Fastify, FastAPI, Streamlit and the reviewed local Neo4j graph passed launcher and readiness checks |
| Graph identity | Full source fragment verified, not counts alone: 3,415 nodes and 16,230 edges |
| Frozen Random Forest | SHA-256 `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`; 55 features; 313 prediction/probability rows matched the preserved baseline |
| Five real scenarios | Exact candidates and optimizer state matched preserved fixtures: 100/100/100/100/0 |
| Local regression | Backend 128 passed; ML 133 passed; scripts 27 passed, one Windows-only skip |
| GitHub CI | [PR #57 run](https://github.com/AshenDary/PolyMerge/actions/runs/39146677722): regression and native Windows launcher jobs passed; security and three container scanner jobs failed |
| Favicon/static assets | HTTP/MIME checks passed; browser-visible favicon acceptance pending |
| Documentation | At merge, 81 Markdown files and 185 local links checked with zero broken targets; see the later [documentation audit](audits/final-documentation-audit.md) for the current count |
| Shutdown | Launcher-owned app processes stopped; shared Neo4j left running |

These are dated results, not a guarantee about a future machine or changed
dependency environment. Run [Local Setup](LOCAL_SETUP.md), the read-only
`scripts/check_demo_readiness.py` check and the
[Final Demo Guide](FINAL_DEMO_GUIDE.md) before presenting. Research Takeaway
derives from the returned candidate data; it is not a separate model or a
clinical conclusion. The held-out evaluation was not rerun.

## Remaining Gates and Limits

The frozen scikit-learn 1.4.0 dependency retains advisory
`PYSEC-2024-110`. Trivy and Grype HIGH-severity container findings remain;
the scanners continue to fail visibly. Local functional success is **not**
cloud/production security clearance. See the
[security audit](audits/sprint6-final-release-gate-assessment.md) and
[container review](audits/sprint6-final-container-security-review.md) for the
dated findings; neither report is superseded by this local release record.

Native Windows launcher CI covered batch paths, process containment and locked
environments, not a full graph/model demo on Windows. Terminal macOS launch and
shutdown passed; Finder double-click, browser/iframe layout, keyboard/mobile
behavior and visible favicon still require manual acceptance. Follow the
[UI checklist](sprint6-guided-demo.md); do not represent HTTP/unit checks as
visual acceptance.

The approved scope is **loopback-only local academic demonstration** with the
original trusted model and reviewed graph. Do not expose this stack publicly,
interpret its candidates as prescriptions or claim paid/cloud deployment.
