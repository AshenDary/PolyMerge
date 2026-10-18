"""The shared entry point delegates without starting services during tests."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import local_demo


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('unified_launcher', ROOT / 'Run-PolyMerge.py')
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class UnifiedLauncherTests(unittest.TestCase):
    def test_repeat_start_reports_only_verified_running_urls(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / '.polymerge' / 'state.json'
            state.parent.mkdir()
            state.write_text(json.dumps({'token': 'private-control-token', 'ports': {'streamlit': 8516, 'backend': 3016}}))
            with patch.object(launcher, 'ROOT', Path(folder)):
                with patch.object(launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'PASS', '')):
                    with patch.object(launcher.os, 'execv') as execv, io.StringIO() as output, redirect_stdout(output):
                        self.assertEqual(launcher.main([]), 0)
                        self.assertIn('http://127.0.0.1:8516', output.getvalue())
                        self.assertNotIn('private-control-token', output.getvalue())
                        execv.assert_not_called()

    def test_unhealthy_existing_state_does_not_bypass_lock(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / '.polymerge' / 'state.json'
            state.parent.mkdir()
            state.write_text(json.dumps({'ports': {'streamlit': 8516, 'backend': 3016}}))
            with patch.object(launcher, 'ROOT', Path(folder)):
                with patch.object(launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, 'FAIL', '')):
                    self.assertIsNone(launcher.running_demo_urls())

    def test_python311_uses_installed_interpreter_for_fresh_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(launcher, 'ROOT', Path(folder)):
            with patch.object(launcher.shutil, 'which', return_value='python-3.11'):
                with patch.object(launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '3.11\n', '')):
                    expected = ['python-3.11', '-3.11'] if launcher.os.name == 'nt' else ['python-3.11']
                    self.assertEqual(launcher.python311_runtime(), expected)

    def test_python311_prefers_existing_demo_environment(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(launcher, 'ROOT', Path(folder)):
            candidate = Path(folder) / '.venv-demo-ml' / ('Scripts/python.exe' if launcher.os.name == 'nt' else 'bin/python')
            candidate.parent.mkdir(parents=True)
            candidate.touch()
            with patch.object(launcher.shutil, 'which', return_value=None):
                with patch.object(launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '3.11\n', '')):
                    self.assertEqual(launcher.python311_runtime(), [str(candidate)])

    def test_default_start_uses_setup_once_for_fresh_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix='PolyMerge path with spaces ') as folder:
            with patch.object(launcher, 'ROOT', Path(folder)), patch.object(launcher, 'SUPERVISOR', Path(folder) / 'scripts/local_demo.py'):
                with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv') as execv:
                    self.assertEqual(launcher.main(['--no-browser', '--ml-port', '8016']), 0)
                    setup.assert_called_once_with(False)
                    execv.assert_called_once_with(sys.executable, [
                        sys.executable, str(Path(folder) / 'scripts/local_demo.py'),
                        'start', '--no-browser', '--ml-port', '8016',
                    ])

    def test_existing_environments_skip_setup(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for name in ('.venv-demo-ml', '.venv-demo-ui'):
                (Path(folder) / name).mkdir()
            with patch.object(launcher, 'ROOT', Path(folder)):
                with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv'):
                    self.assertEqual(launcher.main([]), 0)
                    setup.assert_not_called()

    def test_yes_is_forwarded_to_setup_and_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(launcher, 'ROOT', Path(folder)):
                with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv') as execv:
                    self.assertEqual(launcher.main(['--yes']), 0)
                    setup.assert_called_once_with(True)
                    self.assertEqual(execv.call_args.args[1][-2:], ['start', '--yes'])

    def test_partial_install_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / '.venv-demo-ml').mkdir()
            with patch.object(launcher, 'ROOT', Path(folder)):
                with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv') as execv:
                    self.assertEqual(launcher.main([]), 1)
                    setup.assert_not_called()
                    execv.assert_not_called()

    def test_explicit_actions_do_not_run_automatic_setup(self) -> None:
        with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv') as execv:
            self.assertEqual(launcher.main(['stop']), 0)
            self.assertEqual(launcher.main(['check', '--preflight']), 0)
            self.assertEqual(launcher.main(['setup']), 0)
            setup.assert_not_called()
            self.assertEqual(execv.call_args_list[0].args[1][-1], 'stop')
            self.assertEqual(execv.call_args_list[1].args[1][-2:], ['check', '--preflight'])
            self.assertEqual(execv.call_args_list[2].args[1][-1], 'setup')

    def test_help_does_not_install(self) -> None:
        with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv'):
            self.assertEqual(launcher.main(['--help']), 0)
            setup.assert_not_called()

    def test_invalid_start_option_does_not_install(self) -> None:
        with patch.object(local_demo, 'setup') as setup, patch.object(launcher.os, 'execv') as execv:
            with self.assertRaises(SystemExit) as failure:
                launcher.main(['--unknown-option'])
            self.assertEqual(failure.exception.code, 2)
            setup.assert_not_called()
            execv.assert_not_called()


if __name__ == '__main__':
    unittest.main()
