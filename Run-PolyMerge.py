#!/usr/bin/env python3
"""One entry point for the existing local PolyMerge setup and supervisor.

macOS: python3 Run-PolyMerge.py [start|stop|check|setup]
Windows: py -3.11 Run-PolyMerge.py [start|stop|check|setup]

On macOS, an existing .venv-demo-ml supplies Python 3.11 when the editor invokes
an older python3. A fresh checkout still needs Python 3.11 installed first.
Supply the trusted model, private Neo4j settings and an existing reviewed graph.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
SUPERVISOR = ROOT / 'scripts' / 'local_demo.py'


def python311_runtime() -> list[str] | None:
    installed = ROOT / '.venv-demo-ml' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    candidates = [[str(installed)]] if installed.is_file() else []
    system = shutil.which('py' if os.name == 'nt' else 'python3.11')
    if system:
        candidates.append([system, '-3.11'] if os.name == 'nt' else [system])
    for command in candidates:
        try:
            result = subprocess.run(
                [*command, '-c', 'import sys; print("%s.%s" % sys.version_info[:2])'],
                capture_output=True, text=True, timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip() == '3.11':
            return command
    return None


def action_and_options(argv: list[str]) -> tuple[str, list[str]]:
    if argv and argv[0] in {'start', 'stop', 'check', 'setup'}:
        return argv[0], argv[1:]
    return 'start', argv


def needs_setup() -> bool:
    from scripts import local_demo

    ml = ROOT / '.venv-demo-ml'
    ui = ROOT / '.venv-demo-ui'
    if ml.exists() != ui.exists():
        raise local_demo.DemoError(
            'Only one demo environment exists. Inspect it before using the '
            'setup recovery steps in docs/LOCAL_SETUP.md; nothing was changed.'
        )
    return not ml.exists()


def running_demo_urls() -> tuple[str, str] | None:
    state_path = ROOT / '.polymerge' / 'state.json'
    if not state_path.is_file():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(SUPERVISOR), 'check'],
            cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
        )
        if result.returncode:
            return None
        values = json.loads(state_path.read_text())['ports']
        backend = int(values['backend'])
        streamlit = int(values['streamlit'])
        if not all(1024 <= port <= 65535 for port in (backend, streamlit)):
            return None
        return (f'http://127.0.0.1:{streamlit}', f'http://127.0.0.1:{backend}')
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return None


def main(argv: list[str] | None = None) -> int:
    options_from_user = list(sys.argv[1:] if argv is None else argv)
    if sys.version_info[:2] != (3, 11):
        interpreter = python311_runtime()
        if interpreter:
            print('Using Python 3.11 for the local demo.', flush=True)
            try:
                os.execv(interpreter[0], [*interpreter, str(ROOT / 'Run-PolyMerge.py'), *options_from_user])
            except OSError:
                print('FAIL: Could not start Python 3.11. See docs/LOCAL_SETUP.md.', flush=True)
                return 1
        print('FAIL: Python 3.11 is required. Install it or run with .venv-demo-ml/bin/python. '
              'See docs/LOCAL_SETUP.md.', flush=True)
        return 1

    from scripts import local_demo

    action, options = action_and_options(options_from_user)
    try:
        help_requested = bool({'-h', '--help'} & set(options))
        if not help_requested:
            local_demo.parser().parse_args([action, *options])
        if action == 'start' and not help_requested:
            urls = running_demo_urls()
            if urls:
                local_demo.message(f'PolyMerge is already running.\nStreamlit: {urls[0]}\nFastify frontend: {urls[1]}')
                return 0
        if action == 'start' and not help_requested and needs_setup():
            local_demo.setup('--yes' in options)
        os.execv(sys.executable, [sys.executable, str(SUPERVISOR), action, *options])
    except (local_demo.DemoError, OSError, EOFError) as error:
        local_demo.message('FAIL: ' + (
            str(error) if isinstance(error, local_demo.DemoError)
            else 'Local launch failed. See docs/LOCAL_SETUP.md.'
        ))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
