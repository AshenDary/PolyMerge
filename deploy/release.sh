#!/usr/bin/env bash
set -euo pipefail
# Run on a pre-provisioned, trusted staging host. Never creates databases.
sha=${1:?Supply reviewed full commit SHA}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "${POLYMERGE_DEPLOY_APPROVED:-}" == "staging" ]] || { echo 'Staging approval missing'; exit 2; }
repo=/srv/polymerge/repository
release=/srv/polymerge/releases/$sha
git -C "$repo" fetch origin main
git -C "$repo" merge-base --is-ancestor "$sha" origin/main
test ! -e "$release"
git -C "$repo" worktree add --detach "$release" "$sha"
cd "$release"
export RELEASE_SHA="$sha"
compose=(docker compose --project-name polymerge-staging --env-file /srv/polymerge/staging.env -f deploy/compose.staging.yml)
"${compose[@]}" build --pull
"${compose[@]}" up -d --wait --wait-timeout 180
python3 scripts/deployment_smoke.py --frontend http://127.0.0.1:3000 --ml http://127.0.0.1:8000 --streamlit http://127.0.0.1:8501 --query
# A failed smoke test exits nonzero. Operator selects rollback; no database mutation here.
