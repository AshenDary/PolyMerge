const WORKFLOW_STAGES = [
  ['graph', 'Knowledge graph retrieval', 'Disease evidence lookup'],
  ['mapping', 'Drug mapping', 'Drugs linked to selected diseases'],
  ['ranking', 'Candidate generation and ranking', 'Candidate sets ordered for review'],
  ['rules', 'Deterministic rules', 'Configured rule check'],
  ['optimization', 'Coverage optimization', 'Graph coverage summary'],
  ['ml', 'Interaction prediction', 'Drug-pair severity prediction'],
  ['evidence', 'Selected candidate evidence', 'Candidate evidence ready for inspection'],
];
const ALLOWED_GRAPH_RELATIONSHIPS = new Set(['CtD', 'CbG', 'CuG', 'CdG', 'CcSE']);
const DEFAULT_CATALOG_TIMEOUT_MS = 10000;
const DEFAULT_CANDIDATE_TIMEOUT_MS = 150000;

const state = {
  selectedDiseases: new Set(),
  availableDiseases: [],
  currentResult: null,
  selectedCandidateId: null,
  analysisStartedAt: null,
  elapsedTimer: null,
  comparisonLoaded: false,
  modelAnalysisData: null,
  modelAnalysisTab: 'overview',
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function percent(value) {
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : 'Not provided';
}

function relationshipType(path) {
  return path?.relationship?.type ?? path?.relationship ?? '';
}

function candidateLabel(candidate) {
  return (candidate?.drugNames?.length ? candidate.drugNames : candidate?.drugs ?? []).join(' + ') || 'Candidate set';
}

function diseaseLabelMap(data) {
  return new Map((data?.diseases ?? []).map((disease) => [disease.id, disease.name]));
}

function selectedDiseaseObjects() {
  const byId = new Map(state.availableDiseases.map((disease) => [disease.id, disease]));
  return Array.from(state.selectedDiseases).map((id) => byId.get(id) ?? { id, name: id });
}

function withTimeout(ms) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => clearTimeout(timeout) };
}

async function readJsonResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;
  const message = data.error ?? data.detail ?? 'The request could not be completed.';
  throw new Error(`${response.status}: ${message}`);
}

async function fetchJson(url, options = {}, timeoutMs = DEFAULT_CATALOG_TIMEOUT_MS) {
  const timeout = withTimeout(timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: timeout.signal });
    return await readJsonResponse(response);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)} seconds`);
    }
    throw error;
  } finally {
    timeout.clear();
  }
}

function filterDiseases(diseases, query) {
  const normalized = String(query ?? '').trim().toLowerCase();
  if (!normalized) return diseases;
  return diseases.filter((disease) => `${disease.name} ${disease.id}`.toLowerCase().includes(normalized));
}

function graphPaths(candidate) {
  return (candidate?.graphEvidence?.paths ?? []).filter((path) => ALLOWED_GRAPH_RELATIONSHIPS.has(relationshipType(path)));
}

function allGraphPaths(candidates) {
  return [...new Map(candidates.flatMap((candidate) => graphPaths(candidate)).map((path) => [
    path.pathId ?? JSON.stringify([path.sourceEntity?.id, relationshipType(path), path.targetEntity?.id]), path,
  ])).values()];
}

function mlSummary(candidates) {
  const applied = candidates.filter((candidate) => appliedPairs(candidate).length > 0).length;
  const notApplied = candidates.length - applied;
  const pairCount = candidates.reduce((total, candidate) => total + appliedPairs(candidate).length, 0);
  return { applied, notApplied, pairCount, total: candidates.length };
}

function appliedPairs(candidate) {
  return candidate?.mlStatus === 'applied' && candidate.drugs?.length > 1
    ? (candidate.mlPrediction?.pairs ?? []).filter((pair) => pair.inferenceStatus === 'applied' && pair.predictedSeverity)
    : [];
}

function ruleLabel(candidate) {
  return candidate?.status === 'accepted' ? 'Passed' : candidate?.status === 'rejected' ? 'Rejected' : 'Not available';
}

function analysisMetrics(data) {
  const candidates = data.candidateSets ?? [];
  return [
    ['Selected diseases', new Set(data.diseaseIds ?? (data.diseases ?? []).map((disease) => disease.id)).size],
    ['Mapped drugs in results', new Set(candidates.flatMap((candidate) => candidate.drugs ?? [])).size],
    ['Returned candidate sets', candidates.length],
    ['Passed rules', candidates.filter((candidate) => candidate.status === 'accepted').length],
    ['Rejected by rules', candidates.filter((candidate) => candidate.status === 'rejected').length],
    ['Pair predictions across results', mlSummary(candidates).pairCount],
  ];
}

function mappingMarkup(paths) {
  const treatments = paths.filter((path) => relationshipType(path) === 'CtD');
  return treatments.length ? `<ul class="mapping-list">${treatments.map((path) => `<li>${escapeHtml(path.sourceEntity?.name ?? path.sourceEntity?.id)} → ${escapeHtml(path.targetEntity?.name ?? path.targetEntity?.id)} <small>CtD</small></li>`).join('')}</ul>` : '<p>No treatment mapping paths were returned.</p>';
}

const RANK_EXPLANATION = 'At generation, sets are ordered by configured rule status (passed first), then more selected diseases represented, then fewer drugs. Candidate set ID breaks remaining ties. Backend validation can add a rejection without changing that rank. Interaction severity does not determine this rank.';

function candidateNarrative(candidate, data) {
  const labels = diseaseLabelMap(data);
  const covered = (candidate.treatedDiseaseIds ?? []).filter((id) => (data.diseaseIds ?? [...labels.keys()]).includes(id));
  const ml = candidateMlPresentation(candidate);
  return `<section class="candidate-narrative">
    <p class="eyebrow">Candidate #${escapeHtml(candidate.rank ?? 'Not provided')}</p>
    <h3>${escapeHtml(candidateLabel(candidate))}</h3>
    <h4>Why this candidate?</h4>
    <p>These drugs appear in the returned graph-derived candidate set. Its represented treatment connections are:</p>
    ${mappingMarkup(graphPaths(candidate))}
    <dl class="candidate-facts"><div><dt>Graph coverage</dt><dd>${covered.length} of ${(data.diseaseIds ?? [...labels.keys()]).length} selected diseases represented</dd><dd>${covered.map((id) => escapeHtml(labels.get(id) ?? id)).join(', ') || 'None returned'}</dd></div>
    <div><dt>Configured rule check</dt><dd>${ruleLabel(candidate)}</dd><dd>${(candidate.rejectionReasons ?? []).length} returned rejection reasons</dd></div>
    <div><dt>Interaction prediction</dt><dd>${escapeHtml(ml.label)}</dd><dd>${escapeHtml(ml.detail)}</dd></div></dl>
    <details><summary>Why this rank?</summary><p>${RANK_EXPLANATION}</p><p>Rank #${escapeHtml(candidate.rank ?? 'Not provided')} · Graph coverage ${covered.length} / ${(data.diseaseIds ?? [...labels.keys()]).length} · ${candidate.drugs?.length ?? 0} drugs · Rules: ${ruleLabel(candidate)} · ${appliedPairs(candidate).length} classified pairs</p></details>
  </section>`;
}

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function humanStatus(status) {
  const labels = {
    complete: 'Complete',
    partial: 'Partial',
    not_applicable: 'Not applicable',
    not_applied: 'Not applied',
    unavailable: 'Unavailable',
    error: 'Error',
    pending: 'Pending',
    processing: 'Processing',
    ready: 'Ready',
  };
  return labels[status] ?? String(status ?? 'Pending');
}

function candidateMlPresentation(candidate) {
  const pairs = appliedPairs(candidate);
  const pairCount = pairs.length;
  if (candidate?.drugs?.length === 1) {
    return {
      status: 'not_applicable',
      label: 'Not applicable',
      summary: 'Single-drug candidate; no drug pair to classify',
      detail: 'This candidate contains one drug, so there is no drug pair to classify.',
    };
  }
  if (candidate?.mlStatus === 'applied' && pairCount > 0) {
    return {
      status: 'complete',
      label: [...new Set(pairs.map((pair) => pair.predictedSeverity))].join(' / '),
      summary: pluralize(pairCount, 'drug-pair prediction'),
      detail: `Random Forest classified ${pluralize(pairCount, 'represented drug pair')}. Severity: ${[...new Set(pairs.map((pair) => pair.predictedSeverity))].join(', ')}.`,
    };
  }
  return {
    status: 'unavailable',
    label: 'Not available',
    summary: 'No pair-level prediction returned',
    detail: candidate?.mlPrediction?.reason ?? 'No pair-level prediction was returned for this candidate.',
  };
}

function computeWorkflowStages(data, selectedCandidateId = null, running = false, error = null) {
  if (error) {
    return WORKFLOW_STAGES.map(([key, name, pending]) => ({ key, name, status: 'error', summary: error }));
  }
  if (running) {
    return WORKFLOW_STAGES.map(([key, name, pending]) => ({
      key,
      name,
      status: 'pending',
      summary: 'Analysis running... Stage results are available after the response.',
    }));
  }
  if (!data) {
    return WORKFLOW_STAGES.map(([key, name, pending]) => ({ key, name, status: 'pending', summary: pending }));
  }

  const candidates = data.candidateSets ?? [];
  const paths = allGraphPaths(candidates);
  const uniqueCompounds = new Set(candidates.flatMap((candidate) => candidate.drugs ?? []));
  const accepted = candidates.filter((candidate) => candidate.status === 'accepted').length;
  const rejected = candidates.filter((candidate) => candidate.status === 'rejected').length;
  const selected = candidates.find((candidate) => candidate.candidateSetId === selectedCandidateId) ?? candidates[0];
  const ml = mlSummary(candidates);
  const optimization = data.metadata?.optimization;
  const coveredCount = candidates[0]?.treatedDiseaseIds?.length ?? 0;
  const targetCount = data.diseaseIds?.length ?? data.diseases?.length ?? 0;
  const selectedPaths = graphPaths(selected);
  const selectedMl = candidateMlPresentation(selected);
  const allSingleDrug = candidates.length > 0 && candidates.every((candidate) => candidate.drugs?.length === 1);

  return [
    {
      key: 'graph',
      name: 'Knowledge graph retrieval',
      status: paths.length ? 'complete' : 'unavailable',
      summary: `${pluralize(data.diseases?.length ?? 0, 'disease')} returned with ${pluralize(paths.length, 'evidence path')} across results.`,
      detail: 'PolyMerge retrieved represented Hetionet relationships connected to the selected diseases. Returned paths provide treatment, gene, and side-effect context; repeated paths are counted once.',
    },
    {
      key: 'mapping',
      name: 'Drug mapping',
      status: uniqueCompounds.size ? 'complete' : 'unavailable',
      summary: `${pluralize(uniqueCompounds.size, 'mapped drug')} appear in returned candidate sets.`,
      detail: 'Represented compound-to-disease treatment connections supply drugs for candidate generation.',
      mappings: paths,
    },
    {
      key: 'ranking',
      name: 'Candidate generation and ranking',
      status: candidates.length ? 'complete' : 'unavailable',
      summary: `${pluralize(candidates.length, 'candidate set')} returned in rank order.`,
      detail: 'PolyMerge combined graph-mapped drugs into candidate sets. The returned list may be capped; it is not the total number of combinations considered.',
    },
    {
      key: 'rules',
      name: 'Deterministic rules',
      status: !candidates.length ? 'unavailable' : rejected ? 'partial' : 'complete',
      summary: `${accepted} passed · ${rejected} rejected among returned sets; ${candidates.reduce((count, candidate) => count + (candidate.rejectionReasons?.length ?? 0), 0)} rejection reasons returned.`,
      detail: 'Each candidate was checked against the configured deterministic hard-rule layer. Passed means no configured hard-rule violation was detected.',
    },
    {
      key: 'optimization',
      name: 'Coverage optimization',
      status: optimization ? 'complete' : 'partial',
      summary: candidates.length ? `Top returned candidate: rank #${candidates[0].rank ?? 'Not provided'} · ${coveredCount} / ${targetCount} selected diseases represented · ${candidates[0].drugs?.length ?? 0} drugs` : 'No ranked candidate returned.',
      detail: `${RANK_EXPLANATION}${optimization?.selectedCandidateSetIds ? ` Separately, the greedy coverage baseline selected ${optimization.selectedCandidateSetIds.length} sets representing ${optimization.coveredDiseaseIds?.length ?? 0} selected diseases.` : ''}`,
    },
    {
      key: 'ml',
      name: 'Interaction prediction',
      status: allSingleDrug ? 'not_applicable' : ml.applied ? (ml.notApplied ? 'partial' : 'complete') : 'unavailable',
      summary: allSingleDrug
        ? 'Single-drug candidate; no drug pair to classify'
        : ml.applied
          ? `${ml.applied} of ${ml.total} candidates include drug-pair predictions`
          : 'No pair-level predictions returned',
      detail: 'The Random Forest model evaluates supported drug pairs after candidate generation. Its DDInter severity prediction is a separate evidence channel.',
    },
    {
      key: 'evidence',
      name: 'Selected candidate evidence',
      status: selected ? 'ready' : 'pending',
      summary: selected
        ? `Graph evidence: ${pluralize(selectedPaths.length, 'represented path')} · Configured rules: ${ruleLabel(selected)} · Interaction prediction: ${selectedMl.label}`
        : 'Select a candidate to inspect graph, rules, and ML evidence',
    },
  ];
}

function setMessage(container, message, kind = 'info') {
  container.innerHTML = `<p class="state-message state-${escapeHtml(kind)}" role="${kind === 'error' ? 'alert' : 'status'}">${escapeHtml(message)}</p>`;
}

function renderWorkflow(stages) {
  const list = document.getElementById('workflow-list');
  list.innerHTML = stages.map((stage, index) => `
    <li class="workflow-step status-${escapeHtml(stage.status)}">
      <div class="workflow-icon" aria-hidden="true">${index + 1}</div>
      <div>
        <div class="workflow-step-header">
          <strong>${escapeHtml(stage.name)}</strong>
          <span>${escapeHtml(humanStatus(stage.status))}</span>
        </div>
        <p>${escapeHtml(stage.summary)}</p>
        ${stage.detail ? `<details><summary>What happened?</summary><p>${escapeHtml(stage.detail)}</p></details>` : ''}
        ${stage.mappings ? `<details><summary>View mapped treatment connections</summary>${mappingMarkup(stage.mappings)}</details>` : ''}
      </div>
    </li>`).join('');
}

function renderSelectionSummary() {
  const count = document.getElementById('selection-count');
  const clear = document.getElementById('clear-selection');
  const analyze = document.getElementById('analyze-btn');
  const list = document.getElementById('selected-disease-list');
  const diseases = selectedDiseaseObjects();
  count.textContent = `${diseases.length} disease${diseases.length === 1 ? '' : 's'} selected`;
  clear.disabled = diseases.length === 0;
  analyze.disabled = diseases.length === 0 || Boolean(state.analysisStartedAt);
  list.innerHTML = diseases.map((disease) => `
    <button type="button" class="selected-pill" data-remove-disease="${escapeHtml(disease.id)}">
      <span>${escapeHtml(disease.name)}</span><small>${escapeHtml(disease.id)}</small>
    </button>`).join('');
  list.querySelectorAll('[data-remove-disease]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedDiseases.delete(button.dataset.removeDisease);
      renderDiseases();
    });
  });
}

function renderDiseases() {
  const diseaseList = document.getElementById('disease-list');
  const diseaseSearch = document.getElementById('disease-search');
  const filtered = filterDiseases(state.availableDiseases, diseaseSearch.value);
  if (!filtered.length) {
    setMessage(diseaseList, diseaseSearch.value ? 'No diseases match this search.' : 'No diseases are available from the graph service.', 'warning');
    renderSelectionSummary();
    return;
  }
  diseaseList.innerHTML = filtered.map((disease) => `
    <button type="button" class="disease-chip ${state.selectedDiseases.has(disease.id) ? 'selected' : ''}"
      data-id="${escapeHtml(disease.id)}" aria-pressed="${state.selectedDiseases.has(disease.id)}">
      <span>${escapeHtml(disease.name)}</span>
      <small>${escapeHtml(disease.id)}</small>
    </button>`).join('');
  diseaseList.querySelectorAll('.disease-chip').forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.dataset.id;
      if (state.selectedDiseases.has(id)) state.selectedDiseases.delete(id);
      else state.selectedDiseases.add(id);
      renderDiseases();
    });
  });
  renderSelectionSummary();
}

async function loadDiseases() {
  const catalogTag = document.getElementById('catalog-tag');
  const catalogMessage = document.getElementById('catalog-message');
  const diseaseList = document.getElementById('disease-list');
  catalogTag.textContent = 'Loading catalog';
  catalogMessage.hidden = false;
  catalogMessage.className = 'catalog-message loading-message';
  catalogMessage.innerHTML = '<strong>Loading disease catalog</strong><p>Connecting to the knowledge graph service...</p>';
  diseaseList.replaceChildren();
  try {
    const data = await fetchJson('/api/diseases', {}, DEFAULT_CATALOG_TIMEOUT_MS);
    state.availableDiseases = data.diseases ?? [];
    catalogMessage.hidden = true;
    catalogTag.textContent = 'Catalog ready';
    renderDiseases();
  } catch (error) {
    catalogTag.textContent = 'Catalog unavailable';
    catalogMessage.className = 'catalog-message unavailable-message';
    catalogMessage.innerHTML = `<div><strong>Disease catalog unavailable</strong><p>The knowledge graph catalog could not be loaded.</p><small>${escapeHtml(error.message)}</small></div><button type="button" id="retry-catalog" class="retry-button">Try Again</button>`;
    catalogMessage.hidden = false;
    diseaseList.replaceChildren();
    document.getElementById('retry-catalog').addEventListener('click', loadDiseases);
  }
}

function renderSummary(data) {
  const cards = document.getElementById('summary-cards');
  document.getElementById('analysis-summary').hidden = false;
  const labels = diseaseLabelMap(data);
  document.getElementById('your-analysis').innerHTML = `<h3>Your analysis</h3><ul class="analysis-diseases">${(data.diseaseIds ?? [...labels.keys()]).map((id) => `<li><strong>${escapeHtml(labels.get(id) ?? id)}</strong><small>${escapeHtml(id)}</small></li>`).join('')}</ul><p>PolyMerge searched represented relationships, generated drug sets, checked configured rules, ranked graph coverage, and classified supported drug pairs.</p>`;
  const cardData = analysisMetrics(data);
  cards.innerHTML = cardData.map(([label, value]) => `
    <div class="funnel-step"><div class="value">${escapeHtml(value)}</div><div class="label">${escapeHtml(label)}</div></div>`).join('');
}

function renderResults(data) {
  const results = document.getElementById('results');
  const candidates = data.candidateSets ?? [];
  renderSummary(data);
  if (data.metadata?.dataStatus === 'graph_unavailable') {
    setMessage(results, data.metadata.warning || 'Graph evidence is unavailable; no candidate sets were returned.', 'warning');
    return;
  }
  if (!candidates.length) {
    setMessage(results, 'No candidate sets were returned for this selection.', 'empty');
    return;
  }

  const diseaseLabels = diseaseLabelMap(data);
  results.innerHTML = candidates.map((candidate) => {
    const selected = candidate.candidateSetId === state.selectedCandidateId;
    const rejectionReasons = (candidate.rejectionReasons ?? []).map((reason) => reason.message).join('; ');
    const ml = candidateMlPresentation(candidate);
    return `<article class="result-card ${selected ? 'selected-result' : ''}">
      <div class="result-header">
        <div>
          <p class="eyebrow">Candidate #${escapeHtml(candidate.rank ?? 'Not provided')}</p>
          <h3>${escapeHtml(candidateLabel(candidate))}</h3>
        </div>
        <span class="status-badge status-${candidate.status === 'rejected' ? 'rejected' : 'accepted'}">Rule check: ${ruleLabel(candidate)}</span>
      </div>
      <ul class="drug-list">${(candidate.drugs ?? []).map((id, index) => `
        <li class="drug-item"><strong>${escapeHtml(candidate.drugNames?.[index] ?? id)}</strong><code>${escapeHtml(id)}</code></li>`).join('')}</ul>
      <div class="result-meta">
        <span><strong>Graph coverage</strong> ${(candidate.treatedDiseaseIds ?? []).length} of ${data.diseaseIds?.length ?? data.diseases?.length ?? 0} selected diseases represented</span>
        <span>Covered: ${(candidate.treatedDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None provided'}</span>
        <span>Uncovered: ${(candidate.uncoveredDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None'}</span>
        <span>Drugs: ${escapeHtml(candidate.drugCount ?? candidate.drugs?.length ?? 'Not provided')}</span>
        <span>Interaction prediction: ${escapeHtml(ml.label)}</span>
      </div>
      ${rejectionReasons ? `<p class="inline-warning">${escapeHtml(rejectionReasons)}</p>` : ''}
      <button type="button" class="secondary explanation-button" data-candidate-id="${escapeHtml(candidate.candidateSetId)}" aria-pressed="${selected}">Inspect candidate</button>
    </article>`;
  }).join('');
  results.querySelectorAll('[data-candidate-id]').forEach((button) => {
    button.addEventListener('click', () => selectCandidate(button.dataset.candidateId, true));
  });
}

function renderGraphVisualization(candidate) {
  const priority = { CtD: 0, CbG: 1, CuG: 1, CdG: 1, CcSE: 2 };
  const paths = graphPaths(candidate).slice().sort((a, b) => priority[relationshipType(a)] - priority[relationshipType(b)]).slice(0, 30);
  if (!paths.length) return '<p class="muted">Graph paths are unavailable for this candidate.</p>';
  return `<div class="graph-stage">
    <div class="evidence-diagram" aria-label="Candidate knowledge graph evidence paths">
      ${paths.map((path) => {
        const rel = relationshipType(path);
        const type = rel === 'CtD' ? 'disease' : rel === 'CcSE' ? 'side-effect' : 'gene';
        return `<div class="evidence-edge">
          <div class="evidence-node node-compound"><small>Drug</small><strong>${escapeHtml(path.sourceEntity?.name ?? path.sourceEntity?.id)}</strong></div>
          <span class="evidence-connector" title="${escapeHtml(path.pathId)} · ${escapeHtml(path.provenance?.source)} · ${escapeHtml(path.provenance?.graphVersion)}">${escapeHtml(rel)} <span aria-hidden="true">→</span></span>
          <div class="evidence-node node-${type}"><small>${type === 'side-effect' ? 'Side Effect' : type === 'disease' ? 'Disease' : 'Gene'}</small><strong>${escapeHtml(path.targetEntity?.name ?? path.targetEntity?.id)}</strong></div>
        </div>`;
      }).join('')}
    </div>
    <div class="graph-legend">
      <span class="legend-compound">Drug / Compound</span><span class="legend-disease">Disease</span><span class="legend-gene">Gene</span><span class="legend-side-effect">Side Effect</span>
    </div>
    <dl class="relationship-legend"><div><dt>CtD</dt><dd>Compound treats Disease</dd></div><div><dt>CbG</dt><dd>Compound binds Gene</dd></div><div><dt>CuG</dt><dd>Compound upregulates Gene</dd></div><div><dt>CdG</dt><dd>Compound downregulates Gene</dd></div><div><dt>CcSE</dt><dd>Compound causes Side Effect</dd></div></dl>
    ${graphPaths(candidate).length > paths.length ? `<p class="muted">Showing ${paths.length} of ${graphPaths(candidate).length} paths to keep the graph readable.</p>` : ''}
  </div>`;
}

function renderPathList(candidate, semanticType, title) {
  const paths = graphPaths(candidate).filter((path) => path.semanticType === semanticType);
  if (!paths.length) return '';
  return `<section class="evidence-section"><h4>${escapeHtml(title)}</h4><ul class="path-list">${paths.map((path) => `
    <li><strong>${escapeHtml(path.sourceEntity?.name ?? path.sourceEntity?.id)}</strong>
      <span class="relationship-arrow">-- ${escapeHtml(relationshipType(path))} --></span>
      <strong>${escapeHtml(path.targetEntity?.name ?? path.targetEntity?.id)}</strong>
      <details><summary>Technical graph details</summary><small>${escapeHtml(path.sourceEntity?.id)} → ${escapeHtml(path.targetEntity?.id)} · ${escapeHtml(path.semanticType)} · ${escapeHtml(path.provenance?.source ?? 'source not provided')} · ${escapeHtml(path.provenance?.graphVersion ?? 'version not provided')} · ${escapeHtml(path.pathId)}</small></details>
    </li>`).join('')}</ul></section>`;
}

function renderSelectedCandidate(candidate, data) {
  const container = document.getElementById('explainability');
  if (!candidate) {
    container.innerHTML = '<div class="empty-state"><span class="empty-icon">ⓘ</span><p>Run a simulation and choose a candidate to inspect its explanations.</p></div>';
    return;
  }
  const diseaseLabels = diseaseLabelMap(data);
  const mlPairs = appliedPairs(candidate);
  const reasons = candidate.rejectionReasons ?? [];
  const ml = candidateMlPresentation(candidate);
  container.innerHTML = `<article class="candidate-explanation">
    ${candidateNarrative(candidate, data)}
    <aside class="reading-guide"><h4>How to read this result</h4><p><strong>Graph Evidence</strong> shows represented biomedical relationships. <strong>Deterministic Rules</strong> shows configured rule outcomes. <strong>Interaction Prediction</strong> shows Random Forest predicted DDInter severity for supported drug pairs.</p></aside>
    <section class="evidence-section section-graph">
      <h4>Graph Evidence</h4>
      <div class="graph-summary">
        <span>Graph coverage: ${(candidate.treatedDiseaseIds ?? []).length} / ${data.diseaseIds?.length ?? data.diseases?.length ?? 0}</span>
        <span>Covered diseases: ${(candidate.treatedDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None provided'}</span>
        <span>Uncovered diseases: ${(candidate.uncoveredDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None'}</span>
      </div>
      <p>Represented evidence for this candidate</p>
      ${renderGraphVisualization(candidate)}
      <details class="technical-details"><summary>Technical graph details</summary><p>${escapeHtml(candidate.graphEvidence?.source ?? data.metadata?.graph ?? 'Not provided')} · ${escapeHtml(candidate.graphEvidence?.graphVersion ?? 'Not provided')}</p>
      ${renderPathList(candidate, 'treatment', 'CtD Treatment Paths')}
      ${renderPathList(candidate, 'gene_context', 'Gene Context')}
      ${renderPathList(candidate, 'side_effect_context', 'Side-Effect Context')}</details>
    </section>
    <section class="evidence-section section-rules">
      <h4>Deterministic Rules</h4>
      ${reasons.length ? `<ul class="rule-list">${reasons.map((reason) => `<li class="rule-item rule-rejected">
        <strong>Configured rule check · Rejected</strong>
        <p>${escapeHtml(reason.message ?? 'Reason not provided')}</p>
        ${reason.pair?.length ? `<small>Pair: ${reason.pair.map(escapeHtml).join(' + ')}</small>` : ''}
        <small>Stage: ${escapeHtml(reason.stage ?? 'Not provided')} · Source: ${escapeHtml(reason.source ?? 'PolyMerge Safety Rules')}</small>
      </li>`).join('')}</ul>` : `<div class="rule-pass"><strong>Configured rule check</strong><span>${ruleLabel(candidate)}</span><p>${candidate.status === 'accepted' ? 'No configured deterministic hard-rule violation detected.' : 'No rule reason was returned.'}</p></div>`}
    </section>
    <section class="evidence-section section-predictions">
      <h4>Interaction Prediction</h4>
      ${candidate.mlStatus === 'applied' && mlPairs.length ? `<ul class="prediction-list">${mlPairs.map((pair) => `<li class="prediction-item">
        <div class="prediction-grid">
          <span><small>Drug pair</small><strong>${pair.drugPair?.map((id) => escapeHtml(candidate.drugNames?.[candidate.drugs.indexOf(id)] ?? id)).join(' + ') ?? 'Drug pair not provided'}</strong></span>
          <span><small>Predicted severity</small><strong>${escapeHtml(pair.predictedSeverity)}</strong></span>
          <span><small>Model</small><strong>Random Forest · Sprint 5</strong></span>
        </div>
        <details><summary>Technical model details</summary><small>${escapeHtml(pair.model?.name ?? 'Model not provided')} · ${escapeHtml(pair.model?.version ?? 'Version not provided')} · ${escapeHtml(pair.inferenceStatus ?? 'Status not provided')}</small></details>
      </li>`).join('')}</ul>` : `<div class="predictions-unavailable"><strong>${escapeHtml(ml.label)}</strong><p>${escapeHtml(ml.detail)}</p></div>`}
    </section>
    <details class="technical-details"><summary>Candidate metadata</summary><p>Candidate set ID: ${escapeHtml(candidate.candidateSetId)} · Raw status: ${escapeHtml(candidate.status)}</p><p>${(candidate.drugs ?? []).map(escapeHtml).join(', ')}</p></details>
    <p class="overall-disclaimer">PolyMerge is a research decision-support prototype and does not provide clinical recommendations.</p>
  </article>`;
}

function selectCandidate(candidateId, navigate = false) {
  state.selectedCandidateId = candidateId;
  const candidates = state.currentResult?.candidateSets ?? [];
  const candidate = candidates.find((item) => item.candidateSetId === candidateId) ?? candidates[0];
  renderWorkflow(computeWorkflowStages(state.currentResult, state.selectedCandidateId));
  renderResults(state.currentResult);
  renderSelectedCandidate(candidate, state.currentResult);
  if (navigate) window.location.hash = 'explainability-panel';
}

function startElapsedTimer() {
  const elapsed = document.getElementById('elapsed-time');
  clearInterval(state.elapsedTimer);
  state.analysisStartedAt = Date.now();
  state.elapsedTimer = setInterval(() => {
    elapsed.textContent = `Elapsed: ${Math.floor((Date.now() - state.analysisStartedAt) / 1000)}s`;
  }, 1000);
}

function stopElapsedTimer() {
  clearInterval(state.elapsedTimer);
  state.elapsedTimer = null;
  state.analysisStartedAt = null;
}

async function analyzeCombination() {
  if (!state.selectedDiseases.size || state.analysisStartedAt) return;
  const analyzeBtn = document.getElementById('analyze-btn');
  const results = document.getElementById('results');
  const catalogTag = document.getElementById('catalog-tag');
  const running = document.getElementById('analysis-running');
  analyzeBtn.disabled = true;
  catalogTag.textContent = 'Search in progress';
  running.hidden = false;
  state.currentResult = null;
  state.selectedCandidateId = null;
  document.getElementById('analysis-summary').hidden = true;
  startElapsedTimer();
  renderWorkflow(computeWorkflowStages(null, null, true));
  setMessage(results, 'Analysis running. The local research graph pipeline may take about a minute.');
  document.getElementById('summary-cards').replaceChildren();
  renderSelectedCandidate(null, null);
  try {
    const data = await fetchJson('/api/candidate-sets/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseaseIds: Array.from(state.selectedDiseases) }),
    }, DEFAULT_CANDIDATE_TIMEOUT_MS);
    state.currentResult = data;
    state.selectedCandidateId = data.candidateSets?.[0]?.candidateSetId ?? null;
    catalogTag.textContent = data.metadata?.dataStatus === 'graph_unavailable' ? 'Graph unavailable' : 'Search complete';
    renderResults(data);
    renderWorkflow(computeWorkflowStages(data, state.selectedCandidateId));
    renderSelectedCandidate(data.candidateSets?.[0], data);
  } catch (error) {
    catalogTag.textContent = error.message.includes('timed out') ? 'Candidate search timeout' : 'System error';
    setMessage(results, `Candidate search unavailable: ${error.message}`, 'error');
    renderWorkflow(computeWorkflowStages(null, null, false, error.message));
  } finally {
    stopElapsedTimer();
    running.hidden = true;
    renderSelectionSummary();
  }
}

function renderModelAnalysisShell(data = null) {
  const rows = data?.rows ?? [
    { Model: 'LogisticRegression', 'Mean Macro F1': '0.290759' },
    { Model: 'RandomForestClassifier', 'Mean Macro F1': '0.506086' },
    { Model: 'HistGradientBoostingClassifier', 'Mean Macro F1': '0.407769' },
  ];
  const values = rows.map((row) => ({ name: row.Model, value: Number(row['Mean Macro F1']) }));
  const max = Math.max(...values.map((row) => row.value));
  const table = rows.map((row) => `<tr>${Object.values(row).map((value) => `<td>${escapeHtml(value)}</td>`).join('')}</tr>`).join('');
  const tabs = [
    ['overview', 'Overview'],
    ['eda', 'EDA'],
    ['comparison', 'Model Comparison'],
    ['final', 'Final Model'],
    ['limitations', 'Limitations'],
  ];
  const selected = state.modelAnalysisTab;
  const tabNav = `<div class="analysis-tabs" role="tablist" aria-label="Model Analysis sections">
    ${tabs.map(([id, label]) => `<button type="button" role="tab" aria-selected="${selected === id}" data-analysis-tab="${escapeHtml(id)}">${escapeHtml(label)}</button>`).join('')}
  </div>`;
  const sections = {
    overview: `<section class="analysis-section" role="tabpanel">
      <h3>Overview</h3>
      <p>PolyMerge uses graph evidence, deterministic rules, set-cover optimization, and a traditional Random Forest DDI severity model as separate research evidence channels.</p>
      <div class="final-metrics">
        <span>DDInter classes: Major, Moderate, Minor</span>
        <span>Primary metric: validation Macro F1</span>
        <span>Selected model: Random Forest</span>
      </div>
    </section>`,
    comparison: `<section class="analysis-section" role="tabpanel">
      <h3>Model Comparison</h3>
      <p>Preserved Sprint 4 validation Macro F1. Random Forest was selected by highest mean validation Macro F1.</p>
      <div class="bar-chart" aria-label="Validation Macro F1 chart">
        ${values.map((row) => `<div class="bar-row ${row.name === 'RandomForestClassifier' ? 'selected-model' : ''}"><span>${escapeHtml(row.name.replace('Classifier', ''))}</span><div><i style="width:${Math.max(8, (row.value / max) * 100)}%"></i></div><strong>${row.value.toFixed(6)}</strong></div>`).join('')}
      </div>
      <p class="muted">Selected model: Random Forest. It had the highest mean validation Macro F1 among the three required traditional ML algorithms.</p>
      <div class="comparison-table-wrap"><table class="comparison-table"><thead><tr>${Object.keys(rows[0] ?? {}).map((key) => `<th>${escapeHtml(key)}</th>`).join('')}</tr></thead><tbody>${table}</tbody></table></div>
    </section>`,
    eda: `<section class="analysis-section" role="tabpanel">
      <h3>Exploratory Data Analysis</h3>
      <div class="eda-metrics">
        <div><strong>130,422</strong><span>Total labeled pairs</span></div>
        <div><strong>26,914</strong><span>Major · 20.64%</span></div>
        <div><strong>96,675</strong><span>Moderate · 74.12%</span></div>
        <div><strong>6,833</strong><span>Minor · 5.24%</span></div>
      </div>
      <p class="muted">The class imbalance is why Macro F1 is more informative than accuracy alone.</p>
      <div class="eda-grid">
        <figure><h4>Class Distribution</h4><img src="/docs/figures/sprint3/severity_distribution.svg" alt="DDInter class distribution" /><figcaption>Moderate interactions make up most labeled DDInter pairs, creating a class-imbalanced prediction problem. This is why Macro F1 is the primary metric.</figcaption></figure>
        <figure><h4>Structure Coverage</h4><img src="/docs/figures/sprint3/pair_structure_coverage.svg" alt="Pair structure coverage" /><figcaption>Molecular descriptors are available only where a reviewed structure mapping exists.</figcaption></figure>
        <figure><h4>Graph Mapping Coverage</h4><img src="/docs/figures/sprint3/hetionet_mapping_coverage.svg" alt="Hetionet mapping coverage" /><figcaption>Only a subset of DDInter drugs map to Hetionet, so graph-derived features have explicit missingness.</figcaption></figure>
        <figure><h4>Feature Missingness</h4><img src="/docs/figures/sprint3/feature_missingness.svg" alt="Feature missingness" /><figcaption>Missing values are tracked by source rather than treated as evidence of absence.</figcaption></figure>
      </div>
    </section>`,
    final: `<section class="analysis-section" role="tabpanel">
      <h3>Final Selected Model</h3>
      <p>The final test split was evaluated once after model selection and was not used for tuning.</p>
      <div class="comparison-table-wrap"><table class="comparison-table metric-table"><tbody>
        <tr><th>Model</th><td>Random Forest</td></tr>
        <tr><th>Validation Macro F1</th><td>0.506086 +/- 0.005695</td></tr>
        <tr><th>Final Test Macro F1</th><td>0.524630</td></tr>
        <tr><th>Balanced Accuracy</th><td>0.475467</td></tr>
        <tr><th>Macro AUROC</th><td>0.798793</td></tr>
        <tr><th>Macro AUPRC</th><td>0.632468</td></tr>
      </tbody></table></div>
    </section>`,
    limitations: `<section class="analysis-section" role="tabpanel">
      <h3>Limitations</h3>
      <p>Major and Minor recall are substantially lower than Moderate recall. These are research classification metrics, not clinical validation. No final test results were recomputed for this page.</p>
    </section>`,
  };
  return `${tabNav}${sections[selected] ?? sections.overview}`;
}

function bindModelAnalysisTabs() {
  document.querySelectorAll('[data-analysis-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      state.modelAnalysisTab = button.dataset.analysisTab;
      document.getElementById('model-comparison-content').innerHTML = renderModelAnalysisShell(state.modelAnalysisData);
      bindModelAnalysisTabs();
    });
  });
}

async function loadModelComparison() {
  const content = document.getElementById('model-comparison-content');
  content.innerHTML = '<p class="state-message" role="status">Loading preserved model analysis...</p>';
  try {
    const data = await fetchJson('/api/model-comparison', {}, DEFAULT_CATALOG_TIMEOUT_MS);
    state.modelAnalysisData = data;
    content.innerHTML = renderModelAnalysisShell(data);
    bindModelAnalysisTabs();
    state.comparisonLoaded = true;
  } catch (error) {
    state.modelAnalysisData = null;
    content.innerHTML = `<p class="state-message state-warning">Model comparison endpoint unavailable, showing preserved checked-in values. ${escapeHtml(error.message)}</p>${renderModelAnalysisShell()}`;
    bindModelAnalysisTabs();
  }
}

function showView() {
  const viewIds = ['home', 'simulation', 'explainability-panel', 'model-analysis'];
  const requested = window.location.hash.slice(1) || 'home';
  const view = viewIds.includes(requested) ? requested : 'home';
  document.body.dataset.view = view;
  document.getElementById('page-title').textContent = view === 'home'
    ? 'Research Dashboard'
    : view === 'simulation'
      ? 'Simulation'
      : view === 'model-analysis'
        ? 'Model Analysis'
        : 'Explainability';
  document.querySelectorAll('.sidebar nav a').forEach((link) => {
    if (link.hash === `#${view}`) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  if (view === 'model-analysis' && !state.comparisonLoaded) loadModelComparison();
  window.scrollTo(0, 0);
}

function init() {
  renderWorkflow(computeWorkflowStages(null));
  document.getElementById('analyze-btn').addEventListener('click', analyzeCombination);
  document.getElementById('disease-search').addEventListener('input', renderDiseases);
  document.getElementById('clear-selection').addEventListener('click', () => {
    state.selectedDiseases.clear();
    renderDiseases();
  });
  document.getElementById('start-simulation').addEventListener('click', () => {
    window.location.hash = 'simulation';
  });
  document.getElementById('sidebar-toggle').addEventListener('click', () => {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    document.getElementById('sidebar-toggle').setAttribute('aria-expanded', String(!collapsed));
  });
  window.addEventListener('hashchange', showView);
  showView();
  loadDiseases();
}

globalThis.PolyMergeFrontend = {
  ALLOWED_GRAPH_RELATIONSHIPS,
  computeWorkflowStages,
  filterDiseases,
  graphPaths,
  humanStatus,
  mlSummary,
  candidateMlPresentation,
  analysisMetrics,
  candidateNarrative,
  renderGraphVisualization,
  renderSummary,
  renderSelectedCandidate,
  selectCandidate,
  state,
  escapeHtml,
};

if (typeof document !== 'undefined') {
  init();
}
