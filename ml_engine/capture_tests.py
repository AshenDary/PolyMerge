"""Run the Sprint 6 tests inline (no subprocess) and write results to a file."""
import sys
import os
import io

# Add ml_engine root to path
ml_engine_root = os.path.dirname(os.path.abspath(__file__))
if ml_engine_root not in sys.path:
    sys.path.insert(0, ml_engine_root)

out_file = os.path.join(os.path.expanduser("~"), "Desktop", "pm_test_results.txt")

# Capture stdout/stderr
old_stdout = sys.stdout
old_stderr = sys.stderr
buf = io.StringIO()
sys.stdout = buf
sys.stderr = buf

try:
    import pytest
    exit_code = pytest.main([
        os.path.join(ml_engine_root, "tests", "test_sprint6_frontend.py"),
        "--tb=short",
        "-v",
        "--no-header",
        "--override-ini=addopts=",
        f"--rootdir={ml_engine_root}",
    ])
finally:
    sys.stdout = old_stdout
    sys.stderr = old_stderr

output = buf.getvalue()
with open(out_file, "w", encoding="utf-8") as f:
    f.write(output)

print(f"Exit code: {exit_code}")
print(f"Written {len(output)} chars to {out_file}")
print("--- FIRST 2000 chars ---")
print(output[:2000])
