# Explainability Integration

This module transforms returned candidates into separate graph-evidence,
configured-rule and supervised drug-pair prediction channels. It must never
combine them into a clinical safety score.

The current local demo renders candidate explanations from the existing search
response. History-backed `/api/candidate-sets/:queryId/explain` is a legacy route
and is disabled by the supervisor's production configuration. Do not use it as
a local-demo prerequisite.

The frontend's candidate-specific Research Takeaway is deterministic text built
from the selected response in `frontend/app.js`. It summarizes findings and
research gaps without calling another model or rerunning analysis.

Run `npm test` from `backend/` for API, presentation, frontend state and
takeaway tests. Missing inference is an explicit availability state, not a
fabricated severity. Single-drug results are not applicable.

See [backend guide](../../README.md), [API](../../../docs/api.md),
[historical integration specification](../../../docs/sprint5-explainability-integration.md)
and [current architecture](../../../docs/ARCHITECTURE.md).
