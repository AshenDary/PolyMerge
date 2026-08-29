import path from 'node:path';
import { fileURLToPath } from 'node:url';

import Fastify from 'fastify';
import cors from '@fastify/cors';
import dotenv from 'dotenv';

import { checkHardContraindications } from './rules/contraindications.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Single shared .env lives at the repo root, not inside backend/.
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || '0.0.0.0';
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';

const app = Fastify({ logger: true });

await app.register(cors, {
  origin: process.env.CORS_ORIGIN || true,
});

// Liveness check consumed by docker-compose / uptime monitors.
app.get('/health', async () => ({ status: 'ok', service: 'polymerge-backend' }));

// Proxies a drug-set request to the ML engine, then applies hard-coded
// safety fallbacks BEFORE returning anything to the client. Per project
// rules, severe contraindications (e.g. MAOI + SSRI) must be blocked here
// independent of what the neural net scored.
app.post('/api/combinations/search', async (request, reply) => {
  const { diseases } = request.body ?? {};

  if (!Array.isArray(diseases) || diseases.length === 0) {
    return reply.code(400).send({ error: 'diseases[] is required' });
  }

  let mlResult;
  try {
    const res = await fetch(`${ML_SERVICE_URL}/predict/combination`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases }),
    });
    if (!res.ok) throw new Error(`ML engine responded ${res.status}`);
    mlResult = await res.json();
  } catch (err) {
    request.log.error(err, 'ML engine call failed');
    return reply.code(502).send({ error: 'ML engine unavailable' });
  }

  const violation = checkHardContraindications(mlResult.drugSet ?? []);
  if (violation) {
    return reply.code(422).send({ error: 'Blocked by hard safety rule', reason: violation });
  }

  return mlResult;
});

app.listen({ port: PORT, host: HOST }).catch((err) => {
  app.log.error(err);
  process.exit(1);
});
