import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';
import { installSecurity } from '../src/security.js';

test('local demo requires loopback binding and rejects remote HTTP origins', async () => {
  for (const env of [
    { HOST: '0.0.0.0', CORS_ORIGIN: 'http://127.0.0.1:3000' },
    { HOST: '127.0.0.1', CORS_ORIGIN: 'http://example.com' },
  ]) {
    const app = Fastify();
    await assert.rejects(installSecurity(app, { NODE_ENV: 'production', POLYMERGE_LOCAL_DEMO: 'true', ...env }));
    await app.close();
  }
});

test('loopback demo retains production framing, body limits and legacy exclusion', async () => {
  const app = Fastify({ bodyLimit: 32768 });
  await installSecurity(app, { NODE_ENV: 'production', POLYMERGE_LOCAL_DEMO: 'true', HOST: '127.0.0.1',
    CORS_ORIGIN: 'http://127.0.0.1:3000', STREAMLIT_ORIGIN: 'http://127.0.0.1:8501', POLYMERGE_ENABLE_LEGACY: 'true' });
  app.get('/', async () => ({ status: 'ok' }));
  const response = await app.inject('/');
  assert.match(response.headers['content-security-policy'], /frame-ancestors http:\/\/127.0.0.1:8501/);
  assert.equal((await app.inject('/api/history')).statusCode, 404);
  assert.equal((await app.inject({ url: '/', headers: { origin: 'http://evil.example' } })).statusCode, 403);
  await app.close();
});
