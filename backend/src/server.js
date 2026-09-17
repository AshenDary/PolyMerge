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

function createDemoSearchResult(inputDiseases) {
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
      disclaimer: 'Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Results require expert review and appropriate clinical/regulatory validation.',
    },
  };
}

async function fetchMlResult(diseases, optimizationConfig = {}) {
  try {
    const response = await fetch(`${ML_SERVICE_URL}/predict/combination`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases, optimizationConfig }),
    });

    if (!response.ok) {
      throw new Error(`ML engine responded ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return createDemoSearchResult(diseases);
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
  const { diseases = [], optimizationConfig = {} } = request.body ?? {};
  const normalized = normalizeDiseases(diseases);

  if (normalized.error) {
    return reply.code(400).send({ error: normalized.error });
  }

  const mlResult = await fetchMlResult(normalized.diseases, optimizationConfig);

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

app.listen({ port: PORT, host: HOST }).catch((err) => {
  app.log.error(err);
  process.exit(1);
});
