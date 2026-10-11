import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const frontendDir = path.resolve(process.cwd(), '../frontend');

function loadFrontendLogic() {
  const appSource = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');
  const context = {
    globalThis: {},
    Set,
    Map,
    Number,
    Math,
    String,
    Array,
    Object,
    Date,
    JSON,
    clearTimeout() {},
    setTimeout() {},
  };
  context.globalThis = context;
  vm.runInNewContext(appSource, context);
  return Object.assign(context.PolyMergeFrontend, { context });
}

const candidateResponse = {
  diseaseIds: ['Disease::DOID:10763', 'Disease::DOID:9352'],
  diseases: [
    { id: 'Disease::DOID:10763', name: 'hypertension' },
    { id: 'Disease::DOID:9352', name: 'type 2 diabetes mellitus' },
  ],
  metadata: {
    dataStatus: 'real_graph',
    mlStatus: 'applied',
    optimization: {
      coveredDiseaseIds: ['Disease::DOID:10763', 'Disease::DOID:9352'],
    },
  },
  candidateSets: [
    {
      candidateSetId: 'candidate-set:accepted',
      rank: 1,
      drugs: ['Compound::DB00177'],
      drugNames: ['Valsartan'],
      treatedDiseaseIds: ['Disease::DOID:10763', 'Disease::DOID:9352'],
      uncoveredDiseaseIds: [],
      coverage: 1,
      drugCount: 1,
      status: 'accepted',
      rejectionReasons: [],
      mlStatus: 'not_applied',
      mlPrediction: { status: 'not_applied', pairs: [], reason: 'single-drug candidate' },
      graphEvidence: {
        paths: [
          {
            pathId: 'graph-path:treatment',
            semanticType: 'treatment',
            relationship: { type: 'CtD' },
            sourceEntity: { id: 'Compound::DB00177', name: 'Valsartan', kind: 'Compound' },
            targetEntity: { id: 'Disease::DOID:10763', name: 'hypertension', kind: 'Disease' },
          },
          {
            pathId: 'graph-path:crc',
            semanticType: 'compound_resemblance',
            relationship: { type: 'CrC' },
            sourceEntity: { id: 'Compound::DB00177', name: 'Valsartan', kind: 'Compound' },
            targetEntity: { id: 'Compound::DB002', name: 'Other', kind: 'Compound' },
          },
        ],
      },
    },
    {
      candidateSetId: 'candidate-set:rejected-ml',
      rank: 2,
      drugs: ['Compound::DB00177', 'Compound::DB00331'],
      drugNames: ['Valsartan', 'Metformin'],
      treatedDiseaseIds: ['Disease::DOID:10763', 'Disease::DOID:9352'],
      uncoveredDiseaseIds: [],
      coverage: 1,
      drugCount: 2,
      status: 'rejected',
      rejectionReasons: [{ type: 'hard_contraindication', message: 'Configured blocked pair', pair: ['a', 'b'] }],
      mlStatus: 'applied',
      mlPrediction: {
        status: 'applied',
        pairs: [{
          drugPair: ['Compound::DB00177', 'Compound::DB00331'],
          predictedSeverity: 'Moderate',
          inferenceStatus: 'applied',
          model: { name: 'RandomForestClassifier', version: 'RandomForestClassifier-sprint5-v1-65e9834666ad19c5' },
        }],
      },
      graphEvidence: {
        paths: [
          {
            pathId: 'graph-path:gene',
            semanticType: 'gene_context',
            relationship: { type: 'CbG' },
            sourceEntity: { id: 'Compound::DB00177', name: 'Valsartan', kind: 'Compound' },
            targetEntity: { id: 'Gene::1', name: 'GENE1', kind: 'Gene' },
          },
          {
            pathId: 'graph-path:side-effect',
            semanticType: 'side_effect_context',
            relationship: { type: 'CcSE' },
            sourceEntity: { id: 'Compound::DB00331', name: 'Metformin', kind: 'Compound' },
            targetEntity: { id: 'SideEffect::1', name: 'nausea', kind: 'Side Effect' },
          },
        ],
      },
    },
  ],
};

test('frontend exposes Home, Simulation, Explainability, and Model Analysis navigation', () => {
  const html = readFileSync(path.join(frontendDir, 'index.html'), 'utf8');

  assert.match(html, /href="#home"/);
  assert.match(html, /href="#simulation"/);
  assert.match(html, /href="#explainability-panel"/);
  assert.match(html, /href="#model-analysis"/);
  assert.match(html, /Start Simulation/);
  assert.match(html, /Analysis Pipeline/);
  assert.doesNotMatch(html, /topbar-pills/);
  assert.doesNotMatch(html, /ml-tag/);
  assert.doesNotMatch(html, /Research use only/);
  assert.doesNotMatch(html, /Agent-assisted/);
});

test('frontend uses canonical candidate-set APIs and timeout/error copy', () => {
  const app = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');
  const explainability = readFileSync(path.join(frontendDir, 'explainability.js'), 'utf8');

  assert.match(app, /\/api\/diseases/);
  assert.match(app, /\/api\/candidate-sets\/search/);
  assert.doesNotMatch(app, /\/api\/combinations\/search/);
  assert.match(app, /Request timed out/);
  assert.match(app, /Disease catalog unavailable/);
  assert.match(app, /Candidate search unavailable/);
  assert.match(explainability, /\/api\/candidate-sets\/\$\{encodeURIComponent\(queryId\)\}\/explain/);
});

test('disease filtering returns full catalog after clearing search', () => {
  const logic = loadFrontendLogic();
  const diseases = [
    { id: 'Disease::DOID:10763', name: 'hypertension' },
    { id: 'Disease::DOID:9352', name: 'type 2 diabetes mellitus' },
  ];

  assert.deepEqual(logic.filterDiseases(diseases, 'hyper').map((disease) => disease.id), ['Disease::DOID:10763']);
  assert.deepEqual(logic.filterDiseases(diseases, '').map((disease) => disease.id), [
    'Disease::DOID:10763',
    'Disease::DOID:9352',
  ]);
});

test('workflow summary is derived from real candidate response data', () => {
  const logic = loadFrontendLogic();
  const stages = logic.computeWorkflowStages(candidateResponse, 'candidate-set:rejected-ml');

  assert.equal(stages.find((stage) => stage.key === 'graph').status, 'complete');
  assert.match(stages.find((stage) => stage.key === 'graph').summary, /3 evidence paths/);
  assert.match(stages.find((stage) => stage.key === 'mapping').summary, /2 mapped drugs/);
  assert.match(stages.find((stage) => stage.key === 'rules').summary, /1 passed · 1 rejected/);
  assert.equal(stages.find((stage) => stage.key === 'ml').status, 'partial');
  assert.match(stages.find((stage) => stage.key === 'ml').summary, /1 of 2 candidates/);
  assert.match(stages.find((stage) => stage.key === 'evidence').summary, /2 represented paths · Configured rules: Rejected · Interaction prediction: Moderate/);
  assert.equal(logic.humanStatus('not_applied'), 'Not applied');
  assert.equal(logic.humanStatus('not_applicable'), 'Not applicable');
});

test('single-drug interaction prediction is presented as not applicable', () => {
  const logic = loadFrontendLogic();
  const oneDrug = {
    ...candidateResponse,
    diseaseIds: ['Disease::DOID:10763'],
    diseases: [{ id: 'Disease::DOID:10763', name: 'hypertension' }],
    candidateSets: [candidateResponse.candidateSets[0]],
  };
  const stages = logic.computeWorkflowStages(oneDrug, 'candidate-set:accepted');
  const mlStage = stages.find((stage) => stage.key === 'ml');
  const presentation = logic.candidateMlPresentation(candidateResponse.candidateSets[0]);

  assert.equal(mlStage.status, 'not_applicable');
  assert.match(mlStage.summary, /Single-drug candidate; no drug pair to classify/);
  assert.equal(presentation.label, 'Not applicable');
  assert.match(presentation.detail, /one drug/);
});

test('graph rendering contract allows supported relationships and excludes CrC', () => {
  const logic = loadFrontendLogic();
  const acceptedPaths = logic.graphPaths(candidateResponse.candidateSets[0]);
  const rejectedPaths = logic.graphPaths(candidateResponse.candidateSets[1]);

  assert.deepEqual(acceptedPaths.map((path) => path.relationship.type), ['CtD']);
  assert.deepEqual(rejectedPaths.map((path) => path.relationship.type).sort(), ['CbG', 'CcSE']);
  assert.equal(logic.ALLOWED_GRAPH_RELATIONSHIPS.has('CrC'), false);
});

test('frontend presents mixed ML state without combined safety score', () => {
  const app = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');
  const html = readFileSync(path.join(frontendDir, 'index.html'), 'utf8');
  const logic = loadFrontendLogic();

  assert.deepEqual(JSON.parse(JSON.stringify(logic.mlSummary(candidateResponse.candidateSets))), {
    applied: 1,
    notApplied: 1,
    pairCount: 1,
    total: 2,
  });
  assert.match(app, /\$\{ml\.applied\} of \$\{ml\.total\} candidates include drug-pair predictions/);
  assert.doesNotMatch(app, /getElementById\('ml-tag'\)/);
  assert.doesNotMatch(html, /ml-tag/);
  assert.doesNotMatch(app, /safetyScore/);
  assert.doesNotMatch(app, /combined safety score/i);
});

test('Model Analysis references preserved Sprint 3 EDA assets and fixed metric labels', () => {
  const app = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');

  assert.match(app, /Validation Macro F1/);
  assert.match(app, /0\.506086/);
  assert.match(app, /0\.524630/);
  assert.match(app, /severity_distribution\.svg/);
  assert.match(app, /pair_structure_coverage\.svg/);
  assert.match(app, /hetionet_mapping_coverage\.svg/);
  assert.match(app, /feature_missingness\.svg/);
  assert.match(app, /data-analysis-tab/);
  assert.match(app, /Selected model: Random Forest/);
  assert.doesNotMatch(app, /best hyperparameters/i);
});

test('polished frontend copy avoids raw status and generic AI wording in visible markup', () => {
  const html = readFileSync(path.join(frontendDir, 'index.html'), 'utf8');
  const app = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');

  assert.doesNotMatch(html, /AI-powered|revolutionary|powerful insights|unlock|transform|Agent-assisted/i);
  assert.doesNotMatch(html, />[^<]*not_applied[^<]*</);
  assert.match(app, /humanStatus\(stage\.status\)/);
  assert.match(app, /Interaction Prediction/);
  assert.match(app, /Configured rule check/);
});

function attachDocument(logic) {
  const elements = new Map();
  logic.context.document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, { innerHTML: '', hidden: true, querySelectorAll: () => [] });
      return elements.get(id);
    },
  };
  return elements;
}

test('analysis summary renders response disease names, IDs and actual counts', () => {
  const logic = loadFrontendLogic();
  const elements = attachDocument(logic);
  logic.renderSummary(candidateResponse);
  assert.equal(elements.get('analysis-summary').hidden, false);
  assert.match(elements.get('your-analysis').innerHTML, /hypertension/);
  assert.match(elements.get('your-analysis').innerHTML, /Disease::DOID:9352/);
  assert.deepEqual(JSON.parse(JSON.stringify(logic.analysisMetrics(candidateResponse))).map((metric) => metric[1]), [2, 2, 2, 1, 1, 1]);
  assert.match(elements.get('summary-cards').innerHTML, /Returned candidate sets/);
  assert.match(elements.get('summary-cards').innerHTML, /Pair predictions across results/);
});

test('returned evidence is deduplicated and no live stage completion is invented', () => {
  const logic = loadFrontendLogic();
  const repeated = { ...candidateResponse, candidateSets: [candidateResponse.candidateSets[0], candidateResponse.candidateSets[0]] };
  assert.match(logic.computeWorkflowStages(repeated)[0].summary, /1 evidence path/);
  const running = logic.computeWorkflowStages(null, null, true);
  assert.ok(running.every((stage) => stage.status === 'pending' && stage.summary.includes('after the response')));
  const stages = logic.computeWorkflowStages(candidateResponse);
  assert.match(stages.find((stage) => stage.key === 'ranking').detail, /returned list may be capped/);
  assert.match(stages.find((stage) => stage.key === 'optimization').detail, /Interaction severity does not determine this rank/);
  assert.match(stages.find((stage) => stage.key === 'graph').detail, /Hetionet/);
  assert.match(stages.find((stage) => stage.key === 'mapping').detail, /compound-to-disease/);
});

test('candidate narrative uses real treatment paths and escapes external values', () => {
  const logic = loadFrontendLogic();
  const candidate = { ...candidateResponse.candidateSets[0], drugNames: ['<script>bad</script>'] };
  const narrative = logic.candidateNarrative(candidate, candidateResponse);
  assert.match(narrative, /Why this candidate\?/);
  assert.match(narrative, /Why this rank\?/);
  assert.match(narrative, /Valsartan → hypertension/);
  assert.match(narrative, /&lt;script&gt;bad/);
  assert.doesNotMatch(narrative, /<script>/);
  assert.match(narrative, /Not applicable/);
  assert.equal(logic.candidateMlPresentation(candidateResponse.candidateSets[1]).label, 'Moderate');
  assert.equal(logic.candidateMlPresentation({ drugs: ['a', 'b'], mlStatus: 'applied', mlPrediction: { pairs: [] } }).label, 'Not available');
  assert.equal(logic.candidateMlPresentation({}).label, 'Not available');
});

test('selection refreshes card highlight, evidence summary and candidate explanation locally', () => {
  const logic = loadFrontendLogic();
  const elements = attachDocument(logic);
  logic.state.currentResult = candidateResponse;
  logic.selectCandidate('candidate-set:accepted');
  assert.match(elements.get('explainability').innerHTML, /Why this candidate/);
  assert.match(elements.get('workflow-list').innerHTML, /Interaction prediction: Not applicable/);
  logic.selectCandidate('candidate-set:rejected-ml');
  assert.match(elements.get('workflow-list').innerHTML, /Interaction prediction: Moderate/);
  assert.match(elements.get('explainability').innerHTML, /Configured blocked pair/);
  assert.match(elements.get('explainability').innerHTML, /RandomForestClassifier-sprint5-v1/);
  assert.match(elements.get('results').innerHTML, /data-candidate-id="candidate-set:rejected-ml" aria-pressed="true"/);
});

test('graph legend and secondary technical detail preserve evidence semantics', () => {
  const logic = loadFrontendLogic();
  const graph = logic.renderGraphVisualization(candidateResponse.candidateSets[0]);
  for (const relation of ['CtD', 'CbG', 'CuG', 'CdG', 'CcSE']) assert.ok(graph.includes(relation));
  assert.doesNotMatch(graph, /CrC/);
  const elements = attachDocument(logic);
  logic.renderSelectedCandidate(candidateResponse.candidateSets[0], candidateResponse);
  const html = elements.get('explainability').innerHTML;
  assert.match(html, /<details class="technical-details"><summary>Technical graph details/);
  assert.match(html, /<details class="technical-details"><summary>Candidate metadata/);
  assert.match(html, /How to read this result/);
  assert.doesNotMatch(html, /safety score/i);
});

test('Model Analysis interprets preserved visuals without new evaluation', () => {
  const app = readFileSync(path.join(frontendDir, 'app.js'), 'utf8');
  for (const phrase of ['reviewed structure mapping', 'explicit missingness', 'Macro F1 is the primary metric', 'highest mean validation Macro F1', 'evaluated once after model selection']) assert.ok(app.includes(phrase));
});

test('missing and unavailable evidence does not become a passed rule or applied prediction', () => {
  const logic = loadFrontendLogic();
  const empty = { diseaseIds: ['d'], candidateSets: [] };
  assert.equal(logic.computeWorkflowStages(empty).find((stage) => stage.key === 'rules').status, 'unavailable');
  const partial = { drugs: ['a', 'b'], mlStatus: 'applied', mlPrediction: { pairs: [{ inferenceStatus: 'unavailable', predictedSeverity: null }] } };
  assert.equal(logic.mlSummary([partial]).applied, 0);
  assert.equal(logic.mlSummary([partial]).pairCount, 0);
  assert.equal(logic.candidateMlPresentation(partial).label, 'Not available');
  assert.match(logic.candidateNarrative(partial, empty), /Configured rule check<\/dt><dd>Not available/);
});

test('graph diagram prioritizes treatment paths and escapes node names and metadata', () => {
  const logic = loadFrontendLogic();
  const candidate = { graphEvidence: { paths: [
    ...candidateResponse.candidateSets[1].graphEvidence.paths,
    { ...candidateResponse.candidateSets[0].graphEvidence.paths[0], sourceEntity: { id: 'a', name: '<img src=x onerror=alert(1)>' }, pathId: '\" onmouseover=alert(1)' },
  ] } };
  const html = logic.renderGraphVisualization(candidate);
  assert.ok(html.indexOf('node-disease') < html.indexOf('node-gene'));
  assert.match(html, /&lt;img/);
  assert.match(html, /&quot; onmouseover/);
  assert.doesNotMatch(html, /<img/);
  assert.equal((html.match(/class="evidence-edge"/g) ?? []).length, 3);
});
