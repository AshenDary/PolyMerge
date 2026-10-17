# Release checklist

Unchecked items are required work, not implied approvals.

- [x] Audit from latest frontend-repair base, preserve existing work, separate audit branch.
- [x] Local backend, frontend behavior, ML and feature-contract tests.
- [x] Frozen artifact size/hash verified without final evaluation/retraining.
- [x] Three non-root Dockerfiles, model/env exclusion and private-loopback Compose template.
- [x] SHA-pinned read-only CI, blocking dependency checks, disabled staging template.
- [x] Smoke script and tests; real local inference and graph inspection.
- [ ] Resolve applicable dependency advisories; review frozen-model compatibility separately.
- [x] Fix optimizer merged-set rule gap with safe-alternative/uncovered regression cases.
- [ ] Resolve hard-rule label/graph-ID mismatch.
- [ ] Bound generation effort and isolate blocking ML work; test concurrent health and cancellation.
- [ ] Add authentication/access gateway, rate limits, history ownership/TTL and unique query IDs.
- [ ] Restrict CORS, CSP/frame policy, health/error disclosure and legacy demo routes.
- [ ] All GitHub CI checks successful at the intended merge/release SHA.
- [ ] Container builds/runtime checked on target architecture; record image digests and locked dependencies.
- [ ] Jared approves hosting, budget, region, graph/data redistribution and private artifact distribution.
- [ ] Private graph loaded/verified with read-only credentials; backups documented.
- [ ] Model privately mounted, checksum/version verified, memory measured under representative workload.
- [ ] Protected staging Environment reviewers/main-only policy and independently verified SSH host key.
- [ ] Real HTTPS frontend, optional Streamlit URL and matching iframe origin policy.
- [ ] Staging smoke with real graph and applied pair inference passes.
- [ ] Browser desktop/mobile, keyboard, contrast, iframe console, reset-race and second simulation acceptance.
- [ ] Previous release images/model/graph snapshot retained and rollback rehearsed without DB destruction.
- [ ] Separate production approval and protected production Environment; promote tested digests only.

No PR, merge, hosting purchase, DNS update, public deployment, database exposure or artifact publication is authorized by this checklist.
