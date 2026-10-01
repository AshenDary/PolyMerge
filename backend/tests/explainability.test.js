/**
 * Sprint 5 Explainability Integration Tests
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  createGraphEvidence,
  createRuleResults,
  createMLPredictions,
  buildCandidateComparison,
  buildExplainabilityPayload,
} from '../src/explainability/types.js';

describe('Explainability Types', () => {
  describe('createGraphEvidence', () => {
    it('should create structured graph evidence from candidate set', () => {
      const candidateSet = {
        treatedDiseaseIds: ['hypertension', 'type-2-diabetes'],
        uncoveredDiseaseIds: [],
        coverage: 1.0,
        evidence: [
          {
            drugId: 'lisinopril',
            diseaseId: 'hypertension',
            relationship: 'treats',
            source: 'Hetionet',
            evidenceType: 'known',
          },
        ],
        dataStatus: 'real_graph',
      };
      
      const graphEvidence = createGraphEvidence(candidateSet);
      
      assert.equal(graphEvidence.coverage, 1.0);
      assert.equal(graphEvidence.coverageDescription, '100% of requested diseases');
      assert.equal(graphEvidence.treatedDiseaseIds.length, 2);
      assert.equal(graphEvidence.treatmentPaths.length, 1);
      assert.equal(graphEvidence.provenance.dataStatus, 'real_graph');
    });
    
    it('should handle missing evidence gracefully', () => {
      const candidateSet = {
        treatedDiseaseIds: [],
        uncoveredDiseaseIds: ['disease1'],
        coverage: 0,
      };
      
      const graphEvidence = createGraphEvidence(candidateSet);
      
      assert.equal(graphEvidence.coverage, 0);
      assert.equal(graphEvidence.treatmentPaths.length, 0);
      assert.equal(graphEvidence.geneContext.length, 0);
      assert.equal(graphEvidence.sideEffectContext.length, 0);
    });
  });
  
  describe('createRuleResults', () => {
    it('should create acceptance rule when no violations', () => {
      const candidateSet = {
        status: 'accepted',
        rejectionReasons: [],
      };
      
      const rules = createRuleResults(candidateSet);
      
      assert.equal(rules.length, 1);
      assert.equal(rules[0].type, 'accepted');
      assert.equal(rules[0].status, 'accepted');
      assert.equal(rules[0].message, 'No contraindications detected');
    });
    
    it('should include backend violation as rule', () => {
      const candidateSet = {
        status: 'accepted',
        rejectionReasons: [],
      };
      
      const violation = {
        type: 'hard_contraindication',
        message: 'MAOI + SSRI interaction',
        pair: ['maoi', 'ssri'],
        stage: 'backend_validation',
      };
      
      const rules = createRuleResults(candidateSet, violation);
      
      assert.equal(rules.length, 1);
      assert.equal(rules[0].type, 'hard_contraindication');
      assert.equal(rules[0].status, 'rejected');
      assert.equal(rules[0].affectedDrugs.length, 2);
    });
    
    it('should include ML engine rejection reasons', () => {
      const candidateSet = {
        status: 'rejected',
        rejectionReasons: [
          {
            type: 'insufficient_coverage',
            message: 'Coverage below threshold',
            source: 'ML Engine Rules',
          },
        ],
      };
      
      const rules = createRuleResults(candidateSet);
      
      assert.equal(rules.length, 1);
      assert.equal(rules[0].type, 'insufficient_coverage');
      assert.equal(rules[0].source, 'ML Engine Rules');
    });
  });
  
  describe('createMLPredictions', () => {
    it('should return empty array when ML not applied', () => {
      const candidateSet = {
        drugs: ['drug1', 'drug2'],
        mlStatus: 'not_applied',
      };
      
      const predictions = createMLPredictions(candidateSet);
      
      assert.equal(predictions.length, 0);
    });
    
    it('should create prediction placeholders for all drug pairs', () => {
      const candidateSet = {
        drugs: ['drug1', 'drug2', 'drug3'],
        mlStatus: 'applied',
        interactionRisk: 0.5,
      };
      
      const predictions = createMLPredictions(candidateSet);
      
      // 3 drugs = 3 pairs: (1,2), (1,3), (2,3)
      assert.equal(predictions.length, 3);
      assert.deepEqual(predictions[0].drugPair, ['drug1', 'drug2']);
      assert.equal(predictions[0].mlStatus, 'applied');
    });
  });
  
  describe('buildCandidateComparison', () => {
    it('should build complete comparison structure with all channels', () => {
      const candidateSet = {
        candidateSetId: 'candidate-001',
        rank: 1,
        drugs: ['drug1', 'drug2'],
        drugCount: 2,
        status: 'accepted',
        treatedDiseaseIds: ['disease1'],
        uncoveredDiseaseIds: [],
        coverage: 1.0,
        evidence: [],
        rejectionReasons: [],
        dataStatus: 'real_graph',
        mlStatus: 'applied',
      };
      
      const comparison = buildCandidateComparison(candidateSet);
      
      assert.equal(comparison.candidateSetId, 'candidate-001');
      assert.equal(comparison.rank, 1);
      assert.equal(comparison.status, 'accepted');
      
      // Check separate channels exist
      assert.ok(comparison.graphEvidence);
      assert.ok(Array.isArray(comparison.rules));
      assert.ok(Array.isArray(comparison.predictions));
      assert.ok(comparison.presentation);
      
      // Verify channel separation
      assert.notEqual(comparison.graphEvidence, comparison.rules);
      assert.notEqual(comparison.rules, comparison.predictions);
    });
    
    it('should override status when additional violation provided', () => {
      const candidateSet = {
        candidateSetId: 'candidate-002',
        rank: 2,
        drugs: ['drug1', 'drug2'],
        status: 'accepted',
        treatedDiseaseIds: [],
        uncoveredDiseaseIds: [],
        coverage: 0,
        rejectionReasons: [],
        dataStatus: 'real_graph',
        mlStatus: 'not_applied',
      };
      
      const violation = {
        type: 'hard_contraindication',
        message: 'Test violation',
        pair: ['drug1', 'drug2'],
      };
      
      const comparison = buildCandidateComparison(candidateSet, violation);
      
      assert.equal(comparison.status, 'rejected');
      assert.equal(comparison.rules.length, 1);
      assert.equal(comparison.rules[0].type, 'hard_contraindication');
    });
  });
  
  describe('buildExplainabilityPayload', () => {
    it('should build complete payload with metadata', () => {
      const queryId = 'query-123';
      const diseaseIds = ['disease1', 'disease2'];
      const candidateSets = [
        {
          candidateSetId: 'candidate-001',
          rank: 1,
          drugs: ['drug1', 'drug2'],
          status: 'accepted',
          treatedDiseaseIds: ['disease1', 'disease2'],
          uncoveredDiseaseIds: [],
          coverage: 1.0,
          evidence: [],
          rejectionReasons: [],
          dataStatus: 'real_graph',
          mlStatus: 'applied',
        },
        {
          candidateSetId: 'candidate-002',
          rank: 2,
          drugs: ['drug3', 'drug4'],
          status: 'rejected',
          treatedDiseaseIds: ['disease1'],
          uncoveredDiseaseIds: ['disease2'],
          coverage: 0.5,
          evidence: [],
          rejectionReasons: [
            {
              type: 'hard_contraindication',
              message: 'Test rejection',
            },
          ],
          dataStatus: 'real_graph',
          mlStatus: 'not_applied',
        },
      ];
      
      const payload = buildExplainabilityPayload(queryId, diseaseIds, candidateSets);
      
      assert.equal(payload.queryId, 'query-123');
      assert.deepEqual(payload.diseaseIds, diseaseIds);
      assert.equal(payload.candidates.length, 2);
      
      // Check metadata
      assert.equal(payload.metadata.candidateCount, 2);
      assert.equal(payload.metadata.acceptedCount, 1);
      assert.equal(payload.metadata.rejectedCount, 1);
      
      // Check disclaimer and limitations
      assert.ok(payload.disclaimer);
      assert.ok(Array.isArray(payload.limitations));
      assert.ok(payload.limitations.length > 0);
      
      // Verify no mixing message is present
      assert.ok(payload.disclaimer.includes('separate evidence channels'));
    });
  });
  
  describe('Channel Separation', () => {
    it('should keep graph evidence, rules, and predictions structurally distinct', () => {
      const candidateSet = {
        candidateSetId: 'test',
        rank: 1,
        drugs: ['drug1', 'drug2'],
        treatedDiseaseIds: ['disease1'],
        uncoveredDiseaseIds: [],
        coverage: 1.0,
        evidence: [
          {
            drugId: 'drug1',
            diseaseId: 'disease1',
            relationship: 'treats',
          },
        ],
        rejectionReasons: [],
        status: 'accepted',
        dataStatus: 'real_graph',
        mlStatus: 'applied',
        interactionRisk: 0.3,
      };
      
      const comparison = buildCandidateComparison(candidateSet);
      
      // Verify keys are distinct
      const graphKeys = Object.keys(comparison.graphEvidence);
      const ruleKeys = comparison.rules[0] ? Object.keys(comparison.rules[0]) : [];
      const predKeys = comparison.predictions[0] ? Object.keys(comparison.predictions[0]) : [];
      
      // No overlap between channel keys
      const graphSet = new Set(graphKeys);
      const ruleSet = new Set(ruleKeys);
      const predSet = new Set(predKeys);
      
      // Verify no shared keys (except possibly timestamp)
      const graphRuleOverlap = [...graphSet].filter((k) => ruleSet.has(k) && k !== 'timestamp');
      const graphPredOverlap = [...graphSet].filter((k) => predSet.has(k) && k !== 'timestamp');
      const rulePredOverlap = [...ruleSet].filter((k) => predSet.has(k) && k !== 'timestamp');
      
      assert.equal(graphRuleOverlap.length, 0, 'Graph and rules should not share keys');
      assert.equal(graphPredOverlap.length, 0, 'Graph and predictions should not share keys');
      assert.equal(rulePredOverlap.length, 0, 'Rules and predictions should not share keys');
    });
  });
});
