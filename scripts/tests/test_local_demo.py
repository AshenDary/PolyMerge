"""Supervisor unit checks do not require the private model or a database."""
import argparse
import importlib.util
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('local_demo', Path(__file__).parents[1] / 'local_demo.py')
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class LocalDemoTests(unittest.TestCase):
    def test_duplicate_ports_rejected(self) -> None:
        with self.assertRaises(demo.DemoError):
            demo.ports(argparse.Namespace(ml_port=8000, backend_port=8000, streamlit_port=8501))

    def test_privileged_ports_rejected(self) -> None:
        with self.assertRaises(demo.DemoError):
            demo.ports(argparse.Namespace(ml_port=80, backend_port=3000, streamlit_port=8501))

    def test_occupied_port_is_not_killed(self) -> None:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with self.assertRaises(demo.DemoError):
                demo.require_free({'ml': listener.getsockname()[1]})
            self.assertGreater(listener.fileno(), 0)

    def test_failed_command_does_not_disclose_output(self) -> None:
        with self.assertRaises(demo.DemoError) as result:
            demo.checked([sys.executable, '-c', 'import sys; sys.stderr.write("secret-password"); sys.exit(1)'])
        self.assertNotIn('secret-password', str(result.exception))

    def test_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix='PolyMerge path with spaces ') as folder:
            path = Path(folder) / 'hello script.py'
            path.write_text('print("PASS")')
            self.assertEqual(demo.checked([sys.executable, str(path)]), 'PASS')

    def test_explicit_interpreter_does_not_resolve_venv_symlinks(self) -> None:
        selected = str(demo.ROOT / '.venv-demo-ml' / 'bin' / 'python')
        with patch.dict(demo.os.environ, {'POLYMERGE_ML_PYTHON': selected}):
            self.assertEqual(demo.interpreter('unused', 'POLYMERGE_ML_PYTHON'), Path(selected))

    def test_stop_missing_state_never_signals_pid(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(demo, 'RUNTIME', Path(folder)):
            with patch.object(demo.os, 'kill') as kill:
                with self.assertRaises(demo.DemoError):
                    demo.stop()
                kill.assert_not_called()

    def test_missing_model_reports_sanitized_failure(self) -> None:
        with patch.object(demo.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '{"error":"Frozen model artifact missing"}', 'private detail')):
            with self.assertRaisesRegex(demo.DemoError, 'Frozen model artifact missing'):
                demo.probe(Path(sys.executable))

    def test_owned_child_shutdown(self) -> None:
        job = demo.WindowsJob()
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                                 start_new_session=demo.os.name != 'nt',
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if demo.os.name == 'nt' else 0)
        job.assign(child)
        demo.stop_children([child], job)
        self.assertIsNotNone(child.poll())

    @unittest.skipIf(sys.platform == 'win32', 'POSIX process groups only')
    def test_shutdown_contains_descendant_after_parent_exits(self) -> None:
        descendant = 'import os,time; print(os.getpid(), flush=True); time.sleep(60)'
        parent = subprocess.Popen([sys.executable, '-c',
                                   f'import subprocess,sys; subprocess.Popen([sys.executable, "-c", {descendant!r}])'],
                                  start_new_session=True, stdout=subprocess.PIPE, text=True)
        group = parent.pid
        try:
            descendant_pid = int(parent.stdout.readline().strip())
            parent.wait(timeout=5)
            demo.stop_children([parent], demo.WindowsJob())
            for _ in range(50):
                try:
                    demo.os.kill(descendant_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                self.fail('Managed descendant process group survived shutdown')
        finally:
            try:
                demo.os.killpg(group, demo.signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            parent.wait()
            parent.stdout.close()

    def test_preflight_failure_cleans_lock_without_starting_children(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(demo, 'RUNTIME', Path(folder)):
            with patch.object(demo, 'runtimes', side_effect=demo.DemoError('missing environment')):
                with patch.object(demo.subprocess, 'Popen') as spawn:
                    with self.assertRaisesRegex(demo.DemoError, 'missing environment'):
                        demo.launch(argparse.Namespace())
                    spawn.assert_not_called()
            self.assertFalse((Path(folder) / 'launcher.lock').exists())
            self.assertFalse((Path(folder) / 'state.json').exists())

    def test_duplicate_launcher_preserves_existing_lock_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(demo, 'RUNTIME', Path(folder)):
            (Path(folder) / 'launcher.lock').mkdir()
            state = Path(folder) / 'state.json'
            state.write_text('existing state')
            with self.assertRaisesRegex(demo.DemoError, 'lock already exists'):
                demo.launch(argparse.Namespace())
            self.assertEqual(state.read_text(), 'existing state')

    def test_ready_rejects_liveness_and_invalid_json(self) -> None:
        for payload in (b'{"status":"ok"}', b'not json'):
            with patch.object(demo, 'http_get', return_value=payload):
                self.assertFalse(demo.ready('http://127.0.0.1/ready', {'status': 'ready'}))

    def test_platform_wrappers_quote_repository_path(self) -> None:
        for action in ('Start', 'Stop', 'Setup'):
            self.assertIn('cd /d "%~dp0"', (demo.ROOT / (action + '-PolyMerge.bat')).read_text())
            self.assertIn('cd "$(dirname "$0")"', (demo.ROOT / (action + '-PolyMerge.command')).read_text())

    @unittest.skipUnless(sys.platform == 'win32', 'Native CMD execution requires Windows')
    def test_windows_batch_entrypoints_from_path_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix='PolyMerge checkout with spaces ') as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            shutil.copyfile(demo.ROOT / 'scripts/local_demo.py', root / 'scripts/local_demo.py')
            for action in ('Start', 'Stop', 'Setup'):
                wrapper = root / (action + '-PolyMerge.bat')
                shutil.copyfile(demo.ROOT / wrapper.name, wrapper)
                result = subprocess.run(['cmd.exe', '/d', '/c', str(wrapper), '--help'],
                                        input='', capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('--ml-port', result.stdout)


if __name__ == '__main__':
    unittest.main()
