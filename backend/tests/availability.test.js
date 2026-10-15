import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluateRuleApplicability, resolveRuleIdentity, checkHardContraindications } from '../src/rules/contraindications.js';
import { buildCandidateComparison } from '../src/explainability/types.js';
import { formatMLPredictions } from '../src/explainability/presentation.js';
import { validateCandidateSetResult } from '../src/server.js';

test('canonical mapping is positive, versioned, incomplete and not inferred from names', () => {
  for (const id of ['Compound::DB00945', ' compound::db00945 ', 'DB00945']) {
    assert.deepEqual(resolveRuleIdentity(id).tokens, ['nsaid']);
    const evaluation = evaluateRuleApplicability([id]);
    assert.equal(evaluation.status, 'partially_evaluated');
    assert.equal(evaluation.clinicallyValidated, false);
    assert.match(evaluation.mappingVersion, /2026-10-16/);
  }
  for (const id of ['Compound::DB00177', 'Compound::DB99999', 'aspirin', 'lisinopril']) {
    assert.equal(evaluateRuleApplicability([id]).status, 'not_evaluable');
    assert.deepEqual(resolveRuleIdentity(id).tokens, []);
  }
  assert.deepEqual(checkHardContraindications(['Compound::DB00945', 'warfarin']).pair, ['warfarin', 'nsaid']);
  assert.equal(evaluateRuleApplicability(['maoi', 'ssri']).status, 'evaluated');
});

const pair = { drugPair: ['Compound::DB00177', 'Compound::DB00187'], predictedSeverity: 'Moderate',
  model: { name: 'RandomForestClassifier', version: 'fixture' }, inferenceStatus: 'applied' };
const candidate = { candidateSetId: 'fixture', drugs: [...pair.drugPair, 'Compound::DB00796'], drugCount: 3,
  treatedDiseaseIds: ['d'], uncoveredDiseaseIds: [], coverage: 1, status: 'accepted', rejectionReasons: [],
  evidence: [], dataStatus: 'real_graph', mlStatus: 'partial', mlPrediction: { status: 'partial', pairs: [pair],
    unavailablePairs: pair.drugPair.map(id => ({ drugPair: [id, 'Compound::DB00796'], reasonCode: 'missing_drug_mapping', reason: 'Missing reviewed bridge' })) } };

test('partial predictions survive validation and explanation without invented severity', () => {
  const payload = { diseaseIds: ['d'], diseases: [{ id: 'd', name: 'fixture' }], candidateSets: [candidate], metadata: { dataStatus: 'real_graph', mlStatus: 'applied' } };
  assert.equal(validateCandidateSetResult(payload), payload);
  const explanation = formatMLPredictions(buildCandidateComparison(candidate).mlPrediction);
  assert.equal(explanation.status, 'partial');
  assert.equal(explanation.pairs[0].severity, 'Moderate');
  assert.equal(explanation.unavailablePairs.length, 2);
  assert.ok(explanation.unavailablePairs.every(pair => !Object.hasOwn(pair, 'severity')));
  for (const corrupt of [
    c => { c.mlPrediction.unavailablePairs[0].predictedSeverity = 'Minor'; },
    c => { c.mlPrediction.pairs[0].confidence = .9; },
    c => { c.mlPrediction.unavailablePairs.pop(); },
    c => { c.mlPrediction.pairs[0].drugPair = ['other', 'other']; },
  ]) {
    const copy = structuredClone(payload); corrupt(copy.candidateSets[0]);
    assert.throws(() => validateCandidateSetResult(copy));
  }
});

test('explainability distinguishes single-drug not applicable from unsupported pairs', () => {
  const single = buildCandidateComparison({ ...candidate, drugs: ['Compound::DB00177'], mlStatus: 'not_applied', mlPrediction: { pairs: [], reason: 'No pair to classify' } });
  assert.equal(formatMLPredictions(single.mlPrediction).status, 'not_applicable');
  const unsupported = buildCandidateComparison({ ...candidate, mlStatus: 'not_applied', mlPrediction: { pairs: [], reason: 'Missing mapping' } });
  assert.equal(formatMLPredictions(unsupported.mlPrediction).status, 'not_available');
  assert.equal(unsupported.deterministicRules[0].status, 'not_evaluable');
});
