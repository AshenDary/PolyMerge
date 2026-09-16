import assert from 'node:assert/strict';
import http from 'node:http';
import { after, before, test } from 'node:test';

let app;
let mockMlServer;
let mockMode = 'success';
let mockRequestCount = 0;
let originalMlServiceUrl;
let originalMlServiceTimeoutMs;

const graphPayload = {
  queryId: 'graph-integration-test',
  diseases: ['hypertension'],
  candidates: [
    {
      rank: 1,
      drugId: 'Compound::DB00177',
      drugs: ['Compound::DB00177'],
      coverage: 1,
      interactionRisk: null,
      synergyScore: null,
      dataStatus: 'real_graph',
      evidence: [
        {
          source: 'Hetionet',
          relationship: 'CtD',
          evidenceType: 'known',
        },
      ],
    },
  ],
  metadata: {
    dataStatus: 'real_graph',
    mlStatus: 'not_applied',
    model: 'No predictive ML model applied',
    modelVersion: null,
  },
};

function listen(server, port = 0) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server.address().port));
  });
}

function close(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify(payload));
}

before(async () => {
  mockMlServer = http.createServer((request, response) => {
    if (request.method !== 'POST' || request.url !== '/predict/combination') {
      return sendJson(response, 404, { error: 'not found' });
    }

    mockRequestCount += 1;
    let requestBody = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => {
      requestBody += chunk;
    });
    request.on('end', () => {
      const parsedBody = JSON.parse(requestBody);
      assert.deepEqual(parsedBody, { diseases: ['hypertension'] });

      if (mockMode === 'http-error') {
        return sendJson(response, 503, { error: 'temporarily unavailable' });
      }

      if (mockMode === 'malformed') {
        return sendJson(response, 200, {
          ...graphPayload,
          metadata: { dataStatus: 'real_graph' },
        });
      }

      if (mockMode === 'inconsistent-prediction') {
        return sendJson(response, 200, {
          ...graphPayload,
          candidates: [
            {
              ...graphPayload.candidates[0],
              interactionRisk: 0.12,
            },
          ],
        });
      }

      if (mockMode === 'timeout') {
        return setTimeout(() => sendJson(response, 200, graphPayload), 250);
      }

      return sendJson(response, 200, graphPayload);
    });
  });

  const mlPort = await listen(mockMlServer);
  originalMlServiceUrl = process.env.ML_SERVICE_URL;
  originalMlServiceTimeoutMs = process.env.ML_SERVICE_TIMEOUT_MS;
  process.env.ML_SERVICE_URL = `http://127.0.0.1:${mlPort}`;
  process.env.ML_SERVICE_TIMEOUT_MS = '75';

  ({ app } = await import(`../src/server.js?integration-test=${Date.now()}`));
  await app.ready();
});

after(async () => {
  if (app) {
    await app.close();
  }
  if (mockMlServer?.listening) {
    await close(mockMlServer);
  }
  if (originalMlServiceUrl === undefined) {
    delete process.env.ML_SERVICE_URL;
  } else {
    process.env.ML_SERVICE_URL = originalMlServiceUrl;
  }
  if (originalMlServiceTimeoutMs === undefined) {
    delete process.env.ML_SERVICE_TIMEOUT_MS;
  } else {
    process.env.ML_SERVICE_TIMEOUT_MS = originalMlServiceTimeoutMs;
  }
});

test('backend and ML health boundary remains available', async () => {
  const response = await app.inject({ method: 'GET', url: '/health' });
  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.json(), {
    status: 'ok',
    service: 'polymerge-backend',
  });
});

test('candidate search preserves graph provenance and explicit ML status', async () => {
  mockMode = 'success';
  const response = await app.inject({
    method: 'POST',
    url: '/api/combinations/search',
    payload: { diseases: ['hypertension'] },
  });
  const payload = response.json();

  assert.equal(response.statusCode, 200);
  assert.equal(payload.metadata.dataStatus, 'real_graph');
  assert.equal(payload.metadata.mlStatus, 'not_applied');
  assert.equal(payload.candidates[0].dataStatus, 'real_graph');
  assert.equal(payload.candidates[0].mlStatus, 'not_applied');
  assert.equal(payload.candidates[0].interactionRisk, null);
  assert.equal(payload.candidates[0].synergyScore, null);
  assert.equal(payload.candidates[0].evidence[0].source, 'Hetionet');
});

test('invalid requests are rejected before calling the ML service', async () => {
  const requestsBefore = mockRequestCount;
  const responses = await Promise.all([
    app.inject({
      method: 'POST',
      url: '/api/combinations/search',
      payload: { diseases: [] },
    }),
    app.inject({
      method: 'POST',
      url: '/api/combinations/search',
      payload: { diseases: [42] },
    }),
    app.inject({
      method: 'POST',
      url: '/api/combinations/search',
      payload: { diseases: ['hypertension'], optimizationConfig: [] },
    }),
  ]);

  for (const response of responses) {
    assert.equal(response.statusCode, 400);
    assert.equal(response.json().code, 'INVALID_REQUEST');
  }
  assert.equal(mockRequestCount, requestsBefore);
});

for (const mode of ['http-error', 'malformed', 'inconsistent-prediction', 'timeout']) {
  test(`candidate search returns explicitly labeled demo fallback for ${mode}`, async () => {
    mockMode = mode;
    const response = await app.inject({
      method: 'POST',
      url: '/api/combinations/search',
      payload: { diseases: ['hypertension'] },
    });
    const payload = response.json();

    assert.equal(response.statusCode, 200);
    assert.equal(payload.metadata.dataStatus, 'demo');
    assert.equal(payload.metadata.mlStatus, 'demo_placeholder');
    assert.equal(payload.metadata.fallback, true);
    assert.equal(payload.candidates[0].dataStatus, 'demo');
    assert.equal(payload.candidates[0].mlStatus, 'demo_placeholder');
  });
}
