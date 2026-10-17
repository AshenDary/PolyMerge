import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';
import { BlockList, isIP } from 'node:net';

export const PUBLIC_ERROR = 'Analysis is temporarily unavailable. Please try again.';

export function proxyTrust(env = process.env) {
  if (!env.TRUST_PROXY_CIDRS?.trim()) return false;
  const entries = env.TRUST_PROXY_CIDRS.split(',').map(value => value.trim());
  for (const entry of entries) {
    const [address, prefix, ...extra] = entry.split('/');
    const family = isIP(address);
    if (!family || extra.length || (prefix !== undefined &&
        (!/^\d+$/.test(prefix) || Number(prefix) < 1 || Number(prefix) > (family === 4 ? 32 : 128)))) {
      throw new Error('TRUST_PROXY_CIDRS requires explicit IP addresses or non-universal CIDRs');
    }
    const network = new BlockList();
    network.addSubnet(address, Number(prefix ?? (family === 4 ? 32 : 128)), family === 4 ? 'ipv4' : 'ipv6');
    if (network.check('0.0.0.0', 'ipv4') && network.check('255.255.255.255', 'ipv4')) {
      throw new Error('TRUST_PROXY_CIDRS requires explicit IP addresses or non-universal CIDRs');
    }
  }
  return entries;
}

function origins(value, production) {
  return (value || '').split(',').filter(Boolean).map((value) => {
    const url = new URL(value.trim());
    if (url.origin !== value.trim() || url.username || url.password
        || (production ? url.protocol !== 'https:' : !['http:', 'https:'].includes(url.protocol))) {
      throw new Error('Allowed origins must be exact origins; production requires HTTPS');
    }
    return url.origin;
  });
}

export async function installSecurity(app, env = process.env) {
  const production = env.NODE_ENV === 'production';
  const allowed = origins(env.CORS_ORIGIN, production);
  const frames = origins(env.STREAMLIT_ORIGIN, production);
  const legacy = !production && env.POLYMERGE_ENABLE_LEGACY === 'true';
  let active = 0;
  await app.register(cors, { origin: allowed, credentials: false, methods: ['GET', 'POST'] });
  await app.register(rateLimit, {
    max: Number(env.RATE_LIMIT_MAX) || 120,
    timeWindow: 60000,
    cache: 10000,
  });
  app.addHook('onRequest', async (request, reply) => {
    const route = request.routeOptions.url || '';
    if (request.headers.origin && !allowed.includes(request.headers.origin)) {
      return reply.code(403).send({ error: 'Origin not permitted' });
    }
    if (route === '/api/history' || route.includes('/explain')
        || route === '/api/combinations/:id') {
      return reply.code(404).send({ error: 'Server history is disabled' });
    }
    if (!legacy && (route.startsWith('/api/drugs/') || route === '/api/combinations/search'
        || route === '/api/ddi-severity/predict')) {
      return reply.code(404).send({ error: 'Endpoint unavailable' });
    }
  });
  const analysisLimit = app.createRateLimit({ max: Number(env.ANALYSIS_RATE_LIMIT_MAX) || 6, timeWindow: 60000 });
  app.addHook('preHandler', async (request, reply) => {
    if (request.routeOptions.url !== '/api/candidate-sets/search') return;
    const config = request.body?.candidateSetConfig;
    if (production && (config?.maxDrugCount > 3 || config?.maxCandidateSets > 100)) {
      return reply.code(422).send({ error: 'Public demo permits up to three drugs and 100 returned candidates' });
    }
    const result = await analysisLimit(request);
    if (!result.isAllowed && result.isExceeded) return reply.code(429).header('Retry-After', '60').send({ error: 'Analysis quota exceeded. Try again shortly.' });
    if (active >= 1) return reply.code(503).header('Retry-After', '2').send({ error: 'Analysis busy. Try again shortly.' });
    active += 1;
    request.analysisAdmitted = true;
  });
  app.addHook('onResponse', async (request) => {
    if (request.analysisAdmitted) active -= 1;
  });
  app.addHook('onSend', async (_request, reply, payload) => {
    reply.header('Content-Security-Policy', `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors ${frames.length ? frames.join(' ') : "'none'"}`);
    reply.header('X-Content-Type-Options', 'nosniff');
    reply.header('Referrer-Policy', 'no-referrer');
    reply.header('Cache-Control', 'no-store');
    if (production) reply.header('Strict-Transport-Security', 'max-age=31536000');
    return payload;
  });
  app.setErrorHandler((error, request, reply) => {
    request.log.warn({ code: error.code, requestId: request.id }, 'Request failed');
    const status = error.statusCode >= 400 && error.statusCode < 500 ? error.statusCode : 503;
    return reply.code(status).send({ error: status === 413 ? 'Request body too large' : status < 500 ? 'Invalid request' : PUBLIC_ERROR, requestId: request.id });
  });
}
