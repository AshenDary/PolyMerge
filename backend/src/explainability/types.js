/**
 * Sprint 5 explainability structures.
 *
 * These adapters keep graph evidence, deterministic rules, and ML prediction
 * output separate. They consume already-computed candidate state and never
 * re-run hard safety rules.
 */

function relationshipType(path) {
  return path?.relationship?.type ?? path?.relationship ?? null;
}

function pathProvenance(candidateSet, path) {
  return {
    source: path?.provenance?.source ?? candidateSet.graphEvidence?.source ?? 'Hetionet',
    graphVersion: path?.provenance?.graphVersion ?? candidateSet.graphEvidence?.graphVersion ?? null,
    evidenceType: path?.provenance?.evidenceType ?? 'known',
  };
}

function formatTreatmentPath(candidateSet, path) {
  const provenance = pathProvenance(candidateSet, path);
  return {
    pathId: path.pathId,
    drugId: path.sourceEntity?.id,
    drugName: path.sourceEntity?.name,
    diseaseId: path.targetEntity?.id,
    diseaseName: path.targetEntity?.name,
    relationship: relationshipType(path),
    source: provenance.source,
    graphVersion: provenance.graphVersion,
    evidenceType: provenance.evidenceType,
    rawPath: path,
  };
}

function formatGenePath(candidateSet, path) {
  const provenance = pathProvenance(candidateSet, path);
  return {
    pathId: path.pathId,
    drugId: path.sourceEntity?.id,
    drugName: path.sourceEntity?.name,
    geneId: path.targetEntity?.id,
    geneName: path.targetEntity?.name,
    relationship: relationshipType(path),
    source: provenance.source,
    graphVersion: provenance.graphVersion,
    rawPath: path,
  };
}

function formatSideEffectPath(candidateSet, path) {
  const provenance = pathProvenance(candidateSet, path);
  return {
    pathId: path.pathId,
    drugId: path.sourceEntity?.id,
    drugName: path.sourceEntity?.name,
    sideEffectId: path.targetEntity?.id,
    sideEffectName: path.targetEntity?.name,
    relationship: relationshipType(path),
    source: provenance.source,
    graphVersion: provenance.graphVersion,
    rawPath: path,
  };
}

export function createGraphEvidence(candidateSet) {
  const paths = candidateSet.graphEvidence?.paths ?? [];
  const treatmentPaths = paths
    .filter((path) => path.semanticType === 'treatment')
    .map((path) => formatTreatmentPath(candidateSet, path));
  const geneContext = paths
    .filter((path) => path.semanticType === 'gene_context')
    .map((path) => formatGenePath(candidateSet, path));
  const sideEffectContext = paths
    .filter((path) => path.semanticType === 'side_effect_context')
    .map((path) => formatSideEffectPath(candidateSet, path));

  return {
    treatedDiseaseIds: candidateSet.treatedDiseaseIds ?? [],
    uncoveredDiseaseIds: candidateSet.uncoveredDiseaseIds ?? [],
    coverage: candidateSet.coverage ?? 0,
    coverageDescription: `${Math.round((candidateSet.coverage ?? 0) * 100)}% of requested diseases`,
    treatmentPaths,
    geneContext,
    sideEffectContext,
    perDrugPathReferences: candidateSet.comparison?.drugs?.map((drug) => ({
      drugId: drug.drugId,
      drugName: drug.drugName,
      evidencePathIds: drug.evidencePathIds ?? [],
    })) ?? [],
    provenance: {
      source: candidateSet.graphEvidence?.source ?? 'Hetionet',
      version: candidateSet.graphEvidence?.graphVersion ?? null,
      dataStatus: candidateSet.dataStatus,
    },
  };
}

export function createRuleResults(candidateSet) {
  const rules = (candidateSet.rejectionReasons ?? []).map((reason) => ({
    ruleId: `rule-${reason.type}`,
    type: reason.type,
    status: 'rejected',
    message: reason.message,
    affectedDrugs: reason.pair ?? [],
    source: reason.source ?? 'PolyMerge Safety Rules',
    stage: reason.stage ?? 'backend_validation',
  }));

  if (rules.length === 0 && candidateSet.status === 'accepted') {
    rules.push({
      ruleId: 'rule-accepted',
      type: 'accepted',
      status: 'accepted',
      message: 'No configured deterministic hard-rule violation detected',
      affectedDrugs: [],
      source: 'PolyMerge Safety Rules',
      stage: 'precomputed',
    });
  }

  return rules;
}

/**
 * Preserve only real pairwise model results in the explainability response.
 * An applied model without returned pairwise results remains an empty list.
 */
export function createMLPredictions(candidateSet) {
  const prediction = candidateSet.mlPrediction;
  if (!prediction || prediction.status !== 'applied') {
    return [];
  }

  return (prediction.pairs ?? []).map((pair) => ({
    drugPair: pair.drugPair,
    predictedSeverity: pair.predictedSeverity ?? pair.predictedClass,
    modelName: pair.model?.name ?? null,
    modelVersion: pair.model?.version ?? null,
    artifactSha256: pair.model?.artifactSha256,
    featureContractSha256: pair.model?.featureContractSha256,
    inferenceStatus: pair.inferenceStatus,
  }));
}

export function createPresentationHints(candidateSet) {
  return {
    statusIcon: candidateSet.status === 'accepted' ? 'check-circle' : 'x-circle',
    statusColor: candidateSet.status === 'accepted' ? 'green' : 'red',
    coverageBadge: {
      text: `${Math.round((candidateSet.coverage ?? 0) * 100)}% Coverage`,
      color: candidateSet.coverage >= 0.8 ? 'green' : candidateSet.coverage >= 0.5 ? 'yellow' : 'red',
    },
    disclaimer: 'Research use only. Not clinical guidance.',
  };
}

export function buildCandidateComparison(candidateSet) {
  return {
    candidateSetId: candidateSet.candidateSetId,
    rank: candidateSet.rank,
    drugs: candidateSet.drugs ?? [],
    drugNames: candidateSet.drugNames ?? [],
    drugCount: candidateSet.drugCount ?? candidateSet.drugs?.length ?? 0,
    status: candidateSet.status,
    graphEvidence: createGraphEvidence(candidateSet),
    deterministicRules: createRuleResults(candidateSet),
    mlPrediction: {
      status: candidateSet.mlStatus === 'applied' ? 'applied' : 'not_applied',
      pairs: createMLPredictions(candidateSet),
      reason: candidateSet.mlPrediction?.reason,
    },
    presentation: createPresentationHints(candidateSet),
    dataStatus: candidateSet.dataStatus,
    mlStatus: candidateSet.mlStatus,
  };
}

export function buildExplainabilityPayload(queryId, diseaseIds, candidateSets) {
  const candidates = candidateSets.map((candidateSet) => buildCandidateComparison(candidateSet));
  return {
    queryId,
    diseaseIds,
    candidates,
    metadata: {
      timestamp: new Date().toISOString(),
      candidateCount: candidates.length,
      acceptedCount: candidates.filter((candidate) => candidate.status === 'accepted').length,
      rejectedCount: candidates.filter((candidate) => candidate.status === 'rejected').length,
    },
    disclaimer: 'Research decision-support only. PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. Graph evidence, deterministic rules, and ML predictions are separate evidence channels that must not be combined into a single safety score.',
    limitations: [
      'Graph coverage measures representation in the knowledge graph, not clinical efficacy.',
      'Configured deterministic rules are not a comprehensive clinical interaction database.',
      'ML predictions are statistical estimates from research models, not clinical validation.',
      'All evidence channels require expert review and appropriate clinical/regulatory validation.',
    ],
  };
}
