# Fastify Backend

Hosts the static frontend and validates/orchestrates requests to FastAPI.
Production local-demo mode preserves request limits, narrow origins and disabled
legacy routes while allowing HTTP only on 127.0.0.1.

Use [root setup](../docs/LOCAL_SETUP.md); Node >=20, baseline 22. Setup runs
`npm ci --ignore-scripts`. The supervisor runs `node src/server.js` with
`ML_SERVICE_URL`, matching ports/origins and production restrictions.
MySQL/Prisma are legacy foundations, not local-demo prerequisites.

Run `npm test` here. `/health` is liveness; `/ready` verifies dependencies.
Frontend and favicon assets are served from `../frontend/`.
See [API scope](../docs/api.md) and [explainability](src/explainability/README.md).
