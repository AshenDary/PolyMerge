"""Standard-library local supervisor; never provision data or kill foreign PIDs."""
from __future__ import annotations

import argparse
import hmac
import http.server
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.polymerge'


class DemoError(RuntimeError):
    pass


def message(value: str) -> None:
    sys.stdout.write(value + '\n')
    sys.stdout.flush()


def interpreter(folder: str, override: str) -> Path:
    value = os.getenv(override)
    # Resolving a venv's Python symlink would silently select the base interpreter.
    return Path(value).expanduser().absolute() if value else ROOT / folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def checked(command: list[str], *, timeout: int = 60, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DemoError('Required command unavailable or timed out; see docs/LOCAL_SETUP.md.') from error
    if result.returncode:
        # Dependency/database errors can contain connection strings. Never echo them.
        raise DemoError('Preflight command failed; check runtime dependencies and local database configuration.')
    return result.stdout.strip()


def runtimes() -> tuple[Path, Path, str]:
    ml = interpreter('.venv-demo-ml', 'POLYMERGE_ML_PYTHON')
    ui = interpreter('.venv-demo-ui', 'POLYMERGE_UI_PYTHON')
    for python in (ml, ui):
        if not python.is_file():
            raise DemoError('Python environment missing. Run Setup-PolyMerge for first-time setup.')
        if checked([str(python), '-c', 'import sys; print("%s.%s" % sys.version_info[:2])']) != '3.11':
            raise DemoError('Python 3.11 is required. Existing environments will not be modified automatically.')
    node = shutil.which('node')
    if not node or not shutil.which('npm'):
        raise DemoError('Node.js 22 LTS and npm must be installed and available on PATH.')
    version = checked([node, '--version'])
    if int(version.lstrip('v').split('.')[0]) < 20:
        raise DemoError('Node.js >=20 is required; the documented baseline is Node.js 22 LTS.')
    checked([node, '--input-type=module', '-e', "await import('./backend/node_modules/fastify/fastify.js')"])
    for python in (ml, ui):
        checked([str(python), '-m', 'pip', 'check'])
    checked([str(ui), '-c', 'import streamlit; assert streamlit.__version__ == "1.66.0"'])
    return ml, ui, node


def ports(args: argparse.Namespace) -> dict[str, int]:
    values = {'ml': args.ml_port, 'backend': args.backend_port, 'streamlit': args.streamlit_port}
    if any(not 1024 <= port <= 65535 for port in values.values()) or len(set(values.values())) != 3:
        raise DemoError('Choose three distinct ports between 1024 and 65535.')
    return values


def require_free(values: dict[str, int]) -> None:
    for port in values.values():
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
            except OSError as error:
                raise DemoError(f'Port {port} is already in use. No existing process was stopped.') from error


def probe(ml: Path, *, graph: bool = True) -> dict:
    command = [str(ml), str(ROOT / 'scripts/demo_preflight.py')]
    if not graph:
        command.append('--without-graph')
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
        payload = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise DemoError('ML preflight failed or timed out. Verify Python 3.11 and locked dependencies.') from error
    if result.returncode:
        raise DemoError(payload.get('error', 'Model or graph preflight failed.'))
    return payload


def database_start(name: str | None) -> None:
    if not name:
        return
    docker = shutil.which('docker')
    if not docker:
        raise DemoError('Docker is unavailable. Start Docker Desktop or start native Neo4j manually.')
    try:
        value = json.loads(checked([docker, 'inspect', name, '--format', '{{json .}}']))
    except (DemoError, ValueError) as error:
        raise DemoError('The named existing Neo4j container was not found. No database was created.') from error
    labels = value.get('Config', {}).get('Labels') or {}
    image = value.get('Config', {}).get('Image', '')
    if not image.startswith('neo4j:') or labels.get('com.docker.compose.service') != 'neo4j':
        raise DemoError('Container identity is not the supported Compose Neo4j service; start it manually.')
    if not value['State']['Running']:
        checked([docker, 'start', name])
    # Neo4j is shared state: even if started here, Stop deliberately leaves it running.
    (RUNTIME / 'logs/database.log').write_text('Verified existing Neo4j container; no data mutations.\n')


def http_get(url: str) -> bytes:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=3) as response:
        return response.read(2_000_000)


def ready(url: str, expected: dict | None = None) -> bool:
    try:
        body = http_get(url)
        return all(json.loads(body).get(key) == value for key, value in expected.items()) if expected else body.strip() == b'ok'
    except (OSError, ValueError, urllib.error.URLError):
        return False


class WindowsJob:
    """Contain all descendant processes even if a service parent exits early."""
    def __init__(self) -> None:
        self.handle = None
        if os.name != 'nt':
            return
        import ctypes
        from ctypes import wintypes

        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('read_ops', 'write_ops', 'other_ops', 'read', 'write', 'other')]

        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]

        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise DemoError('Windows process containment could not be initialized.')

    def assign(self, process: subprocess.Popen) -> None:
        if self.handle and not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            process.kill()
            process.wait()
            raise DemoError('Windows could not contain the child process; startup stopped.')

    def close(self) -> None:
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def stop_children(children: list[subprocess.Popen], job: WindowsJob) -> None:
    for process in reversed(children):
        if process.poll() is not None:
            continue
        try:
            if os.name == 'nt':
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    deadline = time.monotonic() + 8
    for process in children:
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    job.close()
    for process in children:
        if process.poll() is None:
            process.kill()
        process.wait()


def stop() -> None:
    try:
        state = json.loads((RUNTIME / 'state.json').read_text())
        port = int(state['control_port'])
        if not 1 <= port <= 65535:
            raise ValueError('port')
        request = urllib.request.Request(f'http://127.0.0.1:{port}/stop', data=b'', method='POST',
                                         headers={'Authorization': 'Bearer ' + state['token']})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=5) as response:
            if response.read() != b'PolyMerge stopping':
                raise ValueError('identity')
        for _ in range(100):
            if not (RUNTIME / 'state.json').exists():
                message('PolyMerge stopped. Neo4j was left running; no database data was changed.')
                return
            time.sleep(0.2)
        raise DemoError('Shutdown is still in progress; inspect the launcher terminal.')
    except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
        raise DemoError('No verified launcher control endpoint responded. No PID was killed. See stale-state recovery in docs/LOCAL_SETUP.md.') from error


def launch(args: argparse.Namespace) -> None:
    RUNTIME.mkdir(exist_ok=True, mode=0o700)
    lock = RUNTIME / 'launcher.lock'
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as error:
        raise DemoError('A launcher lock already exists. Use Stop-PolyMerge; do not start duplicate services.') from error
    children: list[subprocess.Popen] = []
    streams = []
    control = None
    job = None
    stopped = threading.Event()
    try:
        job = WindowsJob()
        (RUNTIME / 'logs').mkdir(exist_ok=True, mode=0o700)
        (RUNTIME / 'logs/launcher.log').write_text('Starting local-only PolyMerge supervisor.\n')
        ml, ui, node = runtimes()
        values = ports(args)
        require_free(values)
        probe(ml, graph=False)
        database_start(args.neo4j_container)
        database_deadline = time.monotonic() + args.timeout
        while True:
            try:
                probe(ml)
                break
            except DemoError:
                if time.monotonic() >= database_deadline or not args.neo4j_container:
                    raise
                time.sleep(2)
        token = secrets.token_urlsafe(32)

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                authorized = hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token)
                if self.path != '/stop' or not authorized:
                    self.send_error(403)
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'PolyMerge stopping')
                stopped.set()

            def log_message(self, *_: object) -> None:
                pass

        control = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        control.daemon_threads = True
        threading.Thread(target=control.serve_forever, daemon=True).start()
        state = {'control_port': control.server_port, 'token': token, 'ports': values}
        with (RUNTIME / 'state.json').open('x') as stream:
            os.chmod(stream.name, 0o600)
            json.dump(state, stream)
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, lambda *_: stopped.set())
        if os.name == 'nt':
            signal.signal(signal.SIGBREAK, lambda *_: stopped.set())
        backend_url = f'http://127.0.0.1:{values["backend"]}'
        ml_url = f'http://127.0.0.1:{values["ml"]}'
        ui_url = f'http://127.0.0.1:{values["streamlit"]}'
        env = os.environ.copy()
        env.update({'NODE_ENV': 'production', 'POLYMERGE_LOCAL_DEMO': 'true', 'POLYMERGE_ENABLE_LEGACY': 'false', 'HOST': '127.0.0.1', 'PORT': str(values['backend']),
                    'ML_SERVICE_URL': ml_url, 'POLYMERGE_FRONTEND_URL': backend_url,
                    'CORS_ORIGIN': backend_url, 'STREAMLIT_ORIGIN': ui_url,
                    'TRUST_PROXY_CIDRS': '', 'POLYMERGE_REQUIRE_MODEL': 'true', 'PYTHONUNBUFFERED': '1'})
        commands = [
            ('fastapi', [str(ml), '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(values['ml']), '--workers', '1'], ROOT / 'ml_engine', ml_url + '/ready', {'status': 'ready'}),
            ('fastify', [node, 'src/server.js'], ROOT / 'backend', backend_url + '/ready', {'status': 'ready'}),
            ('streamlit', [str(ui), '-m', 'streamlit', 'run', 'streamlit_app.py', '--server.address', '127.0.0.1', '--server.port', str(values['streamlit']), '--server.headless', 'true', '--browser.gatherUsageStats', 'false'], ROOT, ui_url + '/_stcore/health', None),
        ]
        for name, command, cwd, url, expected in commands:
            stream = (RUNTIME / f'logs/{name}.log').open('w')
            streams.append(stream)
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=os.name != 'nt',
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
            children.append(process)
            job.assign(process)
            deadline = time.monotonic() + args.timeout
            while not ready(url, expected):
                if stopped.is_set() or process.poll() is not None or time.monotonic() >= deadline:
                    raise DemoError(f'{name} did not become ready. See .polymerge/logs/{name}.log.')
                time.sleep(0.5)
        message('PolyMerge is ready.')
        message(f'Streamlit: {ui_url}\nFastify frontend: {backend_url}\nBackend health: PASS\nML readiness: PASS\nNeo4j graph identity: PASS\nLogs: {RUNTIME / "logs"}')
        (RUNTIME / 'logs/launcher.log').write_text('PASS: model, graph identity and all services ready on loopback.\n')
        if not args.no_browser:
            webbrowser.open(ui_url)
        while not stopped.wait(0.5):
            if any(process.poll() is not None for process in children):
                raise DemoError('A managed service exited; stopping the remaining services. Inspect local logs.')
    finally:
        if job:
            stop_children(children, job)
        if control:
            control.shutdown()
            control.server_close()
        for stream in streams:
            stream.close()
        (RUNTIME / 'state.json').unlink(missing_ok=True)
        lock.rmdir()


def setup(yes: bool) -> None:
    if sys.version_info[:2] != (3, 11):
        raise DemoError('Run setup with Python 3.11; the frozen runtime will not be upgraded.')
    if not shutil.which('node') or not shutil.which('npm'):
        raise DemoError('Install Node.js 22 LTS and npm first.')
    if not yes and input('Create isolated demo environments and install locked dependencies? [y/N] ').strip().lower() != 'y':
        raise DemoError('Setup cancelled. Nothing installed.')
    for folder, lock in [('.venv-demo-ml', 'ml_engine/requirements-dev.lock'), ('.venv-demo-ui', 'requirements-streamlit.lock')]:
        destination = ROOT / folder
        if destination.exists():
            raise DemoError(f'{folder} already exists; refusing to modify an existing environment. See setup recovery instructions.')
        subprocess.run([sys.executable, '-m', 'venv', str(destination)], check=True)
        python = destination / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        subprocess.run([str(python), '-m', 'pip', 'install', '--require-hashes', '-r', str(ROOT / lock)], cwd=ROOT, check=True)
    # npm.cmd needs CMD on Windows; a fixed command avoids interpolating paths.
    npm_command = ['cmd.exe', '/d', '/c', 'npm ci --ignore-scripts'] if os.name == 'nt' else [shutil.which('npm'), 'ci', '--ignore-scripts']
    subprocess.run(npm_command, cwd=ROOT / 'backend', check=True)
    message('Locked dependencies installed. Supply .env, the trusted model and existing graph before Start.')
    ml, _, _ = runtimes()
    probe(ml)
    message('PASS: first-time preflight.')


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('action', choices=['start', 'stop', 'setup', 'check'])
    result.add_argument('--ml-port', type=int, default=8000)
    result.add_argument('--backend-port', type=int, default=3000)
    result.add_argument('--streamlit-port', type=int, default=8501)
    result.add_argument('--neo4j-container', default=os.getenv('POLYMERGE_NEO4J_CONTAINER'))
    result.add_argument('--timeout', type=int, default=120)
    result.add_argument('--no-browser', action='store_true')
    result.add_argument('--yes', action='store_true')
    result.add_argument('--preflight', action='store_true')
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.action == 'stop':
            stop()
        elif args.action == 'setup':
            setup(args.yes)
        elif args.action == 'check':
            ml, _, _ = runtimes()
            probe(ml)
            for asset in ('favicon.svg', 'favicon.ico', 'apple-touch-icon.png'):
                if not (ROOT / 'frontend' / asset).is_file():
                    raise DemoError(f'Required asset missing: {asset}')
            if not args.preflight:
                state = json.loads((RUNTIME / 'state.json').read_text())
                values = state['ports']
                for name in ('ml', 'backend'):
                    if not ready(f'http://127.0.0.1:{values[name]}/ready', {'status': 'ready'}):
                        raise DemoError(f'{name} readiness failed.')
                if not ready(f'http://127.0.0.1:{values["streamlit"]}/_stcore/health'):
                    raise DemoError('Streamlit health failed.')
                html = http_get(f'http://127.0.0.1:{values["backend"]}/').decode()
                if 'PolyMerge' not in html:
                    raise DemoError('Frontend identity mismatch.')
                for asset in ('favicon.svg', 'favicon.ico', 'apple-touch-icon.png'):
                    served = http_get(f'http://127.0.0.1:{values["backend"]}/frontend/{asset}')
                    if served != (ROOT / 'frontend' / asset).read_bytes():
                        raise DemoError(f'Served asset mismatch: {asset}')
            message('PASS: local demo preflight' if args.preflight else 'PASS: local demo service readiness')
            message('WARN: browser/iframe and native platform acceptance require manual verification.')
        else:
            if not 1 <= args.timeout <= 600:
                raise DemoError('Readiness timeout must be between 1 and 600 seconds.')
            launch(args)
        return 0
    except (DemoError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        message('FAIL: ' + (str(error) if isinstance(error, DemoError) else 'Local demo operation failed; consult docs/LOCAL_SETUP.md.'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
