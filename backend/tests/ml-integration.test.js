import { after, afterEach, test } from 'node:test';
import assert from 'node:assert/strict';

import { app } from '../src/server.js';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

after(async () => {
  await app.close();
});

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

test('forwards the candidate request and preserves graph and ML provenance', async () => {
  let forwardedRequest;
  globalThis.fetch = async (url, options) => {
    forwardedRequest = { url, body: JSON.parse(options.body) };
    return jsonResponse({
      queryId: 'graph-integration-test',
      diseases: ['hypertension'],
      candidates: [{
        rank: 1,
        drugId: 'Compound::DB00177',
        drugs: ['Compound::DB00177'],
        interactionRisk: null,
        synergyScore: null,
        dataStatus: 'real_graph',
        status: 'accepted',
      }],
      metadata: {
        dataStatus: 'real_graph',
        mlStatus: 'not_applied',
        model: 'No predictive ML model applied',
        modelVersion: null,
      },
    });
  };

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: {
      diseases: ['Hypertension'],
      optimizationConfig: { maxDrugCount: 2, minimumCoverage: 1 },
    },
  });

  assert.equal(response.statusCode, 200);
  assert.match(forwardedRequest.url, /\/predict\/combination$/);
  assert.deepEqual(forwardedRequest.body, {
    diseases: ['hypertension'],
    optimizationConfig: { maxDrugCount: 2, minimumCoverage: 1 },
  });

  const payload = response.json();
  assert.equal(payload.metadata.dataStatus, 'real_graph');
  assert.equal(payload.metadata.mlStatus, 'not_applied');
  assert.equal(payload.metadata.modelVersion, null);
  assert.equal(payload.candidates[0].dataStatus, 'real_graph');
  assert.equal(payload.candidates[0].mlStatus, 'not_applied');
  assert.equal(payload.candidates[0].interactionRisk, null);
  assert.equal(payload.candidates[0].synergyScore, null);
});

test('rejects invalid client input before calling the ML engine', async () => {
  let fetchCalled = false;
  globalThis.fetch = async () => {
    fetchCalled = true;
    throw new Error('must not be called');
  };

  const nonStringDisease = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: [42] },
  });
  assert.equal(nonStringDisease.statusCode, 400);

  const invalidConfig = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['hypertension'], optimizationConfig: { minimumCoverage: 2 } },
  });
  assert.equal(invalidConfig.statusCode, 400);
  assert.equal(fetchCalled, false);
});

test('labels the fallback when the ML engine returns an error', async () => {
  globalThis.fetch = async () => jsonResponse({ error: 'unavailable' }, 503);

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['hypertension'] },
  });

  assert.equal(response.statusCode, 200);
  const payload = response.json();
  assert.equal(payload.metadata.dataStatus, 'demo');
  assert.equal(payload.metadata.mlStatus, 'demo');
  assert.equal(payload.metadata.upstreamStatus, 'fallback');
  assert.match(payload.metadata.warning, /responded 503/);
  assert.ok(payload.candidates.every((candidate) => (
    candidate.dataStatus === 'demo' && candidate.mlStatus === 'demo'
  )));
});

test('rejects malformed upstream provenance and uses the labeled fallback', async () => {
  globalThis.fetch = async () => jsonResponse({
    queryId: 'bad-contract',
    diseases: ['hypertension'],
    candidates: [],
    metadata: { dataStatus: 'real_graph' },
  });

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['hypertension'] },
  });

  assert.equal(response.statusCode, 200);
  const payload = response.json();
  assert.equal(payload.metadata.dataStatus, 'demo');
  assert.equal(payload.metadata.mlStatus, 'demo');
  assert.match(payload.metadata.warning, /missing dataStatus or mlStatus provenance/);
});

test('reports ML dependency health without changing backend liveness', async () => {
  globalThis.fetch = async () => jsonResponse({
    status: 'ok',
    service: 'polymerge-ml-engine',
  });

  const healthy = await app.inject({ method: 'GET', url: '/health/dependencies' });
  assert.equal(healthy.statusCode, 200);
  assert.equal(healthy.json().dependencies.mlEngine, 'ok');

  globalThis.fetch = async () => {
    throw new Error('connection refused');
  };
  const degraded = await app.inject({ method: 'GET', url: '/health/dependencies' });
  assert.equal(degraded.statusCode, 503);
  assert.equal(degraded.json().dependencies.mlEngine, 'unavailable');

  const liveness = await app.inject({ method: 'GET', url: '/health' });
  assert.equal(liveness.statusCode, 200);
});
