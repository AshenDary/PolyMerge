#!/usr/bin/env bash
set -euo pipefail

image=${1:?image required}
service=${2:?service required}
case "$service" in backend|ml|streamlit) ;; *) exit 2 ;; esac

# No secrets, external networking, elevated capabilities, or writable image layers.
id=$(docker run -d --read-only --tmpfs /tmp:rw,nosuid,nodev,size=128m \
  --network none --cap-drop ALL --security-opt no-new-privileges "$image")
trap 'docker logs "$id"; docker rm -f "$id" >/dev/null' EXIT

check_runtime() {
  test "$(docker exec "$id" id -u)" != 0
  test -z "$(docker exec "$id" find /usr /bin /sbin -xdev -type f -perm /6000 -print)"
  docker exec "$id" sh -c 'test ! -w /app && test ! -w /usr/local'
  for attempt in $(seq 1 30); do
    test "$(docker inspect --format '{{.State.Running}}' "$id")" = true
    if [ "$(docker inspect --format '{{.State.Health.Status}}' "$id")" = healthy ]; then
      return 0
    fi
    sleep 5
  done
  return 1
}

check_service() {
if [ "$service" = backend ]; then
  docker exec "$id" node --input-type=module -e '
    const checks = [["/health",200],["/ready",503],["/api/history",404],["/api/drugs/test",404],["/api/candidate-sets/test/explain",404]];
    for (const [path,status] of checks) {
      const r = await fetch("http://127.0.0.1:"+process.env.PORT+path);
      if(r.status!==status) throw Error(path+": "+r.status);
      if(!r.headers.get("content-security-policy").endsWith("frame-ancestors '\''none'\''")) throw Error("framing");
      if(/joblib|neo4j:|stack|password/i.test(await r.text())) throw Error("error disclosure");
    }
  '
else
  docker exec "$id" python -c 'import importlib.metadata as m; assert not ({"pip", "setuptools", "wheel", "pytest"} & {d.metadata["Name"].lower() for d in m.distributions()})'
  if [ "$service" = ml ]; then
    docker exec "$id" python -c 'import rdkit, sklearn, numpy, neo4j; from rdkit import Chem; assert Chem.MolFromSmiles("CCO") is not None; assert sklearn.__version__ == "1.4.0"; assert numpy.__version__ == "1.26.4"'
    docker exec "$id" python -c '
import os, urllib.request, urllib.error
base = "http://127.0.0.1:" + os.environ["PORT"]
for path, expected, headers, data in [
    ("/health", 200, {}, None), ("/ready", 503, {}, None),
    ("/docs", 404, {}, None), ("/openapi.json", 404, {}, None),
    ("/api/diseases", 403, {"Origin": "https://evil.example"}, None),
    ("/predict/candidate-sets", 413, {"Content-Type": "application/json"}, b"x" * 40000),
]:
    try:
        response = urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=headers), timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.status == expected, (path, response.status)
        body = response.read().decode().lower()
        assert not any(token in body for token in ["joblib", "neo4j:", "password", "traceback"])
'
  fi
fi
}
check_runtime
check_service
docker restart "$id" >/dev/null
check_runtime
check_service
echo "$service: non-root, read-only, capability-free liveness and restart passed"
