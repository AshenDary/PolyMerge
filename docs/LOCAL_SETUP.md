# Local Setup

## Requirements

Use Python 3.11, Node.js 22 with npm (backend minimum 20), Git and an existing
Neo4j 5 database. Docker Desktop is needed only if your database uses Docker.
Allow several GB of disk and memory for dependencies, Neo4j and the approximately
240 MiB model. Earlier measured application memory is not a universal minimum.

macOS: install Python 3.11 and Node, then confirm `python3.11 --version`,
`node --version` and `npm --version` in Terminal. The shell wrappers also
recognize the repository's isolated ML interpreter once installed.
Windows 10/11: install Python 3.11 with the Python launcher and Node/npm on PATH.
Open a new terminal and confirm `py -3.11 --version`, `node --version` and
`npm --version`. Do not reuse Python 3.9 or silently upgrade scikit-learn.

## Private Configuration and Trusted Assets

1. Copy `.env.example` to `.env` in the repository root using your file manager.
   Set your existing `NEO4J_URI` (loopback Bolt), `NEO4J_USER` and
   `NEO4J_PASSWORD`. Keep credentials private.
2. Obtain the original model from the project owner through a trusted channel.
   Place it at `models/sprint5/random_forest_ddi_pipeline.joblib`, or set
   `POLYMERGE_DDI_MODEL_PATH` in `.env`. Tracked metadata stays unchanged.
3. Check SHA-256 against
   `2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
   macOS: `shasum -a 256 models/sprint5/random_forest_ddi_pipeline.joblib`.
   PowerShell: `Get-FileHash models/sprint5/random_forest_ddi_pipeline.joblib -Algorithm SHA256`.
   Size is 251,404,304 bytes. Never deserialize an untrusted joblib file.
4. Start the existing reviewed Neo4j database. Native Neo4j/Desktop users use
   their normal database Start control. Docker users start Docker Desktop and
   their existing container, for example `docker start polymerge_neo4j`.
   Do not run a reset, volume removal or graph loader against an existing database.
5. The expected graph is the tracked fragment: 3,415 nodes and 16,230 edges.
   Preflight compares complete IDs, names, kinds and edge identities, not counts
   alone. Missing/wrong data fails. A new teammate without the graph must arrange
   an owner-reviewed import or restore into a dedicated database separately.
   `scripts/load_fragment.py` is a data mutation tool, not launcher setup.

The old root Compose template includes legacy MySQL, example credentials and
published ports. It is not the recommended one-click provisioning procedure.
No database, model download or cloud resource is created by these launchers.

## First-Time Installation

Double-click **Setup-PolyMerge.command** on macOS or **Setup-PolyMerge.bat** on
Windows. Confirm the installation prompt. Alternatively:

```bash
python3.11 scripts/local_demo.py setup
```

Windows: `py -3.11 scripts/local_demo.py setup`.

Setup creates `.venv-demo-ml` from `ml_engine/requirements-dev.lock` and
`.venv-demo-ui` from `requirements-streamlit.lock`, using required hashes.
The ML environment includes regression tools. It runs `npm ci --ignore-scripts`
in backend, dependency integrity checks, model validation and a read-only graph
check. It refuses to modify pre-existing target environments.
`--yes` is an explicit noninteractive installation confirmation.

If installation was interrupted, inspect the two demo environments. Rename only
those newly created incomplete folders before rerunning setup; leave other
environments and database files untouched. If dependencies installed successfully
but graph/model preflight failed, fix assets/configuration and run the check below
instead of repeating setup.

## Daily Startup and Shutdown

Double-click **Start-PolyMerge.command** or **Start-PolyMerge.bat**.
Keep its terminal open. Successful startup prints **PolyMerge is ready.** and
opens Streamlit once. Defaults are ML 8000, backend 3000 and Streamlit 8501.
Every application binds to 127.0.0.1. No remote model/graph service is accepted.

To start a known existing Compose Neo4j container automatically, pass
`--neo4j-container polymerge_neo4j`, or set `POLYMERGE_NEO4J_CONTAINER` in
the launching shell. This option checks the container image and Compose service
identity; it never creates/imports data. Native installations must be started
manually. The environment option is read from the parent shell, not `.env`.

Double-click **Stop-PolyMerge.command** or **Stop-PolyMerge.bat**, or press Ctrl+C
in the launcher terminal. Stop authenticates to this repository's supervisor.
There is no PID-file kill command. Child groups are stopped on macOS; a Windows
Job Object contains descendants. The persistent Neo4j database is left running.

## Manual Alternative and Custom Ports

The shared supervisor is the supported manual alternative to double-clicking:

```bash
python3.11 scripts/local_demo.py start --ml-port 8016 --backend-port 3016 --streamlit-port 8516 --no-browser
python3.11 scripts/check_demo_readiness.py
python3.11 scripts/local_demo.py stop
```

Windows uses `py -3.11` instead of `python3.11`. Paths containing spaces are
supported; quote paths when invoking commands from another directory.
The supervisor starts these real entry points with matching local child URLs:

- ML environment: `python -m uvicorn main:app --host 127.0.0.1 --port <ml> --workers 1`, in `ml_engine/`.
- Backend: `node src/server.js`, in `backend/`.
- UI environment: `python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port <ui> --server.headless true --browser.gatherUsageStats false`, from root.

Use the supervisor to supply `ML_SERVICE_URL`, `POLYMERGE_FRONTEND_URL`,
`CORS_ORIGIN`, `STREAMLIT_ORIGIN`, `NODE_ENV=production`,
`POLYMERGE_LOCAL_DEMO=true`, `HOST=127.0.0.1`,
`POLYMERGE_ENABLE_LEGACY=false` and `POLYMERGE_REQUIRE_MODEL=true`.
Starting entry points independently requires reproducing that configuration;
a listening TCP port alone is not readiness.

Advanced existing Python 3.11 environments can be selected explicitly with
`POLYMERGE_ML_PYTHON` and `POLYMERGE_UI_PYTHON` in the parent shell.
They must pass the same compatibility checks; normal startup never installs.

## Readiness and Logs

Run `python3.11 scripts/check_demo_readiness.py --preflight` before services:
it checks runtimes, dependencies, model hash/metadata, graph identity and assets.
Without `--preflight`, it also checks the supervisor's actual service ports,
ML/backend `/ready`, Streamlit `/_stcore/health` and frontend identity.
PASS does not claim visual or native-platform acceptance; WARN identifies those
remaining checks. FAIL returns nonzero without modifying graph data.

Logs: `.polymerge/logs/launcher.log`, `fastapi.log`, `fastify.log`,
`streamlit.log`, and `database.log` when container integration is used.
Logs are replaced on each start; copy needed evidence before restarting.
Treat logs as private and redact connection details before sharing.
`.polymerge/state.json` contains a local control token and is never committed.

## Recovery

- **Occupied port:** no process is killed or reused. Stop the service you own,
  or choose three distinct alternate ports. Follow the newly printed URLs.
- **Neo4j unavailable:** start the existing database and verify credentials in
  private configuration. A graph mismatch needs owner-reviewed data recovery,
  not automatic import.
- **Model missing/checksum mismatch:** obtain the original trusted artifact.
  No substitute model or fallback prediction will be used.
- **Python/dependency failure:** use the isolated setup; do not combine Streamlit
  and ML packages or upgrade the frozen ML lock.
- **Service startup failure:** inspect its log. The supervisor stops its other
  children. Correct the cause and start again; there is no restart loop.
- **Wrapper problem:** open the printed Fastify URL directly. It hosts the same
  frontend and real APIs. A successful health check does not verify iframe rendering.
- **Stale lock after a crash:** first try Stop. If no authenticated endpoint
  responds, close the original launcher and confirm its managed service listeners
  are gone using Activity Monitor/Task Manager. Never kill by an old PID.
  Only then remove the stale `.polymerge/launcher.lock` directory and
  `.polymerge/state.json`. If uncertain, restart the computer before cleanup.
- **macOS permissions:** use `chmod +x *-PolyMerge.command` only if executable
  bits were lost during transfer. Open a trusted script through Finder's Open
  action if macOS blocks it; do not disable system security globally.

## Native Acceptance Still Required

On Windows 10 and 11, test a checkout path with spaces, actual Setup/Start/Stop
batch execution, environment discovery, Neo4j identity, all three readiness
endpoints, default-browser opening, iframe rendering, Ctrl+C and Stop shutdown.
Verify an unrelated listener survives an occupied-port error. Repeat after a
service exits unexpectedly. CI unit/package checks are not full-stack acceptance.

On macOS, double-click in Finder and verify browser opening and the same UI
checks. Terminal wrapper execution is not proof of Finder interaction.
See [UI checklist](sprint6-guided-demo.md) and [finalization audit](audits/local-demo-finalization.md).
