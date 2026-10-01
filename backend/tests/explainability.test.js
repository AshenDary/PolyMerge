import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  createGraphEvidence,
  createRuleResults,
  createMLPredictions,
  buildCandidateComparison,
  buildExplainabilityPayload,
} from '../src/explainability/types.js';
import {
  buildExplainabilityResponse,
  createEvidencePathVisualization,
} from '../src/explainability/presentation.js';

function graphPath(pathId, semanticType, relationship, targetEntity) {
  return {
    pathId,
    semanticType,
    sourceEntity: {
      id: 'Compound::DB00177',
      name: 'Valsartan',
      kind: 'Compound',
    },
    relationship: {
      type: relationship,
      metaedge: relationship,
    },
    targetEntity,
    provenance: {
      source: 'Hetionet',
      graphVersion: 'Hetionet v1.0 filtered PolyMerge fragment',
      evidenceType: 'known',
    },
  };
}

function candidateSet(overrides = {}) {
  return {
    candidateSetId: 'candidate-set:Compound::DB00177+Compound::DB00331',
    rank: 1,
    drugs: ['Compound::DB00177', 'Compound::DB00331'],
    drugNames: ['Valsartan', 'Metformin'],
    drugCount: 2,
    status: 'accepted',
    treatedDiseaseIds: ['Disease::DOID:10763', 'Disease::DOID:9352'],
    uncoveredDiseaseIds: [],
    coverage: 1,
    rejectionReasons: [],
    dataStatus: 'real_graph',
    mlStatus: 'applied',
    graphEvidence: {
      source: 'Hetionet',
      graphVersion: 'Hetionet v1.0 filtered PolyMerge fragment',
      paths: [
        graphPath('graph-path:treatment', 'treatment', 'CtD', {
          id: 'Disease::DOID:10763',
          name: 'hypertension',
          kind: 'Disease',
        }),
        graphPath('graph-path:gene', 'gene_context', 'CbG', {
          id: 'Gene::ENSG000001',
          name: 'ACE',
          kind: 'Gene',
        }),
        graphPath('graph-path:side-effect', 'side_effect_context', 'CcSE', {
          id: 'Side Effect::C0018681',
          name: 'headache',
          kind: 'Side Effect',
        }),
      ],
    },
    comparison: {
      drugs: [{
        drugId: 'Compound::DB00177',
        drugName: 'Valsartan',
        evidencePathIds: ['graph-path:treatment', 'graph-path:gene', 'graph-path:side-effect'],
      }],
    },
    mlPrediction: {
      status: 'applied',
      pairs: [{
        drugPair: ['Compound::DB00177', 'Compound::DB00331'],
        predictedSeverity: 'Moderate',
        model: {
          name: 'RandomForestClassifier',
          version: 'RandomForestClassifier-sprint5-v1-65e9834666ad19c5',
          artifactSha256: 'a'.repeat(64),
          featureContractSha256: 'b'.repeat(64),
        },
        inferenceStatus: 'applied',
      }],
    },
    ...overrides,
  };
}

describe('Sprint 5 explainability adapters', () => {
  it('consumes CtD treatment paths from graphEvidence.paths', () => {
    const graphEvidence = createGraphEvidence(candidateSet());

    assert.equal(graphEvidence.treatmentPaths.length, 1);
    assert.equal(graphEvidence.treatmentPaths[0].relationship, 'CtD');
    assert.equal(graphEvidence.treatmentPaths[0].pathId, 'graph-path:treatment');
    assert.equal(graphEvidence.treatmentPaths[0].drugId, 'Compound::DB00177');
    assert.equal(graphEvidence.treatmentPaths[0].diseaseId, 'Disease::DOID:10763');
    assert.equal(graphEvidence.provenance.source, 'Hetionet');
  });

  it('separates gene and side-effect context by semanticType', () => {
    const graphEvidence = createGraphEvidence(candidateSet());

    assert.equal(graphEvidence.geneContext.length, 1);
    assert.equal(graphEvidence.geneContext[0].relationship, 'CbG');
    assert.equal(graphEvidence.geneContext[0].geneId, 'Gene::ENSG000001');
    assert.equal(graphEvidence.sideEffectContext.length, 1);
    assert.equal(graphEvidence.sideEffectContext[0].relationship, 'CcSE');
    assert.equal(graphEvidence.sideEffectContext[0].sideEffectId, 'Side Effect::C0018681');
  });

  it('preserves per-drug evidencePathIds', () => {
    const graphEvidence = createGraphEvidence(candidateSet());

    assert.deepEqual(graphEvidence.perDrugPathReferences[0].evidencePathIds, [
      'graph-path:treatment',
      'graph-path:gene',
      'graph-path:side-effect',
    ]);
  });

  it('uses precomputed deterministic rule state without rerunning hard rules', () => {
    const acceptedDespiteNames = candidateSet({
      drugs: ['maoi', 'ssri'],
      status: 'accepted',
      rejectionReasons: [],
      mlStatus: 'not_applied',
      mlPrediction: { status: 'not_applied', pairs: [] },
    });

    const comparison = buildCandidateComparison(acceptedDespiteNames);

    assert.equal(comparison.status, 'accepted');
    assert.equal(comparison.deterministicRules[0].message, 'No configured deterministic hard-rule violation detected');
  });

  it('presents rejected candidate reasons as deterministic rules', () => {
    const rules = createRuleResults(candidateSet({
      status: 'rejected',
      rejectionReasons: [{
        type: 'hard_contraindication',
        message: 'Absolute contraindication: maoi + ssri',
        pair: ['maoi', 'ssri'],
        stage: 'pre_optimization',
      }],
    }));

    assert.equal(rules.length, 1);
    assert.equal(rules[0].status, 'rejected');
    assert.deepEqual(rules[0].affectedDrugs, ['maoi', 'ssri']);
  });

  it('preserves real model prediction fields without fabricating confidence or probabilities', () => {
    const predictions = createMLPredictions(candidateSet());

    assert.equal(predictions.length, 1);
    assert.equal(predictions[0].predictedSeverity, 'Moderate');
    assert.equal(predictions[0].modelVersion, 'RandomForestClassifier-sprint5-v1-65e9834666ad19c5');
    assert.equal(Object.hasOwn(predictions[0], 'confidence'), false);
    assert.equal(Object.hasOwn(predictions[0], 'probabilities'), false);
  });

  it('keeps graph, deterministic rules, and ML prediction channels distinct', () => {
    const comparison = buildCandidateComparison(candidateSet());

    assert.ok(comparison.graphEvidence);
    assert.ok(Array.isArray(comparison.deterministicRules));
    assert.ok(comparison.mlPrediction);
    assert.equal(Object.hasOwn(comparison, 'safetyScore'), false);
    assert.equal(Object.hasOwn(comparison, 'clinicalSafety'), false);
  });

  it('builds detailed, comparison, visualization, and structured responses', () => {
    const detailed = buildExplainabilityResponse('query-1', ['Disease::DOID:10763'], [candidateSet()], 'detailed');
    const comparison = buildExplainabilityResponse('query-1', ['Disease::DOID:10763'], [candidateSet()], 'comparison');
    const visualization = buildExplainabilityResponse('query-1', ['Disease::DOID:10763'], [candidateSet()], 'visualization');
    const structured = buildExplainabilityResponse('query-1', ['Disease::DOID:10763'], [candidateSet()], 'structured');

    assert.equal(detailed.detailedExplanations.length, 1);
    assert.equal(comparison.comparisonView.comparisonTable.rows.length, 1);
    assert.equal(visualization.visualizations[0].evidencePath.edges[0].label, 'CtD');
    assert.equal(structured.candidates[0].candidateSetId, candidateSet().candidateSetId);
  });

  it('visualization includes represented CtD, gene, and side-effect context only', () => {
    const visualization = createEvidencePathVisualization(buildCandidateComparison(candidateSet()));

    assert.ok(visualization.edges.some((edge) => edge.label === 'CtD'));
    assert.ok(visualization.edges.some((edge) => edge.label === 'CbG'));
    assert.ok(visualization.edges.some((edge) => edge.label === 'CcSE'));
    assert.equal(visualization.edges.some((edge) => edge.label === 'CrC'), false);
    assert.equal(visualization.edges.some((edge) => edge.label === 'predicted graph relationships'), false);
  });

  it('payload metadata counts accepted and rejected candidates', () => {
    const payload = buildExplainabilityPayload('query-2', ['Disease::DOID:10763'], [
      candidateSet(),
      candidateSet({
        candidateSetId: 'candidate-set:rejected',
        rank: 2,
        status: 'rejected',
        rejectionReasons: [{ type: 'hard_contraindication', message: 'blocked' }],
        mlStatus: 'not_applied',
        mlPrediction: { status: 'not_applied', pairs: [] },
      }),
    ]);

    assert.equal(payload.metadata.acceptedCount, 1);
    assert.equal(payload.metadata.rejectedCount, 1);
    assert.match(payload.disclaimer, /separate evidence channels/);
  });
});
