import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promises as fs } from 'node:fs';

import Fastify from 'fastify';
import cors from '@fastify/cors';
import dotenv from 'dotenv';

import { checkHardContraindications } from './rules/contraindications.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Single shared .env lives at the repo root, not inside backend/.
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || '0.0.0.0';
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';
const configuredMlTimeoutMs = Number(process.env.ML_SERVICE_TIMEOUT_MS);
const ML_SERVICE_TIMEOUT_MS = Number.isFinite(configuredMlTimeoutMs) && configuredMlTimeoutMs > 0
  ? configuredMlTimeoutMs
  : 15000;

const DISEASES = [
  { id: 'hypertension', name: 'Hypertension', kind: 'Disease' },
  { id: 'type-2-diabetes', name: 'Type 2 Diabetes', kind: 'Disease' },
  { id: 'coronary-artery-disease', name: 'Coronary Artery Disease', kind: 'Disease' },
];

const DRUGS = {
  lisinopril: {
    id: 'lisinopril',
    name: 'Lisinopril',
    kind: 'Drug',
    dosageForms: ['tablet'],
    availableStrengths: ['5 mg', '10 mg', '20 mg'],
    source: 'Hetionet fragment',
    relationships: [
      { type: 'treats', target: 'hypertension', source: 'Hetionet', evidenceType: 'known' },
    ],
  },
  amlodipine: {
    id: 'amlodipine',
    name: 'Amlodipine',
    kind: 'Drug',
    dosageForms: ['tablet'],
    availableStrengths: ['5 mg', '10 mg'],
    source: 'Hetionet fragment',
    relationships: [
      { type: 'treats', target: 'hypertension', source: 'Hetionet', evidenceType: 'known' },
    ],
  },
  metformin: {
    id: 'metformin',
    name: 'Metformin',
    kind: 'Drug',
    dosageForms: ['tablet'],
    availableStrengths: ['500 mg', '850 mg', '1000 mg'],
    source: 'Hetionet fragment',
    relationships: [
      { type: 'treats', target: 'type-2-diabetes', source: 'Hetionet', evidenceType: 'known' },
    ],
  },
  empagliflozin: {
    id: 'empagliflozin',
    name: 'Empagliflozin',
    kind: 'Drug',
    dosageForms: ['tablet'],
    availableStrengths: ['10 mg', '25 mg'],
    source: 'Hetionet fragment',
    relationships: [
      { type: 'treats', target: 'type-2-diabetes', source: 'Hetionet', evidenceType: 'known' },
    ],
  },
  aspirin: {
    id: 'aspirin',
    name: 'Aspirin',
    kind: 'Drug',
    dosageForms: ['tablet'],
    availableStrengths: ['81 mg', '325 mg'],
    source: 'Hetionet fragment',
    relationships: [
      { type: 'treats', target: 'coronary-artery-disease', source: 'Hetionet', evidenceType: 'known' },
    ],
  },
  atorvastatin: {
    id: 'atorvastatin',
    name: 'Atorvastatin',
    kind: 'Drug',
    dosageForms: ['tablet'],
    availableStrengths: ['10 mg', '20 mg', '40 mg'],
    source: 'Hetionet fragment',
    relationships: [
      { type: 'treats', target: 'coronary-artery-disease', source: 'Hetionet', evidenceType: 'known' },
    ],
  },
  maoi: {
    id: 'maoi',
    name: 'MAOI',
    kind: 'Drug',
    dosageForms: ['reference'],
    availableStrengths: ['reference only'],
    source: 'PolyMerge Safety Rules',
    relationships: [],
  },
  ssri: {
    id: 'ssri',
    name: 'SSRI',
    kind: 'Drug',
    dosageForms: ['reference'],
    availableStrengths: ['reference only'],
    source: 'PolyMerge Safety Rules',
    relationships: [],
  },
};

const history = new Map();

function normalizeDiseases(diseases) {
  if (!Array.isArray(diseases) || diseases.length === 0) {
    return { error: 'diseases[] is required' };
  }

  if (diseases.length > 10) {
    return { error: 'diseases[] must contain at most 10 items' };
  }

  if (diseases.some((disease) => typeof disease !== 'string')) {
    return { error: 'diseases[] must contain only strings' };
  }

  const normalized = diseases
    .map((disease) => String(disease).trim())
    .filter(Boolean)
    .map((disease) => disease.toLowerCase());

  if (normalized.length === 0) {
    return { error: 'diseases[] is required' };
  }

  const unknown = normalized.filter((disease) => !DISEASES.some((item) => item.id === disease || item.name.toLowerCase() === disease));

  if (unknown.length > 0) {
    return { error: `Unknown disease requested: ${unknown.join(', ')}` };
  }

  return { diseases: normalized };
}

function normalizeOptimizationConfig(optimizationConfig) {
  if (optimizationConfig == null) {
    return { optimizationConfig: {} };
  }

  if (typeof optimizationConfig !== 'object' || Array.isArray(optimizationConfig)) {
    return { error: 'optimizationConfig must be an object' };
  }

  return { optimizationConfig };
}

function createDemoSearchResult(inputDiseases, fallbackReason = 'ml_service_unavailable') {
  const orderedDiseases = inputDiseases.map((diseaseId) => DISEASES.find((item) => item.id === diseaseId) ?? { id: diseaseId, name: diseaseId });

  const candidateBuckets = {
    hypertension: [
      { drugs: ['lisinopril', 'metformin'], coverage: 1.0, interactionRisk: 0.12, synergyScore: 0.81, confidence: 0.78, evidenceLevel: 'medium' },
      { drugs: ['amlodipine', 'metformin'], coverage: 1.0, interactionRisk: 0.18, synergyScore: 0.74, confidence: 0.71, evidenceLevel: 'medium' },
    ],
    'type-2-diabetes': [
      { drugs: ['metformin', 'empagliflozin'], coverage: 1.0, interactionRisk: 0.16, synergyScore: 0.83, confidence: 0.80, evidenceLevel: 'medium' },
      { drugs: ['metformin', 'lisinopril'], coverage: 1.0, interactionRisk: 0.14, synergyScore: 0.75, confidence: 0.73, evidenceLevel: 'medium' },
    ],
    'coronary-artery-disease': [
      { drugs: ['aspirin', 'atorvastatin'], coverage: 1.0, interactionRisk: 0.11, synergyScore: 0.86, confidence: 0.82, evidenceLevel: 'high' },
      { drugs: ['aspirin', 'lisinopril'], coverage: 1.0, interactionRisk: 0.15, synergyScore: 0.76, confidence: 0.70, evidenceLevel: 'medium' },
    ],
  };

  const diseasePool = orderedDiseases.flatMap((disease) => candidateBuckets[disease.id] ?? []);
  const candidates = diseasePool
    .slice(0, 3)
    .map((candidate, index) => ({
      rank: index + 1,
      drugs: candidate.drugs,
      coverage: candidate.coverage,
      interactionRisk: candidate.interactionRisk,
      synergyScore: candidate.synergyScore,
      drugCount: candidate.drugs.length,
      evidenceLevel: candidate.evidenceLevel,
      confidence: candidate.confidence,
      dataStatus: 'demo',
      mlStatus: 'demo_placeholder',
      status: 'accepted',
      evidence: [
        {
          source: 'Hetionet',
          relationship: 'treats',
          evidenceType: 'known',
          confidence: null,
        },
        {
          source: 'PolyMerge Demo Pipeline',
          relationship: 'DDI',
          evidenceType: 'predicted',
          score: candidate.interactionRisk,
          modelVersion: 'demo-0.1.0',
        },
        {
          source: 'PolyMerge Safety Rules',
          evidenceType: 'rule',
          status: 'passed',
        },
      ],
      reasons: [
        'Selected disease cluster coverage is computed from treatment relationships represented in the knowledge graph.',
        'Demo interaction and synergy values are clearly labeled and should not be used as clinical claims.',
      ],
    }));

  return {
    queryId: `demo-${Date.now()}`,
    diseases: orderedDiseases.map((disease) => disease.name),
    candidates,
    metadata: {
      model: 'PolyMerge Demo Pipeline',
      modelVersion: 'demo-0.1.0',
      dataset: 'Hetionet fragment',
      graph: 'Neo4j fragment',
      timestamp: new Date().toISOString(),
      dataStatus: 'demo',
      mlStatus: 'demo_placeholder',
      fallback: true,
      fallbackReason,
      disclaimer: 'Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.',
    },
  };
}

function validateMlResult(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('ML engine returned a non-object response');
  }

  if (typeof payload.queryId !== 'string' || !payload.queryId.trim()) {
    throw new Error('ML engine response is missing queryId');
  }

  if (!Array.isArray(payload.diseases) || !Array.isArray(payload.candidates)) {
    throw new Error('ML engine response is missing diseases or candidates');
  }

  if (payload.diseases.some((disease) => typeof disease !== 'string')) {
    throw new Error('ML engine response diseases must be strings');
  }

  if (!payload.metadata || typeof payload.metadata !== 'object' || Array.isArray(payload.metadata)) {
    throw new Error('ML engine response is missing metadata');
  }

  if (
    typeof payload.metadata.dataStatus !== 'string'
    || !payload.metadata.dataStatus
    || typeof payload.metadata.mlStatus !== 'string'
    || !payload.metadata.mlStatus
  ) {
    throw new Error('ML engine response is missing dataStatus or mlStatus');
  }

  for (const candidate of payload.candidates) {
    if (!candidate || typeof candidate !== 'object' || !Array.isArray(candidate.drugs)) {
      throw new Error('ML engine returned an invalid candidate');
    }

    if (candidate.drugs.some((drug) => typeof drug !== 'string')) {
      throw new Error('ML engine candidate drugs must be strings');
    }

    if (candidate.dataStatus != null && typeof candidate.dataStatus !== 'string') {
      throw new Error('ML engine candidate dataStatus must be a string');
    }

    if (
      payload.metadata.mlStatus === 'not_applied'
      && (candidate.interactionRisk != null || candidate.synergyScore != null)
    ) {
      throw new Error('ML engine returned prediction scores while mlStatus is not_applied');
    }
  }

  return payload;
}

async function fetchMlResult(diseases) {
  try {
    const response = await fetch(`${ML_SERVICE_URL}/predict/combination`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases }),
      signal: AbortSignal.timeout(ML_SERVICE_TIMEOUT_MS),
    });

    if (!response.ok) {
      throw new Error(`ML engine responded ${response.status}`);
    }

    return validateMlResult(await response.json());
  } catch (error) {
    const fallbackReason = error?.name === 'TimeoutError'
      ? 'ml_service_timeout'
      : 'ml_service_unavailable_or_invalid';
    return createDemoSearchResult(diseases, fallbackReason);
  }
}

function buildExplainability(candidate) {
  return {
    candidateId: candidate.rank,
    status: candidate.status,
    graph: {
      nodes: candidate.drugs.map((drug) => ({ id: drug, kind: 'Drug' })),
      edges: candidate.drugs.map((drug, index) => ({
        source: drug,
        target: candidate.drugs[(index + 1) % candidate.drugs.length],
        relationship: index % 2 === 0 ? 'known relationship' : 'predicted relationship',
        evidenceType: index % 2 === 0 ? 'known' : 'predicted',
      })),
    },
    explanation: [
      'The candidate covers the requested disease cluster using treatment relationships represented in the knowledge graph.',
      'Predicted interaction risk and synergy are research-only model estimates and should be reviewed by experts.',
      'A hard contraindication rule is applied independently of model predictions and can reject the candidate outright.',
    ],
    reasons: candidate.reasons ?? [],
  };
}

const app = Fastify({ logger: true });

await app.register(cors, {
  origin: process.env.CORS_ORIGIN || true,
});

app.get('/health', async () => ({ status: 'ok', service: 'polymerge-backend' }));

app.get('/', async (_, reply) => {
  const html = await fs.readFile(path.join(__dirname, '../../frontend/index.html'), 'utf8');
  return reply.type('text/html').send(html);
});

app.get('/frontend/:file', async (request, reply) => {
  const requestedFile = request.params.file;
  const safeFile = path.basename(requestedFile);
  const filePath = path.join(__dirname, '../../frontend', safeFile);

  try {
    const contents = await fs.readFile(filePath, 'utf8');
    const extension = path.extname(safeFile);
    const types = {
      '.css': 'text/css',
      '.js': 'text/javascript',
      '.html': 'text/html',
    };
    return reply.type(types[extension] || 'text/plain').send(contents);
  } catch {
    return reply.code(404).send({ error: 'File not found' });
  }
});

app.get('/api/diseases', async () => ({
  diseases: DISEASES,
}));

app.get('/api/drugs/:id', async (request, reply) => {
  const paramId = String(request.params.id).trim().toLowerCase();
  const drug = DRUGS[paramId];

  if (!drug) {
    return reply.code(404).send({ error: 'Drug not found' });
  }

  return {
    ...drug,
    relationships: drug.relationships,
  };
});

app.get('/api/drugs/:id/interactions', async (request, reply) => {
  const paramId = String(request.params.id).trim().toLowerCase();
  const drug = DRUGS[paramId];

  if (!drug) {
    return reply.code(404).send({ error: 'Drug not found' });
  }

  return {
    drugId: drug.id,
    interactions: [
      {
        target: paramId === 'maoi' ? 'ssri' : 'hypertension',
        relationship: 'predicted',
        score: 0.18,
        evidenceType: 'predicted',
        source: 'PolyMerge Demo Pipeline',
        confidence: 'medium',
      },
    ],
  };
});

app.post('/api/combinations/search', async (request, reply) => {
  if (!request.body || typeof request.body !== 'object' || Array.isArray(request.body)) {
    return reply.code(400).send({
      error: 'Request body must be a JSON object',
      code: 'INVALID_REQUEST',
    });
  }

  const { diseases = [], optimizationConfig: requestedOptimizationConfig = {} } = request.body;
  const normalized = normalizeDiseases(diseases);

  if (normalized.error) {
    return reply.code(400).send({ error: normalized.error, code: 'INVALID_REQUEST' });
  }

  const normalizedConfig = normalizeOptimizationConfig(requestedOptimizationConfig);
  if (normalizedConfig.error) {
    return reply.code(400).send({ error: normalizedConfig.error, code: 'INVALID_REQUEST' });
  }

  const optimizationConfig = normalizedConfig.optimizationConfig;

  const mlResult = await fetchMlResult(normalized.diseases);

  const candidates = (mlResult.candidates ?? []).map((candidate, index) => {
    const violation = checkHardContraindications(candidate.drugs ?? []);

    return {
      ...candidate,
      rank: candidate.rank ?? index + 1,
      status: violation ? 'rejected' : candidate.status ?? 'accepted',
      reason: violation
        ? {
            type: 'hard_contraindication',
            message: violation.message,
            pair: violation.pair,
          }
        : candidate.reason ?? null,
      reasons: violation
        ? [
            'Candidate contains a prohibited interaction according to the configured safety rule.',
            'The hard safety rule blocks this candidate regardless of model score.',
          ]
        : candidate.reasons ?? [],
      dataStatus: candidate.dataStatus ?? mlResult.metadata?.dataStatus ?? 'demo',
      mlStatus: candidate.mlStatus ?? mlResult.metadata?.mlStatus ?? 'not_applied',
      optimizationConfig,
    };
  });

  const searchResult = {
    queryId: mlResult.queryId ?? `query-${Date.now()}`,
    diseases: mlResult.diseases ?? normalized.diseases,
    candidates,
    metadata: {
      ...mlResult.metadata,
      optimizationConfig,
      disclaimer: 'Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.',
    },
  };

  history.set(searchResult.queryId, searchResult);

  return searchResult;
});

app.get('/api/combinations/:id', async (request, reply) => {
  const result = history.get(request.params.id);

  if (!result) {
    return reply.code(404).send({ error: 'Combination result not found' });
  }

  return result;
});

app.get('/api/combinations/:id/explain', async (request, reply) => {
  const result = history.get(request.params.id);

  if (!result) {
    return reply.code(404).send({ error: 'Combination result not found' });
  }

  const explainability = result.candidates.map((candidate) => buildExplainability(candidate));

  return {
    queryId: result.queryId,
    diseases: result.diseases,
    candidates: explainability,
  };
});

app.get('/api/history', async () => ({
  history: Array.from(history.values()),
}));

export { app };

const isDirectRun = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));

if (isDirectRun) {
  app.listen({ port: PORT, host: HOST }).catch((err) => {
    app.log.error(err);
    process.exit(1);
  });
}
