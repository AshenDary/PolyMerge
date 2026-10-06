/**
 * Sprint 5 Explainability Presentation Layer
 * 
 * Formats candidate comparisons and evidence for frontend consumption
 * while maintaining clear separation between evidence channels.
 */

import { buildCandidateComparison, buildExplainabilityPayload } from './types.js';

/**
 * Format graph evidence for human-readable display
 */
export function formatGraphEvidence(graphEvidence) {
  return {
    summary: {
      coverage: `${Math.round(graphEvidence.coverage * 100)}% of requested diseases`,
      treatedCount: graphEvidence.treatedDiseaseIds.length,
      uncoveredCount: graphEvidence.uncoveredDiseaseIds.length,
    },
    treatmentPaths: graphEvidence.treatmentPaths.map((path) => ({
      description: `${path.drugName ?? path.drugId} ${path.relationship} ${path.diseaseName ?? path.diseaseId}`,
      pathId: path.pathId,
      drugId: path.drugId,
      diseaseId: path.diseaseId,
      relationship: path.relationship,
      evidenceType: path.evidenceType,
      source: path.source,
      graphVersion: path.graphVersion,
    })),
    context: {
      genes: graphEvidence.geneContext,
      sideEffects: graphEvidence.sideEffectContext,
      geneCount: graphEvidence.geneContext.length,
      sideEffectCount: graphEvidence.sideEffectContext.length,
      perDrugPathReferences: graphEvidence.perDrugPathReferences,
    },
    provenance: {
      source: graphEvidence.provenance.source,
      version: graphEvidence.provenance.version,
      status: graphEvidence.provenance.dataStatus,
    },
  };
}

/**
 * Format deterministic rules for display
 */
export function formatRules(rules) {
  return rules.map((rule) => ({
    type: rule.type,
    status: rule.status,
    message: rule.message,
    affectedDrugs: rule.affectedDrugs,
    source: rule.source,
    visualStyle: rule.status === 'rejected' ? 'error' : 'success',
  }));
}

/**
 * Format ML predictions for display
 */
export function formatMLPredictions(predictions) {
  if (!predictions || predictions.status !== 'applied' || predictions.pairs.length === 0) {
    return {
      status: 'not_available',
      message: predictions?.reason ?? 'ML predictions are unavailable for this candidate.',
      pairs: [],
    };
  }
  
  return {
    status: 'available',
    pairs: predictions.pairs.map((pred) => ({
      drugs: pred.drugPair,
      severity: pred.predictedSeverity,
      model: {
        name: pred.modelName,
        version: pred.modelVersion,
      },
      inferenceStatus: pred.inferenceStatus,
      visualStyle: pred.predictedSeverity === 'Major' ? 'warning' 
        : pred.predictedSeverity === 'Moderate' ? 'caution' 
        : 'info',
    })),
  };
}

/**
 * Create comparison view for multiple candidates
 */
export function createComparisonView(candidates) {
  return {
    comparisonTable: {
      headers: ['Rank', 'Drugs', 'Coverage', 'Status', 'Rules', 'ML Status'],
      rows: candidates.map((candidate) => ({
        rank: candidate.rank,
        drugs: candidate.drugs.join(', '),
        coverage: `${Math.round((candidate.graphEvidence?.coverage ?? 0) * 100)}%`,
        status: candidate.status,
        rulesStatus: candidate.deterministicRules.some((r) => r.status === 'rejected') ? 'Rejected' : 'Accepted',
        mlStatus: candidate.mlStatus,
        visualStyle: candidate.status === 'accepted' ? 'success' : 'error',
      })),
    },
    sortOptions: ['rank', 'coverage', 'status'],
    filterOptions: {
      status: ['accepted', 'rejected'],
      minCoverage: [0, 0.5, 0.8, 1.0],
    },
  };
}

/**
 * Create detailed explainability view for a single candidate
 */
export function createDetailedExplanation(candidate) {
  return {
    candidateId: candidate.candidateSetId,
    rank: candidate.rank,
    drugs: candidate.drugs,
    status: candidate.status,
    
    sections: [
      {
        title: 'Graph Evidence',
        type: 'graph',
        icon: 'database',
        color: 'blue',
        content: formatGraphEvidence(candidate.graphEvidence),
        disclaimer: 'Based on knowledge graph relationships. Coverage measures representation, not clinical efficacy.',
      },
      {
        title: 'Safety Rules',
        type: 'rules',
        icon: 'shield',
        color: candidate.status === 'rejected' ? 'red' : 'green',
        content: formatRules(candidate.deterministicRules),
        disclaimer: 'Configured deterministic safety checks. Not a comprehensive drug interaction database.',
      },
      {
        title: 'ML Predictions',
        type: 'predictions',
        icon: 'cpu',
        color: 'purple',
        content: formatMLPredictions(candidate.mlPrediction),
        disclaimer: 'Statistical estimates from research models. Not clinical validation.',
      },
    ],
    
    presentation: candidate.presentation,
    
    overallDisclaimer: 'Research decision-support only. All evidence channels require expert review.',
  };
}

/**
 * Create rejection explanation
 */
export function createRejectionExplanation(candidate) {
  const rejectionRules = candidate.deterministicRules.filter((r) => r.status === 'rejected');
  
  return {
    candidateId: candidate.candidateSetId,
    rank: candidate.rank,
    drugs: candidate.drugs,
    status: 'rejected',
    
    rejectionSummary: {
      reason: rejectionRules.length > 0 
        ? 'Deterministic rule violation' 
        : 'Unknown rejection reason',
      ruleCount: rejectionRules.length,
    },
    
    details: rejectionRules.map((rule) => ({
      ruleType: rule.type,
      message: rule.message,
      affectedDrugs: rule.affectedDrugs,
      source: rule.source,
      canOverride: false,
      explanation: 'This is a hard contraindication and cannot be overridden without clinical review.',
    })),
    
    alternatives: {
      message: 'Consider accepted candidates or modify disease selection.',
      showAcceptedCandidates: true,
    },
    
    disclaimer: 'Rejection is based on deterministic rules, not ML predictions. Graph evidence is still available for research purposes.',
  };
}

/**
 * Create evidence path visualization data
 */
export function createEvidencePathVisualization(candidate) {
  const nodes = [];
  const edges = [];
  const nodeIds = new Set();
  
  // Add drug nodes
  for (const drugId of candidate.drugs) {
    if (!nodeIds.has(drugId)) {
      nodes.push({
        id: drugId,
        label: drugId,
        type: 'drug',
        color: '#4CAF50',
      });
      nodeIds.add(drugId);
    }
  }
  
  // Add disease nodes and treatment edges
  for (const path of candidate.graphEvidence.treatmentPaths) {
    if (!nodeIds.has(path.diseaseId)) {
      nodes.push({
        id: path.diseaseId,
        label: path.diseaseId,
        type: 'disease',
        color: '#2196F3',
      });
      nodeIds.add(path.diseaseId);
    }
    
    edges.push({
      source: path.drugId,
      target: path.diseaseId,
      label: path.relationship,
      type: path.evidenceType,
      color: path.evidenceType === 'known' ? '#4CAF50' : '#FF9800',
      style: path.evidenceType === 'known' ? 'solid' : 'dashed',
    });
  }
  
  // Add gene context nodes
  for (const gene of candidate.graphEvidence.geneContext.slice(0, 10)) {
    if (!nodeIds.has(gene.geneId)) {
      nodes.push({
        id: gene.geneId,
        label: gene.geneId,
        type: 'gene',
        color: '#9C27B0',
      });
      nodeIds.add(gene.geneId);
    }
    
    edges.push({
      source: gene.drugId,
      target: gene.geneId,
      label: gene.relationship,
      type: 'context',
      color: '#9C27B0',
      style: 'dotted',
    });
  }

  for (const sideEffect of candidate.graphEvidence.sideEffectContext.slice(0, 10)) {
    if (!nodeIds.has(sideEffect.sideEffectId)) {
      nodes.push({
        id: sideEffect.sideEffectId,
        label: sideEffect.sideEffectName ?? sideEffect.sideEffectId,
        type: 'side_effect',
        color: '#FF9800',
      });
      nodeIds.add(sideEffect.sideEffectId);
    }

    edges.push({
      source: sideEffect.drugId,
      target: sideEffect.sideEffectId,
      label: sideEffect.relationship,
      type: 'context',
      color: '#FF9800',
      style: 'dotted',
    });
  }
  
  return {
    nodes,
    edges,
    layout: 'force-directed',
    legend: [
      { label: 'Drug', color: '#4CAF50', shape: 'circle' },
      { label: 'Disease', color: '#2196F3', shape: 'circle' },
      { label: 'Gene', color: '#9C27B0', shape: 'circle' },
      { label: 'Side Effect', color: '#FF9800', shape: 'circle' },
      { label: 'Known Evidence', style: 'solid' },
      { label: 'Inferred Evidence', style: 'dashed' },
      { label: 'Context', style: 'dotted' },
    ],
    disclaimer: 'Visualization shows graph relationships only. Not a clinical decision tree.',
  };
}

/**
 * Main function to build complete explainability response
 */
export function buildExplainabilityResponse(queryId, diseaseIds, candidateSets, format = 'detailed') {
  const payload = buildExplainabilityPayload(queryId, diseaseIds, candidateSets);
  
  if (format === 'comparison') {
    return {
      ...payload,
      comparisonView: createComparisonView(payload.candidates),
    };
  }
  
  if (format === 'detailed') {
    return {
      ...payload,
      detailedExplanations: payload.candidates.map((candidate) => 
        createDetailedExplanation(candidate)
      ),
    };
  }
  
  if (format === 'visualization') {
    return {
      ...payload,
      visualizations: payload.candidates.map((candidate) => ({
        candidateId: candidate.candidateSetId,
        rank: candidate.rank,
        evidencePath: createEvidencePathVisualization(candidate),
      })),
    };
  }
  
  // Default: return structured payload
  return payload;
}
