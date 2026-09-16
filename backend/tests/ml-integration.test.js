import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { after, before, test } from 'node:test';

const backendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

let backendProcess;
let backendUrl;
let mockMlServer;
let mockMode = 'success';
let mockRequestCount = 0;
let backendLogs = '';

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

async function findAvailablePort() {
  const server = net.createServer();
  const port = await listen(server);
  await close(server);
  return port;
}

async function waitForBackend(url) {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${url}/health`);
      if (response.ok) return;
    } catch {
      // The child process may still be binding its port.
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(`Backend did not start. Logs:\n${backendLogs}`);
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
  const backendPort = await findAvailablePort();
  backendUrl = `http://127.0.0.1:${backendPort}`;

  backendProcess = spawn(process.execPath, ['src/server.js'], {
    cwd: backendRoot,
    env: {
      ...process.env,
      HOST: '127.0.0.1',
      PORT: String(backendPort),
      ML_SERVICE_URL: `http://127.0.0.1:${mlPort}`,
      ML_SERVICE_TIMEOUT_MS: '75',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const captureLogs = (chunk) => {
    backendLogs = `${backendLogs}${chunk}`.slice(-12000);
  };
  backendProcess.stdout.on('data', captureLogs);
  backendProcess.stderr.on('data', captureLogs);

  await waitForBackend(backendUrl);
});

after(async () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
  if (mockMlServer?.listening) {
    await close(mockMlServer);
  }
});

test('backend and ML health boundary remains available', async () => {
  const response = await fetch(`${backendUrl}/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    status: 'ok',
    service: 'polymerge-backend',
  });
});

test('candidate search preserves graph provenance and explicit ML status', async () => {
  mockMode = 'success';
  const response = await fetch(`${backendUrl}/api/combinations/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ diseases: ['hypertension'] }),
  });
  const payload = await response.json();

  assert.equal(response.status, 200);
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
    fetch(`${backendUrl}/api/combinations/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases: [] }),
    }),
    fetch(`${backendUrl}/api/combinations/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases: [42] }),
    }),
    fetch(`${backendUrl}/api/combinations/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases: ['hypertension'], optimizationConfig: [] }),
    }),
  ]);

  for (const response of responses) {
    assert.equal(response.status, 400);
    assert.equal((await response.json()).code, 'INVALID_REQUEST');
  }
  assert.equal(mockRequestCount, requestsBefore);
});

for (const mode of ['http-error', 'malformed', 'inconsistent-prediction', 'timeout']) {
  test(`candidate search returns explicitly labeled demo fallback for ${mode}`, async () => {
    mockMode = mode;
    const response = await fetch(`${backendUrl}/api/combinations/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases: ['hypertension'] }),
    });
    const payload = await response.json();

    assert.equal(response.status, 200);
    assert.equal(payload.metadata.dataStatus, 'demo');
    assert.equal(payload.metadata.mlStatus, 'demo_placeholder');
    assert.equal(payload.metadata.fallback, true);
    assert.equal(payload.candidates[0].dataStatus, 'demo');
    assert.equal(payload.candidates[0].mlStatus, 'demo_placeholder');
  });
}
