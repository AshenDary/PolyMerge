import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import Fastify from 'fastify';
import { installSecurity, proxyTrust } from '../src/security.js';

test('proxy configuration rejects aliases, universal networks and malformed entries', () => {
  assert.equal(proxyTrust({}), false);
  assert.deepEqual(proxyTrust({ TRUST_PROXY_CIDRS: '192.0.2.1/32,2001:db8::/64' }), ['192.0.2.1/32', '2001:db8::/64']);
  for (const value of ['true', '*', 'loopback', '0.0.0.0/0', '::/0', '::ffff:0:0/96', '1.2.3.4/33', '::1/129', '1.2.3.4,', '1.2.3.4/32/1']) {
    assert.throws(() => proxyTrust({ TRUST_PROXY_CIDRS: value }), /explicit IP/);
  }
});

async function backend(t, trust) {
  const app = Fastify({ trustProxy: trust, bodyLimit: 32768 });
  await installSecurity(app, { NODE_ENV: 'production', ANALYSIS_RATE_LIMIT_MAX: '1' });
  app.post('/api/candidate-sets/search', async request => ({ ip: request.ip }));
  t.after(() => app.close());
  await app.listen({ host: '127.0.0.1', port: 0 });
  return app;
}

async function edge(t, app, observedClient) {
  // A test edge appends its independently observed client, never a client header.
  // Synthetic addresses model separate visitors without claiming Render behavior.
  const proxy = http.createServer((req, res) => {
    const chain = [req.headers['x-forwarded-for'], observedClient].filter(Boolean).join(', ');
    const upstream = http.request({ hostname: '127.0.0.1', port: app.server.address().port,
      path: req.url, method: req.method, headers: { ...req.headers, 'x-forwarded-for': chain, connection: 'close' } }, response => {
      res.writeHead(response.statusCode, response.headers);
      response.pipe(res);
    });
    upstream.on('error', () => { res.writeHead(502); res.end(); });
    req.pipe(upstream);
  });
  await new Promise(resolve => proxy.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { proxy.close(resolve); proxy.closeAllConnections(); }));
  return `http://127.0.0.1:${proxy.address().port}/api/candidate-sets/search`;
}

test('real loopback proxy preserves quotas despite spoofed leftmost forwarded IPs', async t => {
  const app = await backend(t, proxyTrust({ TRUST_PROXY_CIDRS: '127.0.0.1/32' }));
  const visitorA = await edge(t, app, '198.51.100.1');
  const visitorB = await edge(t, app, '198.51.100.2');
  const options = spoof => ({ method: 'POST', headers: { 'content-type': 'application/json', 'x-forwarded-for': spoof }, body: '{}' });
  const first = await fetch(visitorA, options('203.0.113.1'));
  assert.equal(first.status, 200);
  assert.equal((await first.json()).ip, '198.51.100.1');
  assert.equal((await fetch(visitorA, options('203.0.113.2'))).status, 429);
  assert.equal((await fetch(visitorB, options('203.0.113.1'))).status, 200);
  const direct = await app.inject({ method: 'POST', url: '/api/candidate-sets/search', payload: {},
    remoteAddress: '203.0.113.3', headers: { 'x-forwarded-for': '198.51.100.2' } });
  assert.equal(direct.json().ip, '203.0.113.3');
});

test('unconfigured proxy trust aggregates clients instead of trusting their headers', async t => {
  const app = await backend(t, proxyTrust({}));
  const first = await edge(t, app, '198.51.100.1');
  const second = await edge(t, app, '198.51.100.2');
  const request = { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' };
  assert.equal((await fetch(first, request)).status, 200);
  assert.equal((await fetch(second, request)).status, 429);
});
