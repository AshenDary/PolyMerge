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
const ML_SERVICE_TIMEOUT_MS = Number(process.env.ML_SERVICE_TIMEOUT_MS) || 15000;

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

export function normalizeDiseases(diseases) {
  if (!Array.isArray(diseases) || diseases.length === 0) {
    return { error: 'diseases[] is required' };
  }

  if (diseases.length > 10 || diseases.some((disease) => typeof disease !== 'string')) {
    return { error: 'diseases[] must contain between 1 and 10 disease names or IDs' };
  }

  const normalized = [...new Set(diseases
    .map((disease) => disease.trim())
    .filter(Boolean)
  )];

  if (normalized.length === 0) {
    return { error: 'diseases[] is required' };
  }

  return { diseases: normalized };
}

function normalizeLookupKey(value) {
  return String(value).trim().toLowerCase();
}

export function resolveDiseasesFromCatalog(diseases, catalog) {
  const byId = new Map();
  const byName = new Map();

  for (const disease of catalog) {
    byId.set(normalizeLookupKey(disease.id), disease);
    byName.set(normalizeLookupKey(disease.name), disease);
  }

  const resolved = [];
  const unknown = [];
  const seen = new Set();

  for (const disease of diseases) {
    const key = normalizeLookupKey(disease);
    const match = byId.get(key) ?? byName.get(key);

    if (!match) {
      unknown.push(disease);
      continue;
    }

    if (!seen.has(match.id)) {
      resolved.push(match);
      seen.add(match.id);
    }
  }

  if (unknown.length > 0) {
    return { error: `Unknown disease requested: ${unknown.join(', ')}`, unknown };
  }

  return { diseases: resolved };
}

export function normalizeOptimizationConfig(config) {
  if (config === undefined) {
    return { optimizationConfig: {} };
  }

  if (config === null || typeof config !== 'object' || Array.isArray(config)) {
    return { error: 'optimizationConfig must be an object' };
  }

  const normalized = {};
  if (config.maxDrugCount !== undefined) {
    if (!Number.isInteger(config.maxDrugCount) || config.maxDrugCount < 0 || config.maxDrugCount > 50) {
      return { error: 'optimizationConfig.maxDrugCount must be an integer between 0 and 50' };
    }
    normalized.maxDrugCount = config.maxDrugCount;
  }

  if (config.minimumCoverage !== undefined) {
    if (typeof config.minimumCoverage !== 'number' || !Number.isFinite(config.minimumCoverage)
      || config.minimumCoverage < 0 || config.minimumCoverage > 1) {
      return { error: 'optimizationConfig.minimumCoverage must be a number between 0 and 1' };
    }
    normalized.minimumCoverage = config.minimumCoverage;
  }

  return { optimizationConfig: normalized };
}

export function normalizeCandidateSetConfig(config) {
  if (config === undefined) {
    return { candidateSetConfig: {} };
  }
  if (config === null || typeof config !== 'object' || Array.isArray(config)) {
    return { error: 'candidateSetConfig must be an object' };
  }

  const normalized = {};
  if (config.maxDrugCount !== undefined) {
    if (!Number.isInteger(config.maxDrugCount) || config.maxDrugCount < 1 || config.maxDrugCount > 10) {
      return { error: 'candidateSetConfig.maxDrugCount must be an integer between 1 and 10' };
    }
    normalized.maxDrugCount = config.maxDrugCount;
  }
  if (config.maxCandidateSets !== undefined) {
    if (!Number.isInteger(config.maxCandidateSets)
      || config.maxCandidateSets < 1 || config.maxCandidateSets > 500) {
      return { error: 'candidateSetConfig.maxCandidateSets must be an integer between 1 and 500' };
    }
    normalized.maxCandidateSets = config.maxCandidateSets;
  }
  return { candidateSetConfig: normalized };
}

function createDemoSearchResult(inputDiseases, warning = 'ML engine unavailable; returning explicitly labeled demo output.') {
  const orderedDiseases = inputDiseases.map((disease) => (
    typeof disease === 'string' ? { id: disease, name: disease } : disease
  ));

  return {
    queryId: `demo-${Date.now()}`,
    diseaseIds: orderedDiseases.map((disease) => disease.id),
    diseases: orderedDiseases.map((disease) => disease.name),
    candidates: [],
    candidateSets: [],
    metadata: {
      model: 'No predictive ML model applied',
      modelVersion: null,
      dataset: null,
      graph: null,
      timestamp: new Date().toISOString(),
      dataStatus: 'demo',
      mlStatus: 'demo',
      upstreamStatus: 'fallback',
      warning,
      fallbackReason: 'No graph-backed candidate data returned because the ML graph service was unavailable or invalid.',
      disclaimer: 'Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.',
    },
  };
}

function validateDiseaseCatalog(payload) {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload) || !Array.isArray(payload.diseases)) {
    throw new Error('ML disease catalog response is missing diseases[]');
  }

  const diseases = payload.diseases.map((disease) => {
    if (disease === null || typeof disease !== 'object' || Array.isArray(disease)
      || typeof disease.id !== 'string' || typeof disease.name !== 'string') {
      throw new Error('ML disease catalog returned an invalid disease schema');
    }

    return {
      id: disease.id,
      name: disease.name,
      kind: disease.kind ?? 'Disease',
      source: disease.source,
      graphVersion: disease.graphVersion,
    };
  });

  return diseases;
}

async function fetchDiseaseCatalog(options = {}) {
  const fetchImpl = options.fetchImpl ?? fetch;
  const mlServiceUrl = options.mlServiceUrl ?? ML_SERVICE_URL;
  const timeoutMs = options.timeoutMs ?? ML_SERVICE_TIMEOUT_MS;
  const response = await fetchImpl(`${mlServiceUrl}/api/diseases`, {
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!response.ok) {
    throw new Error(`ML disease catalog responded ${response.status}`);
  }

  return validateDiseaseCatalog(await response.json());
}

export function validateMlResult(payload) {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('ML engine returned a non-object response');
  }
  if (!Array.isArray(payload.diseases) || !Array.isArray(payload.candidates)) {
    throw new Error('ML engine response is missing diseases[] or candidates[]');
  }
  if (payload.metadata === null || typeof payload.metadata !== 'object' || Array.isArray(payload.metadata)) {
    throw new Error('ML engine response is missing metadata');
  }
  if (typeof payload.metadata.dataStatus !== 'string' || typeof payload.metadata.mlStatus !== 'string') {
    throw new Error('ML engine response is missing dataStatus or mlStatus provenance');
  }
  if (payload.candidates.some((candidate) => candidate === null || typeof candidate !== 'object'
    || !Array.isArray(candidate.drugs) || candidate.drugs.some((drug) => typeof drug !== 'string'))) {
    throw new Error('ML engine returned an invalid candidate schema');
  }
  return payload;
}

export function validateCandidateSetResult(payload) {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('ML engine returned a non-object candidate-set response');
  }
  if (!Array.isArray(payload.diseaseIds) || !Array.isArray(payload.diseases)
    || !Array.isArray(payload.candidateSets)) {
    throw new Error('ML candidate-set response is missing diseaseIds[], diseases[], or candidateSets[]');
  }
  if (payload.metadata === null || typeof payload.metadata !== 'object' || Array.isArray(payload.metadata)
    || typeof payload.metadata.dataStatus !== 'string'
    || typeof payload.metadata.mlStatus !== 'string') {
    throw new Error('ML candidate-set response is missing provenance metadata');
  }

  if (payload.diseaseIds.some((diseaseId) => typeof diseaseId !== 'string' || !diseaseId)
    || new Set(payload.diseaseIds).size !== payload.diseaseIds.length
    || payload.diseases.some((disease) => disease === null || typeof disease !== 'object'
      || typeof disease.id !== 'string' || typeof disease.name !== 'string')
    || payload.diseases.some((disease) => !payload.diseaseIds.includes(disease.id))) {
    throw new Error('ML engine returned invalid or unstable disease identifiers');
  }

  const candidateSetIds = new Set();
  for (const candidateSet of payload.candidateSets) {
    const validStatus = candidateSet?.status === 'accepted' || candidateSet?.status === 'rejected';
    if (candidateSet === null || typeof candidateSet !== 'object' || Array.isArray(candidateSet)
      || typeof candidateSet.candidateSetId !== 'string' || !candidateSet.candidateSetId
      || !Array.isArray(candidateSet.drugs) || candidateSet.drugs.length === 0
      || candidateSet.drugs.some((drugId) => typeof drugId !== 'string' || !drugId)
      || new Set(candidateSet.drugs).size !== candidateSet.drugs.length
      || !Array.isArray(candidateSet.treatedDiseaseIds)
      || !Array.isArray(candidateSet.uncoveredDiseaseIds)
      || candidateSet.treatedDiseaseIds.some((diseaseId) => !payload.diseaseIds.includes(diseaseId))
      || candidateSet.uncoveredDiseaseIds.some((diseaseId) => !payload.diseaseIds.includes(diseaseId))
      || typeof candidateSet.coverage !== 'number'
      || candidateSet.coverage < 0 || candidateSet.coverage > 1
      || candidateSet.drugCount !== candidateSet.drugs.length
      || !validStatus
      || !Array.isArray(candidateSet.rejectionReasons)
      || (candidateSet.status === 'rejected' && candidateSet.rejectionReasons.length === 0)
      || !Array.isArray(candidateSet.evidence)
      || typeof candidateSet.dataStatus !== 'string'
      || typeof candidateSet.mlStatus !== 'string') {
      throw new Error('ML engine returned an invalid candidate-set schema');
    }
    if (candidateSetIds.has(candidateSet.candidateSetId)) {
      throw new Error('ML engine returned duplicate candidate-set IDs');
    }
    candidateSetIds.add(candidateSet.candidateSetId);
    if (candidateSet.mlStatus === 'not_applied'
      && (candidateSet.interactionRisk != null || candidateSet.synergyScore != null)) {
      throw new Error('ML engine returned prediction scores while mlStatus is not_applied');
    }
    if (candidateSet.dataStatus !== payload.metadata.dataStatus
      || candidateSet.mlStatus !== payload.metadata.mlStatus) {
      throw new Error('ML candidate-set provenance does not match response metadata');
    }
  }
  return payload;
}

async function fetchMlResult(diseases, optimizationConfig = {}, options = {}) {
  const fetchImpl = options.fetchImpl ?? fetch;
  const mlServiceUrl = options.mlServiceUrl ?? ML_SERVICE_URL;
  const timeoutMs = options.timeoutMs ?? ML_SERVICE_TIMEOUT_MS;
  try {
    const response = await fetchImpl(`${mlServiceUrl}/predict/combination`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases, optimizationConfig }),
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      throw new Error(`ML engine responded ${response.status}`);
    }

    return validateMlResult(await response.json());
  } catch (error) {
    options.logger?.warn({ error: error.message }, 'ML engine request failed; using demo fallback');
    return createDemoSearchResult(options.resolvedDiseases ?? diseases, error.message);
  }
}

async function fetchCandidateSetResult(
  diseaseIds,
  candidateSetConfig = {},
  optimizationConfig = {},
  options = {},
) {
  const fetchImpl = options.fetchImpl ?? fetch;
  const mlServiceUrl = options.mlServiceUrl ?? ML_SERVICE_URL;
  const timeoutMs = options.timeoutMs ?? ML_SERVICE_TIMEOUT_MS;
  try {
    const response = await fetchImpl(`${mlServiceUrl}/predict/candidate-sets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseaseIds, candidateSetConfig, optimizationConfig }),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response.ok) {
      throw new Error(`ML candidate-set service responded ${response.status}`);
    }
    return validateCandidateSetResult(await response.json());
  } catch (error) {
    options.logger?.warn({ error: error.message }, 'ML candidate-set request failed; using empty fallback');
    return createDemoSearchResult(options.resolvedDiseases ?? diseaseIds, error.message);
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

export const app = Fastify({ logger: process.env.NODE_ENV !== 'test' });

await app.register(cors, {
  origin: process.env.CORS_ORIGIN || true,
});

app.get('/health', async () => ({ status: 'ok', service: 'polymerge-backend' }));

app.get('/health/dependencies', async (request, reply) => {
  try {
    const response = await fetch(`${ML_SERVICE_URL}/health`, {
      signal: AbortSignal.timeout(ML_SERVICE_TIMEOUT_MS),
    });
    const payload = await response.json();
    if (!response.ok || payload?.status !== 'ok') {
      throw new Error(`ML engine health check returned ${response.status}`);
    }
    return { status: 'ok', service: 'polymerge-backend', dependencies: { mlEngine: 'ok' } };
  } catch (error) {
    request.log?.warn?.({ error: error.message }, 'ML engine health check failed');
    return reply.code(503).send({
      status: 'degraded',
      service: 'polymerge-backend',
      dependencies: { mlEngine: 'unavailable' },
    });
  }
});

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

app.get('/api/diseases', async (request, reply) => {
  try {
    return { diseases: await fetchDiseaseCatalog() };
  } catch (error) {
    request.log?.warn?.({ error: error.message }, 'Disease catalog request failed');
    return reply.code(503).send({
      error: 'Disease catalog unavailable',
      detail: error.message,
    });
  }
});

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

app.post('/api/candidate-sets/search', async (request, reply) => {
  if (request.body === null || typeof request.body !== 'object' || Array.isArray(request.body)) {
    return reply.code(400).send({ error: 'Request body must be a JSON object' });
  }

  const { diseaseIds = [], candidateSetConfig, optimizationConfig } = request.body ?? {};
  const normalizedDiseases = normalizeDiseases(diseaseIds);
  if (normalizedDiseases.error) {
    return reply.code(400).send({ error: normalizedDiseases.error });
  }
  const normalizedCandidateConfig = normalizeCandidateSetConfig(candidateSetConfig);
  if (normalizedCandidateConfig.error) {
    return reply.code(400).send({ error: normalizedCandidateConfig.error });
  }
  const normalizedOptimization = normalizeOptimizationConfig(optimizationConfig);
  if (normalizedOptimization.error) {
    return reply.code(400).send({ error: normalizedOptimization.error });
  }

  let diseaseCatalog;
  try {
    diseaseCatalog = await fetchDiseaseCatalog();
  } catch (error) {
    request.log?.warn?.({ error: error.message }, 'Disease catalog validation failed');
    return reply.code(503).send({ error: 'Disease catalog unavailable', detail: error.message });
  }

  const resolved = resolveDiseasesFromCatalog(normalizedDiseases.diseases, diseaseCatalog);
  if (resolved.error) {
    return reply.code(400).send({
      error: resolved.error,
      unknownDiseaseIds: resolved.unknown,
    });
  }

  const resolvedDiseaseIds = resolved.diseases.map((disease) => disease.id);
  const mlResult = await fetchCandidateSetResult(
    resolvedDiseaseIds,
    normalizedCandidateConfig.candidateSetConfig,
    normalizedOptimization.optimizationConfig,
    { logger: request.log, resolvedDiseases: resolved.diseases },
  );
  const dataStatus = mlResult.metadata.dataStatus;
  const mlStatus = mlResult.metadata.mlStatus;
  const candidateSets = (mlResult.candidateSets ?? []).map((candidateSet, index) => {
    const violation = checkHardContraindications(candidateSet.drugs);
    const rejectionReasons = [...(candidateSet.rejectionReasons ?? [])];
    if (violation && !rejectionReasons.some((reason) => reason.type === violation.type)) {
      rejectionReasons.push({
        type: violation.type,
        message: violation.message,
        pair: violation.pair,
        stage: 'backend_validation',
      });
    }
    return {
      ...candidateSet,
      rank: candidateSet.rank ?? index + 1,
      status: violation ? 'rejected' : candidateSet.status,
      rejectionReasons,
      dataStatus: candidateSet.dataStatus ?? dataStatus,
      mlStatus: candidateSet.mlStatus ?? mlStatus,
      interactionRisk: null,
      synergyScore: null,
    };
  });

  const result = {
    queryId: mlResult.queryId ?? `candidate-sets-${Date.now()}`,
    diseaseIds: mlResult.diseaseIds ?? resolvedDiseaseIds,
    diseases: mlResult.diseases ?? resolved.diseases,
    candidateSets,
    metadata: {
      ...mlResult.metadata,
      dataStatus,
      mlStatus,
      candidateSetConfig: normalizedCandidateConfig.candidateSetConfig,
      optimizationConfig: normalizedOptimization.optimizationConfig,
      disclaimer: 'Research decision-support only. Candidate-set coverage is graph-derived and is not a clinical efficacy, safety, or prescribing claim.',
    },
  };
  history.set(result.queryId, result);
  return result;
});

app.post('/api/combinations/search', async (request, reply) => {
  if (request.body === null || typeof request.body !== 'object' || Array.isArray(request.body)) {
    return reply.code(400).send({ error: 'Request body must be a JSON object' });
  }

  const { diseases = [], optimizationConfig } = request.body ?? {};
  const normalized = normalizeDiseases(diseases);

  if (normalized.error) {
    return reply.code(400).send({ error: normalized.error });
  }

  const normalizedConfig = normalizeOptimizationConfig(optimizationConfig);
  if (normalizedConfig.error) {
    return reply.code(400).send({ error: normalizedConfig.error });
  }

  let diseaseCatalog;
  try {
    diseaseCatalog = await fetchDiseaseCatalog();
  } catch (error) {
    request.log?.warn?.({ error: error.message }, 'Disease catalog validation failed');
    return reply.code(503).send({
      error: 'Disease catalog unavailable',
      detail: error.message,
    });
  }

  const resolved = resolveDiseasesFromCatalog(normalized.diseases, diseaseCatalog);
  if (resolved.error) {
    return reply.code(400).send({ error: resolved.error, unknownDiseases: resolved.unknown });
  }

  const diseaseIds = resolved.diseases.map((disease) => disease.id);
  const mlResult = await fetchMlResult(diseaseIds, normalizedConfig.optimizationConfig, {
    logger: request.log,
    resolvedDiseases: resolved.diseases,
  });
  const dataStatus = mlResult.metadata.dataStatus;
  const mlStatus = mlResult.metadata.mlStatus;

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
      dataStatus: candidate.dataStatus ?? dataStatus,
      mlStatus: candidate.mlStatus ?? mlStatus,
      optimizationConfig: normalizedConfig.optimizationConfig,
    };
  });

  const searchResult = {
    queryId: mlResult.queryId ?? `query-${Date.now()}`,
    diseases: mlResult.diseases ?? normalized.diseases,
    candidates,
    metadata: {
      ...mlResult.metadata,
      dataStatus,
      mlStatus,
      optimizationConfig: normalizedConfig.optimizationConfig,
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

const isMainModule = process.argv[1]
  && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMainModule) {
  app.listen({ port: PORT, host: HOST }).catch((err) => {
    app.log.error(err);
    process.exit(1);
  });
}
