/**
 * Sprint 5 Explainability Types and Structures
 * 
 * Defines structured types for candidate comparison and explainability
 * without mixing predicted severity, graph evidence, or deterministic rules.
 */

/**
 * @typedef {Object} GraphEvidence
 * @property {string[]} treatedDiseaseIds - Disease IDs covered by this candidate
 * @property {string[]} uncoveredDiseaseIds - Disease IDs not covered
 * @property {number} coverage - Fraction of requested diseases covered (0-1)
 * @property {Object[]} treatmentPaths - Graph paths showing treatment relationships
 * @property {Object[]} geneContext - Gene associations from graph
 * @property {Object[]} sideEffectContext - Side effect associations from graph
 * @property {Object} provenance - Source and version information
 */

/**
 * @typedef {Object} TreatmentPath
 * @property {string} drugId - Drug identifier
 * @property {string} diseaseId - Disease identifier  
 * @property {string} relationship - Relationship type (e.g., "CpD", "CtD")
 * @property {string} source - Evidence source (e.g., "Hetionet")
 * @property {string} evidenceType - Type of evidence ("known", "inferred")
 */

/**
 * @typedef {Object} DeterministicRule
 * @property {string} ruleId - Unique rule identifier
 * @property {string} type - Rule type (e.g., "hard_contraindication", "dosage_conflict")
 * @property {string} status - "accepted" or "rejected"
 * @property {string} message - Human-readable rule explanation
 * @property {string[]} affectedDrugs - Drug IDs involved in rule
 * @property {string} source - Rule source (e.g., "PolyMerge Safety Rules")
 * @property {string} stage - When rule was applied (e.g., "backend_validation")
 */

/**
 * @typedef {Object} MLPrediction
 * @property {string} predictedSeverity - Predicted DDI severity ("Major", "Moderate", "Minor")
 * @property {Object} severityProbabilities - Class probabilities
 * @property {number} confidence - Model confidence (0-1)
 * @property {string} modelName - Model identifier (e.g., "RandomForestClassifier")
 * @property {string} modelVersion - Model version string
 * @property {string} datasetVersion - Training dataset version
 * @property {string} predictionTimestamp - ISO timestamp of prediction
 * @property {string} mlStatus - "applied", "not_applied", "unavailable"
 * @property {Object} metadata - Additional prediction metadata
 */

/**
 * @typedef {Object} CandidateComparison
 * @property {string} candidateSetId - Unique candidate identifier
 * @property {number} rank - Ranking position (1-indexed)
 * @property {string[]} drugs - Drug IDs in this candidate
 * @property {number} drugCount - Number of drugs
 * @property {string} status - "accepted" or "rejected"
 * @property {GraphEvidence} graphEvidence - Graph-derived evidence
 * @property {DeterministicRule[]} rules - Deterministic rule results
 * @property {MLPrediction[]} predictions - ML predictions (one per pair)
 * @property {Object} presentation - UI presentation hints
 */

/**
 * @typedef {Object} ExplainabilityPayload
 * @property {string} queryId - Query identifier
 * @property {string[]} diseaseIds - Requested disease IDs
 * @property {CandidateComparison[]} candidates - Candidate comparisons
 * @property {Object} metadata - Query metadata
 * @property {string} disclaimer - Research use disclaimer
 */

/**
 * Create a structured graph evidence object
 */
export function createGraphEvidence(candidateSet) {
  return {
    treatedDiseaseIds: candidateSet.treatedDiseaseIds ?? [],
    uncoveredDiseaseIds: candidateSet.uncoveredDiseaseIds ?? [],
    coverage: candidateSet.coverage ?? 0,
    coverageDescription: `${Math.round((candidateSet.coverage ?? 0) * 100)}% of requested diseases`,
    treatmentPaths: candidateSet.evidence
      ?.filter((e) => e.relationship === 'treats')
      .map((e) => ({
        drugId: e.drugId,
        diseaseId: e.diseaseId,
        relationship: e.relationship,
        source: e.source ?? 'Hetionet',
        evidenceType: e.evidenceType ?? 'known',
        metapath: e.metapath,
      })) ?? [],
    geneContext: candidateSet.evidence
      ?.filter((e) => e.entityType === 'gene')
      .map((e) => ({
        drugId: e.drugId,
        geneId: e.geneId,
        relationship: e.relationship,
        source: e.source ?? 'Hetionet',
      })) ?? [],
    sideEffectContext: candidateSet.evidence
      ?.filter((e) => e.entityType === 'side_effect')
      .map((e) => ({
        drugId: e.drugId,
        sideEffectId: e.sideEffectId,
        relationship: e.relationship,
        source: e.source ?? 'Hetionet',
      })) ?? [],
    provenance: {
      source: candidateSet.graphSource ?? 'Hetionet',
      version: candidateSet.graphVersion ?? 'v1.0',
      dataStatus: candidateSet.dataStatus,
      timestamp: candidateSet.timestamp ?? new Date().toISOString(),
    },
  };
}

/**
 * Create structured deterministic rule results
 */
export function createRuleResults(candidateSet, additionalViolation = null) {
  const rules = [];
  
  // Add backend-detected violations
  if (additionalViolation) {
    rules.push({
      ruleId: `rule-${additionalViolation.type}`,
      type: additionalViolation.type,
      status: 'rejected',
      message: additionalViolation.message,
      affectedDrugs: additionalViolation.pair ?? [],
      source: 'PolyMerge Safety Rules',
      stage: additionalViolation.stage ?? 'backend_validation',
    });
  }
  
  // Add ML-engine rejection reasons as structured rules
  for (const reason of candidateSet.rejectionReasons ?? []) {
    if (!rules.some((r) => r.type === reason.type)) {
      rules.push({
        ruleId: `rule-${reason.type}`,
        type: reason.type,
        status: 'rejected',
        message: reason.message,
        affectedDrugs: reason.pair ?? [],
        source: reason.source ?? 'ML Engine Rules',
        stage: reason.stage ?? 'ml_engine_validation',
      });
    }
  }
  
  // If no rejections, add acceptance marker
  if (rules.length === 0 && candidateSet.status === 'accepted') {
    rules.push({
      ruleId: 'rule-accepted',
      type: 'accepted',
      status: 'accepted',
      message: 'No contraindications detected',
      affectedDrugs: [],
      source: 'PolyMerge Safety Rules',
      stage: 'backend_validation',
    });
  }
  
  return rules;
}

/**
 * Create ML prediction structure (placeholder for Ranee's API)
 */
export function createMLPredictions(candidateSet) {
  const predictions = [];
  
  // Check if ML predictions are available
  if (candidateSet.mlStatus === 'not_applied' || candidateSet.mlStatus === 'unavailable') {
    return predictions;
  }
  
  // Placeholder: In Sprint 5, Ranee will provide actual predictions
  // For now, document the expected structure
  if (candidateSet.interactionRisk != null || candidateSet.predictions) {
    const drugs = candidateSet.drugs ?? [];
    
    // Generate pair-wise predictions for all drug pairs
    for (let i = 0; i < drugs.length; i++) {
      for (let j = i + 1; j < drugs.length; j++) {
        predictions.push({
          drugPair: [drugs[i], drugs[j]],
          predictedSeverity: null, // Will be filled by Ranee's API
          severityProbabilities: {
            Major: null,
            Moderate: null,
            Minor: null,
          },
          confidence: null,
          modelName: candidateSet.modelName ?? null,
          modelVersion: candidateSet.modelVersion ?? null,
          datasetVersion: candidateSet.datasetVersion ?? null,
          predictionTimestamp: candidateSet.timestamp ?? new Date().toISOString(),
          mlStatus: candidateSet.mlStatus,
          metadata: {
            note: 'ML predictions depend on Ranee API integration (Issue #42)',
          },
        });
      }
    }
  }
  
  return predictions;
}

/**
 * Create presentation hints for UI rendering
 */
export function createPresentationHints(candidateSet) {
  return {
    visualSeparation: {
      graphSection: 'Graph Evidence',
      rulesSection: 'Safety Rules',
      mlSection: 'ML Predictions',
      note: 'These sections must be visually distinct in UI',
    },
    statusIcon: candidateSet.status === 'accepted' ? 'check-circle' : 'x-circle',
    statusColor: candidateSet.status === 'accepted' ? 'green' : 'red',
    coverageBadge: {
      text: `${Math.round((candidateSet.coverage ?? 0) * 100)}% Coverage`,
      color: candidateSet.coverage >= 0.8 ? 'green' : candidateSet.coverage >= 0.5 ? 'yellow' : 'red',
    },
    warningLevel: candidateSet.status === 'rejected' ? 'high' : 'none',
    disclaimer: 'Research use only. Not clinical guidance.',
  };
}

/**
 * Build complete candidate comparison structure
 */
export function buildCandidateComparison(candidateSet, additionalViolation = null) {
  return {
    candidateSetId: candidateSet.candidateSetId,
    rank: candidateSet.rank,
    drugs: candidateSet.drugs ?? [],
    drugCount: candidateSet.drugCount ?? candidateSet.drugs?.length ?? 0,
    status: additionalViolation ? 'rejected' : candidateSet.status,
    
    // Separate evidence channels
    graphEvidence: createGraphEvidence(candidateSet),
    rules: createRuleResults(candidateSet, additionalViolation),
    predictions: createMLPredictions(candidateSet),
    
    // Presentation hints
    presentation: createPresentationHints(candidateSet),
    
    // Metadata
    dataStatus: candidateSet.dataStatus,
    mlStatus: candidateSet.mlStatus,
  };
}

/**
 * Build complete explainability payload
 */
export function buildExplainabilityPayload(queryId, diseaseIds, candidateSets) {
  return {
    queryId,
    diseaseIds,
    candidates: candidateSets.map((cs, index) => {
      // Re-check hard contraindications at explainability stage
      const { checkHardContraindications } = require('../rules/contraindications.js');
      const violation = checkHardContraindications(cs.drugs ?? []);
      return buildCandidateComparison(cs, violation);
    }),
    metadata: {
      timestamp: new Date().toISOString(),
      candidateCount: candidateSets.length,
      acceptedCount: candidateSets.filter((cs) => cs.status === 'accepted').length,
      rejectedCount: candidateSets.filter((cs) => cs.status === 'rejected').length,
    },
    disclaimer: 'Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Graph evidence, deterministic rules, and ML predictions are separate evidence channels that must not be combined into a single "safety score".',
    limitations: [
      'Graph coverage measures representation in knowledge graph, not clinical efficacy',
      'Deterministic rules are hard-coded safety checks, not comprehensive drug interaction databases',
      'ML predictions are statistical estimates from research models, not clinical validation',
      'All evidence channels require expert review and appropriate clinical/regulatory validation',
    ],
  };
}
