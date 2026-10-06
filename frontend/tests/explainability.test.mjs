import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = await readFile(path.join(frontendDir, 'index.html'), 'utf8');
const app = await readFile(path.join(frontendDir, 'app.js'), 'utf8');
const explainabilityClient = await readFile(path.join(frontendDir, 'explainability.js'), 'utf8');

test('main page loads the explainability client before the dashboard controller', () => {
  const clientPosition = html.indexOf('/frontend/explainability.js');
  const appPosition = html.indexOf('/frontend/app.js');
  assert.ok(clientPosition >= 0);
  assert.ok(appPosition > clientPosition);
  assert.match(html, /\/frontend\/explainability\.css/);
});

test('dashboard uses the canonical candidate-set route and keeps three evidence channels', () => {
  assert.match(app, /fetch\('\/api\/candidate-sets\/search'/);
  assert.doesNotMatch(app, /\/api\/combinations\/search/);
  assert.match(app, /Graph Evidence/);
  assert.match(app, /Deterministic Safety Rules/);
  assert.match(app, /ML Prediction/);
});

test('explainability client requests the structured result for an encoded query ID', async () => {
  let requestedUrl;
  const sandbox = {
    window: {},
    fetch: async (url) => {
      requestedUrl = url;
      return { ok: true, json: async () => ({ candidates: [{ rank: 1 }] }) };
    },
  };
  vm.runInNewContext(explainabilityClient, sandbox);

  const result = await sandbox.window.PolyMergeExplainability.fetchStructured('query / 1');
  assert.equal(requestedUrl, '/api/candidate-sets/query%20%2F%201/explain?format=structured');
  assert.equal(result.candidates[0].rank, 1);
});

test('explainability client returns the backend error for unavailable results', async () => {
  const sandbox = {
    window: {},
    fetch: async () => ({ ok: false, status: 503, json: async () => ({ error: 'Graph unavailable' }) }),
  };
  vm.runInNewContext(explainabilityClient, sandbox);

  await assert.rejects(
    sandbox.window.PolyMergeExplainability.fetchStructured('query-1'),
    /Graph unavailable/,
  );
});
