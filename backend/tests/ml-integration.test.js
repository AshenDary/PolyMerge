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

const graphDiseases = [
  {
    id: 'Disease::DOID:10763',
    name: 'hypertension',
    kind: 'Disease',
    source: 'Hetionet',
    graphVersion: 'Hetionet v1.0 filtered PolyMerge fragment',
  },
  {
    id: 'Disease::DOID:9352',
    name: 'type 2 diabetes mellitus',
    kind: 'Disease',
    source: 'Hetionet',
    graphVersion: 'Hetionet v1.0 filtered PolyMerge fragment',
  },
];

function mockGraphCatalogAndPrediction(predictionPayload) {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (String(url).endsWith('/api/diseases')) {
      return jsonResponse({ diseases: graphDiseases });
    }
    if (String(url).endsWith('/predict/combination')) {
      return jsonResponse(predictionPayload);
    }
    return jsonResponse({ error: 'unexpected url' }, 404);
  };
  return calls;
}

test('loads the disease catalog from the ML graph service', async () => {
  globalThis.fetch = async (url) => {
    assert.match(String(url), /\/api\/diseases$/);
    return jsonResponse({ diseases: graphDiseases });
  };

  const response = await app.inject({ method: 'GET', url: '/api/diseases' });

  assert.equal(response.statusCode, 200);
  const payload = response.json();
  assert.equal(payload.diseases[0].id, 'Disease::DOID:10763');
  assert.equal(payload.diseases[0].name, 'hypertension');
  assert.equal(payload.diseases[0].source, 'Hetionet');
});

test('reports graph disease catalog failures', async () => {
  globalThis.fetch = async () => jsonResponse({ error: 'unavailable' }, 503);

  const response = await app.inject({ method: 'GET', url: '/api/diseases' });

  assert.equal(response.statusCode, 503);
  assert.equal(response.json().error, 'Disease catalog unavailable');
});

test('forwards the candidate request and preserves graph and ML provenance', async () => {
  const calls = mockGraphCatalogAndPrediction({
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

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: {
      diseases: ['Disease::DOID:10763'],
      optimizationConfig: { maxDrugCount: 2, minimumCoverage: 1 },
    },
  });

  assert.equal(response.statusCode, 200);
  assert.match(calls[1].url, /\/predict\/combination$/);
  assert.deepEqual(calls[1].body, {
    diseases: ['Disease::DOID:10763'],
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

test('accepts multiple valid graph disease IDs', async () => {
  const calls = mockGraphCatalogAndPrediction({
    queryId: 'graph-multiple-test',
    diseases: ['hypertension', 'type 2 diabetes mellitus'],
    candidates: [],
    metadata: {
      dataStatus: 'real_graph',
      mlStatus: 'not_applied',
      model: 'No predictive ML model applied',
      modelVersion: null,
    },
  });

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['Disease::DOID:10763', 'Disease::DOID:9352'] },
  });

  assert.equal(response.statusCode, 200);
  assert.deepEqual(calls[1].body.diseases, ['Disease::DOID:10763', 'Disease::DOID:9352']);
});

test('rejects mixed valid and invalid disease IDs before candidate prediction', async () => {
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    return jsonResponse({ diseases: graphDiseases });
  };

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['Disease::DOID:10763', 'Disease::DOID:DOES-NOT-EXIST'] },
  });

  assert.equal(response.statusCode, 400);
  assert.deepEqual(response.json().unknownDiseases, ['Disease::DOID:DOES-NOT-EXIST']);
  assert.equal(calls.length, 1);
  assert.match(calls[0], /\/api\/diseases$/);
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
  globalThis.fetch = async (url) => {
    if (String(url).endsWith('/api/diseases')) {
      return jsonResponse({ diseases: graphDiseases });
    }
    return jsonResponse({ error: 'unavailable' }, 503);
  };

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['Disease::DOID:10763'] },
  });

  assert.equal(response.statusCode, 200);
  const payload = response.json();
  assert.equal(payload.metadata.dataStatus, 'demo');
  assert.equal(payload.metadata.mlStatus, 'demo');
  assert.equal(payload.metadata.upstreamStatus, 'fallback');
  assert.match(payload.metadata.warning, /responded 503/);
  assert.deepEqual(payload.candidates, []);
});

test('rejects malformed upstream provenance and uses the labeled fallback', async () => {
  globalThis.fetch = async (url) => {
    if (String(url).endsWith('/api/diseases')) {
      return jsonResponse({ diseases: graphDiseases });
    }
    return jsonResponse({
      queryId: 'bad-contract',
      diseases: ['hypertension'],
      candidates: [],
      metadata: { dataStatus: 'real_graph' },
    });
  };

  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['Disease::DOID:10763'] },
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
