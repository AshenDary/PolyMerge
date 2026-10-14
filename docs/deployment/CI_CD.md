# CI and gated release

Status: prepared, not authorized for public deployment. See the [audit](../audits/sprint6-final-project-audit.md) for measured results and security blockers.

## Continuous integration

There were no existing `.github/workflows` files at the audited base. `ci.yml` now runs on PRs to main, pushes to main and the audit branch, and manual dispatch. It has read-only repository permissions, SHA-pinned actions, cancellation of superseded runs, time limits, Node 22 and Python 3.11.

Required branch checks should be `regression`, `security`, and all three `containers` matrix checks. Configure protection in GitHub; this task does not change repository settings. Node uses `npm ci` and the committed lockfile. Python top-level versions are pinned but transitive dependencies are not fully locked; a reviewed lock and base-image digests remain release work. Pip/npm caches contain dependencies, not models or credentials.

- Regression: all backend tests (including frontend behavior), ML fixture tests, frontend syntax, Sprint 4 structural/preprocessing validator, frozen metadata checks, deployment-check unit tests, diff whitespace and tracked runtime-artifact checks.
- Security: npm production audit and pip-audit for ML/Streamlit. Findings fail the job, without suppression or automatic upgrades. The tracked-file gate is not a comprehensive secret-history scanner.
- Containers: build three images without publishing; start each and require Docker liveness. ML missing-artifact liveness is intentional, not inference readiness. Real inference requires the separately provisioned private model and graph.

Unit CI never needs the 251 MB artifact, live Neo4j, MySQL, hosting secrets or production networking. Tests using tiny synthetic trained fixtures do not retrain the frozen research model. `validate_sprint4_contract.py` reads holdout data to verify split/feature/preprocessing structure; it does not predict or evaluate holdout labels. No final-evaluation or training scripts are scheduled.

One external-data integration test explicitly skips when all licensed raw DDInter downloads are absent. If any raw files are present, missing/corrupt remaining files still fail. Tracked manifest assertions and synthetic source-loader checksum/schema tests always execute. Local full-source suite: 85 passed; clean-checkout suite: 84 passed, one external-data skip. Do not describe the skipped download check as CI-verified raw-source integrity.

## Deployment template

`deploy/staging-workflow.yml.disabled` is deliberately outside `.github/workflows`. It cannot trigger. There is no public deployment action on feature-branch pushes.

After Jared approves a target AND security blockers are remediated:

1. Provision a private staging host, Docker Compose v2, Python >=3.10, graph, trusted model, TLS/access gateway and a dedicated deployment account.
2. Configure a protected GitHub `staging` Environment: required reviewer, prevent self-review where supported, main-only deployment branches. Confirm these controls are supported by the repository's plan before enabling deployment.
3. Put `STAGING_SSH_KEY` and independently verified `STAGING_KNOWN_HOSTS` in environment secrets. Put `STAGING_SSH_HOST` and `STAGING_DEPLOY_ENABLED=true` in environment variables. Never disable SSH host-key verification.
4. Install a reviewed copy of `deploy/release.sh` at `/srv/polymerge/release.sh`, outside writable release worktrees. Provision `/srv/polymerge/repository` with read-only origin access, `/srv/polymerge/releases`, and owner-only `/srv/polymerge/staging.env`.
5. Move the template into `.github/workflows` in a reviewed change. Dispatch on main. The job requires the latest push CI for that exact commit to succeed. The host independently verifies that SHA is an ancestor of origin/main.
6. The host creates a detached release worktree, builds SHA-tagged images, starts only application containers, waits for liveness, then runs real private smoke inference. A failed build or smoke exits nonzero; it is not a successful release.

The deployment account can control Docker and must be treated as privileged. Restrict its key/network access; prefer a dedicated staging machine. No database schema migration is part of this procedure. The release script refuses an existing worktree; a retry must be operator-reviewed, not blindly delete existing releases.

## Promotion

Staging -> successful smoke evidence -> browser acceptance -> Jared/manual production approval. Production deployment is intentionally not implemented or enabled without a real target. Configure a separate protected production Environment in the later authorized task. Promote the exact tested image digests, model hash and graph snapshot; do not rebuild floating dependencies during promotion. Retain those digests and the previous release for rollback. The staging template builds on the host, so capture resulting image IDs/digests after it runs; a source SHA alone does not make Python transitive dependencies immutable.

## Verification commands

```sh
actionlint .github/workflows/ci.yml deploy/staging-workflow.yml.disabled
bash -n deploy/release.sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/check_release_metadata.py
gh run list --branch sprint6/jared/final-audit-cicd
```

Use `docker compose -f deploy/compose.staging.yml config --quiet` with a protected env file. Do not print expanded Compose configuration in shared logs because it includes credentials. YAML parsing alone is not workflow acceptance; inspect actual GitHub job logs and container checks. Current remote results are recorded in the audit.
