# Scripts

`local_demo.py` is the standard-library cross-platform supervisor.
`check_demo_readiness.py` exposes read-only preflight/running-stack checks.
`demo_preflight.py` executes in the isolated ML environment and validates the
trusted model and complete source graph identity. See [Local Setup](../docs/LOCAL_SETUP.md).

From the repository root after Setup, run:

```bash
.venv-demo-ml/bin/python -m pytest -q scripts/tests
.venv-demo-ml/bin/python scripts/validate_sprint4_contract.py
.venv-demo-ml/bin/python scripts/check_release_metadata.py
```

Windows uses `.venv-demo-ml\Scripts\python.exe` for these commands. Contract
validation needs packages in the locked ML environment; system `python3.11`
alone is not sufficient. The supervisor itself uses `python3.11` on macOS or
`py -3.11` on Windows and selects the isolated environment for preflight.

Use `verify_frozen_runtime.py` with `--output <path>`,
`--baseline <owner-baseline.json>` and, when available,
`--fixtures <preserved-fixture-directory>`. It compares model predictions and
probabilities, and optionally preserved scenario pairs, without training or
reading held-out evaluation rows. Run it with the locked ML interpreter. It is
not a replacement for the held-out evaluation.
Loader/migration/training/data-preparation scripts are not launcher steps and can
mutate data. Do not run them against the demo database without explicit review.
