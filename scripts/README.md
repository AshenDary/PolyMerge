# Scripts

`local_demo.py` is the standard-library cross-platform supervisor.
`check_demo_readiness.py` exposes read-only preflight/running-stack checks.
`demo_preflight.py` executes in the isolated ML environment and validates the
trusted model and complete source graph identity. See [Local Setup](../docs/LOCAL_SETUP.md).

From root run `python3.11 -m unittest discover -s scripts/tests -v`,
`python3.11 scripts/validate_sprint4_contract.py` and
`python3.11 scripts/check_release_metadata.py`.
Research/data scripts have different dependencies; use the locked ML environment.
Use `py -3.11` on Windows.

`verify_frozen_runtime.py` compares existing model outputs against owner-supplied
preserved fixtures. It is not a replacement for the held-out evaluation.
Loader/migration/training/data-preparation scripts are not launcher steps and can
mutate data. Do not run them against the demo database without explicit review.
