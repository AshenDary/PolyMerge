import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';
import { installSecurity } from '../src/security.js';

async function fixture(t, env = {}, handler = async () => ({ ok: true })) {
  const app = Fastify({ bodyLimit: 32768 });
  await installSecurity(app, { NODE_ENV: 'production', CORS_ORIGIN: 'https://app.example.org', STREAMLIT_ORIGIN: 'https://demo.streamlit.app', ...env });
  for (const url of ['/api/history', '/api/candidate-sets/:id/explain', '/api/combinations/:id', '/api/drugs/:id', '/api/drugs/:id/interactions']) app.get(url, async () => ({ private: true }));
  app.post('/api/combinations/search', async () => ({ demo: true }));
  app.post('/api/ddi-severity/predict', async () => ({ private: true }));
  app.post('/api/candidate-sets/search', handler);
  app.get('/', async () => ({ ok: true }));
  t.after(() => app.close());
  return app;
}

test('history and unauthorized explanations never exist across visitors, identifiers, or time', async (t) => {
  const app = await fixture(t);
  for (const address of ['192.0.2.1', '192.0.2.2']) {
    for (const url of ['/api/history', '/api/candidate-sets/known/explain', '/api/candidate-sets/expired/explain', '/api/combinations/known']) {
      const response = await app.inject({ url, remoteAddress: address });
      assert.equal(response.statusCode, 404);
      assert.doesNotMatch(response.body, /private/);
    }
  }
});

test('production cannot enable legacy or raw ML proxy routes', async (t) => {
  const app = await fixture(t, { POLYMERGE_ENABLE_LEGACY: 'true' });
  for (const url of ['/api/drugs/test', '/api/drugs/test/interactions', '/api/combinations/search', '/api/ddi-severity/predict']) {
    assert.equal((await app.inject({ url, method: url.includes('drugs') ? 'GET' : 'POST', payload: undefined })).statusCode, 404);
  }
});

test('exact origins and Streamlit frame ancestors are enforced without cookies', async (t) => {
  const app = await fixture(t);
  assert.equal((await app.inject({ url: '/', headers: { origin: 'https://evil.example' } })).statusCode, 403);
  const response = await app.inject({ url: '/', headers: { origin: 'https://app.example.org' } });
  assert.equal(response.statusCode, 200);
  assert.equal(response.headers['access-control-allow-origin'], 'https://app.example.org');
  assert.equal(response.headers['access-control-allow-credentials'], undefined);
  assert.equal(response.headers['set-cookie'], undefined);
  assert.match(response.headers['content-security-policy'], /frame-ancestors https:\/\/demo.streamlit.app$/);
});

test('large bodies, analysis quotas, and global quotas are enforced', async (t) => {
  const app = await fixture(t, { ANALYSIS_RATE_LIMIT_MAX: '1', RATE_LIMIT_MAX: '5' });
  const request = { method: 'POST', url: '/api/candidate-sets/search', payload: {} };
  assert.equal((await app.inject({ ...request, payload: { data: 'a'.repeat(40000) } })).statusCode, 413);
  assert.equal((await app.inject(request)).statusCode, 200);
  assert.equal((await app.inject(request)).statusCode, 429);
  for (let i = 0; i < 5; i += 1) await app.inject('/');
  assert.equal((await app.inject('/')).statusCode, 429);
});

test('public analysis settings cannot expand the reviewed demo workload', async (t) => {
  const app = await fixture(t);
  for (const candidateSetConfig of [{ maxDrugCount: 10 }, { maxCandidateSets: 500 }]) {
    const response = await app.inject({ method: 'POST', url: '/api/candidate-sets/search', payload: { diseaseIds: ['d1'], candidateSetConfig } });
    assert.equal(response.statusCode, 422);
  }
});

test('spoofed forwarding headers cannot reset anonymous analysis quotas', async (t) => {
  const app = await fixture(t, { ANALYSIS_RATE_LIMIT_MAX: '1' });
  const request = { method: 'POST', url: '/api/candidate-sets/search', payload: {}, remoteAddress: '192.0.2.1' };
  assert.equal((await app.inject({ ...request, headers: { 'x-forwarded-for': '198.51.100.1' } })).statusCode, 200);
  assert.equal((await app.inject({ ...request, headers: { 'x-forwarded-for': '198.51.100.2' } })).statusCode, 429);
  assert.equal((await app.inject({ ...request, remoteAddress: '192.0.2.2' })).statusCode, 200);
});

test('restart does not restore history or reopen legacy routes', async (t) => {
  for (let restart = 0; restart < 2; restart += 1) {
    const app = await fixture(t);
    assert.equal((await app.inject({ method: 'POST', url: '/api/candidate-sets/search', payload: {} })).statusCode, 200);
    assert.equal((await app.inject('/api/history')).statusCode, 404);
    assert.equal((await app.inject('/api/drugs/test')).statusCode, 404);
    await app.close();
  }
});

test('concurrent analysis is bounded and failures never expose upstream secrets', async (t) => {
  let finish;
  let entered;
  const started = new Promise(resolve => { entered = resolve; });
  const app = await fixture(t, {}, async () => {
    entered();
    await new Promise(resolve => { finish = resolve; });
    throw new Error('neo4j://admin:secret@private-host/model.joblib');
  });
  const request = { method: 'POST', url: '/api/candidate-sets/search', payload: {} };
  const first = app.inject(request);
  await started;
  assert.equal((await app.inject(request)).statusCode, 503);
  finish();
  const response = await first;
  assert.equal(response.statusCode, 503);
  assert.doesNotMatch(response.body, /secret|private-host|joblib|neo4j/);
  assert.ok(response.json().requestId);
});
