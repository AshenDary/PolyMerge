import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const frontendDir = path.resolve(process.cwd(), '../frontend');

test('frontend loads Sprint 5 explainability assets in the main application', () => {
  const html = readFileSync(path.join(frontendDir, 'index.html'), 'utf8');

  assert.match(html, /\/frontend\/explainability\.css/);
  assert.match(html, /\/frontend\/explainability\.js/);
  assert.match(html, /id="explainability"/);
});

test('frontend uses candidate-set search and canonical explainability endpoint', () => {
  const app = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');
  const explainability = readFileSync(path.join(frontendDir, 'explainability.js'), 'utf8');

  assert.match(app, /\/api\/candidate-sets\/search/);
  assert.match(app, /window\.PolyMergeExplainability\?\.loadExplainability/);
  assert.match(explainability, /\/api\/candidate-sets\/\$\{encodeURIComponent\(queryId\)\}\/explain/);
  assert.match(explainability, /ML not applied \/ unavailable/);
});
