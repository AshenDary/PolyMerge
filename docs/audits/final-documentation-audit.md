# Final Repository Documentation Audit

Audit date: 2026-10-19. Starting main:
`7fb6c0accad92790e63d5203aa8b73bb05bb1ec2` (verified local-demo
application baseline). This is a documentation-only review; no model, graph,
dependency, workflow or application logic was changed.

## Scope and Inventory

The audit scanned **82 Markdown files**, including **11 README files**. The
[documentation index](../README.md#complete-markdown-inventory) lists every
file and its classification. This action matrix records the live files and
representative historical groups; files not named as updated were intentionally
left unchanged after review.

| File or group | Purpose | Classification | Finding | Action |
| --- | --- | --- | --- | --- |
| [Root README](../../README.md) | Overview, setup and verification | Active documentation | Main merge described as pending; tests omitted direct scripts suite | Update |
| [Team](../../TEAM.md) | Ownership and handoff | Active documentation | Review-chain wording implied a pending main merge | Update |
| [Backend README](../../backend/README.md) | Fastify responsibilities | Component documentation | Routes, security mode and setup link matched source | Keep |
| [Frontend README](../../frontend/README.md) | UI and static assets | Component documentation | Workflow and favicon paths matched source | Keep |
| [ML README](../../ml_engine/README.md) | FastAPI, graph and model | Component documentation | Locked environment and inference scope matched source | Keep |
| [Scripts README](../../scripts/README.md) | Supervisor and checks | Component documentation | System-Python command could lack ML dependencies | Update |
| [Data README](../../data/README.md), [rules README](../../data/rules/README.md) | Provenance and mappings | Research methodology | Research boundaries and tracked paths remained accurate | Keep |
| [Explainability README](../../backend/src/explainability/README.md) | Evidence adapters | Component documentation | No current-release claim needing correction | Keep |
| [Sprint 4 scripts README](../../ml_engine/scripts/README_sprint4.md) | Earlier experiment workflow | Superseded guide | Historical instructions, not local demo setup | Keep |
| [Documentation index](../README.md) | Navigation and classifications | Active documentation | Needed current baseline and this audit entry | Update |
| [Architecture](../ARCHITECTURE.md) | Local service/data flow | Active documentation | Streamlit wrapper, Fastify, FastAPI, Neo4j and model flow matched source | Keep |
| [Local Setup](../LOCAL_SETUP.md) | Cross-platform operations | Development guide | Launcher arguments, prerequisites, ports and recovery matched source | Keep |
| [Final Demo Guide](../FINAL_DEMO_GUIDE.md) | Presentation workflow | Development guide | Final link implied main baseline still pending | Update |
| [Release record](../RELEASE_READINESS.md) | Main merge and gates | Active documentation | PRs #58/#57 and main incorrectly marked open/pending | Update |
| [API contract](../api.md) | Routes and response fields | API contract | Active and legacy route distinction matched source | Keep |
| [Algorithm limitations](../algorithm-limitations.md) | Scientific boundaries | Research methodology | "Hard safety" wording overstated configured rules | Update |
| [Graph schema](../knowledge-graph-schema.md) | Graph scope | Research methodology | No inaccurate current-release claim found | Keep |
| [Project status](../project-status.md) | Current state | Active documentation | Review branch and PR merges marked pending | Update |
| [UI acceptance](../sprint6-guided-demo.md) | Browser checklist | Development guide | Pending visual acceptance remains truthful | Keep |
| [Deployment index](../deployment/README.md) | Historical cloud guides | Superseded guide | Already identifies local-only plan and unresolved gates | Keep |
| `docs/deployment/*.md`, `docs/audits/sprint6-*.md` | Feasibility, security and incident evidence | Historical audit | Dated findings must remain intact | Keep |
| `Sprints/**/*.md`, research reports, `CHANGELOG.md`, `ROADMAP.md` | Research and development history | Historical audit/research methodology | Past plans and metrics are not current feature claims | Keep |

The index also classifies internal handoffs, data dictionaries and the remaining
research reports individually. Historical cloud options (Render, Streamlit
Community Cloud, AuraDB and Oracle Always Free) were investigated but not
selected for this presentation; they are not active deployment instructions.

## Source and Science Checks

- `backend/package.json`, `backend/src/server.js` and `backend/src/security.js`:
  Node >=20, Fastify routes, static assets, local-demo restrictions and legacy
  route boundaries.
- `ml_engine/main.py`, `ml_engine/app/services/`,
  `data/rules/research_rule_mapping.json` and tracked model metadata: graph
  coverage, incomplete configured research rules, deterministic optimizer and
  frozen 55-feature pairwise DDI severity inference.
- `frontend/app.js`, `frontend/index.html`, `streamlit_app.py` and favicon files:
  four-step simulation, Simple/Researcher views, Research Takeaway and wrapper.
- `scripts/local_demo.py`, `scripts/demo_preflight.py`, launchers, Python locks
  and `.github/workflows/ci.yml`: platform commands, graph/model checks, CI gates
  and local shutdown behavior.
- Preserved Sprint 3-5 research reports remain the authority for the scientific
  metrics. No held-out evaluation was rerun; no result or fixture was rewritten.

The verified application baseline remains main merge
`7fb6c0accad92790e63d5203aa8b73bb05bb1ec2`, with PR #58 merge
`3fa24b814994ed5234f857dfa1b9bbbb67293b7d` in its history. Subsequent
documentation commits must not be presented as model or graph changes.

## Validation and Limits

At the pre-commit check: **82 Markdown files, 11 README files, 217 local links,
2 local heading anchors, 0 broken targets or anchors, and 0 unclosed code
fences**. All 59 table separators had matching header column counts. Duplicate
heading text occurs in historical issue templates/changelogs and the separate
backend/ML sections of the API guide; no checked local anchor depended on those
duplicates. Broken links found/fixed: **0/0**. One existing trailing-whitespace
warning remains in the historical `docs/sprint5-explainability-integration.md`;
its dated content was left intact. Changed files passed `git diff --check`.
External site availability was not used to invalidate historical links.

Updated files: `README.md`, `TEAM.md`, `scripts/README.md`, `docs/README.md`,
`docs/FINAL_DEMO_GUIDE.md`, `docs/RELEASE_READINESS.md`,
`docs/algorithm-limitations.md`, `docs/project-status.md`, and this report.
The other **73 Markdown files** were reviewed and intentionally kept unchanged.

Unresolved documentation-dependent acceptance is limited to real browser/iframe
visual review and a full native Windows graph/model rehearsal. The frozen
scikit-learn advisory and container HIGH findings remain documented in the
[release record](../RELEASE_READINESS.md) and historical security audits. Passing
local regression does not turn those scanner gates green or make the system
production-ready.
