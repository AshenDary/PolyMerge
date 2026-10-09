import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import Fastify from 'fastify';

import { app, createModelComparisonHandler } from '../src/server.js';

after(async () => {
  await app.close();
});

function reportRows(report, headerText) {
  const lines = report.split(/\r?\n/);
  const headerIndex = lines.findIndex((line) => line.startsWith(headerText));
  const headers = lines[headerIndex].trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim());
  const rows = [];
  for (const line of lines.slice(headerIndex + 2)) {
    if (!line.startsWith('|')) break;
    const cells = line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim().replace(/`/g, ''));
    rows.push(Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ''])));
  }
  return rows;
}

test('model comparison endpoint serves the report data without replacing its results', async () => {
  const report = readFileSync(new URL('../../docs/sprint4-model-comparison.md', import.meta.url), 'utf8');
  const response = await app.inject({ method: 'GET', url: '/api/model-comparison' });
  const payload = response.json();

  assert.equal(response.statusCode, 200);
  assert.equal(payload.source, 'docs/sprint4-model-comparison.md');
  assert.deepEqual(payload.rows, reportRows(report, '| Model | Mean Macro F1 |'));
  assert.deepEqual(payload.parameters, reportRows(report, '| Model | Fixed parameters |'));
  assert.equal(payload.rows.length, 3);
  assert.deepEqual(payload.rows.map((row) => row.Model), [
    'LogisticRegression',
    'RandomForestClassifier',
    'HistGradientBoostingClassifier',
  ]);
});

test('model comparison endpoint reports an unavailable source report as 503', async () => {
  const testApp = Fastify();
  testApp.get('/api/model-comparison', createModelComparisonHandler(async () => {
    const error = new Error('report unavailable in test');
    error.code = 'ENOENT';
    throw error;
  }));
  try {
    const response = await testApp.inject({ method: 'GET', url: '/api/model-comparison' });
    assert.equal(response.statusCode, 503);
    assert.deepEqual(response.json(), { error: 'Model comparison report is unavailable' });
  } finally {
    await testApp.close();
  }
});

test('tracked Sprint 3 EDA figures are served for Model Analysis', async () => {
  const response = await app.inject({
    method: 'GET',
    url: '/docs/figures/sprint3/severity_distribution.svg',
  });

  assert.equal(response.statusCode, 200);
  assert.equal(response.headers['content-type'], 'image/svg+xml');
  assert.match(response.body, /<svg/);
});
