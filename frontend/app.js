const WORKFLOW_STAGES = [
  ['graph', 'Knowledge graph retrieval', 'Disease evidence lookup'],
  ['mapping', 'Drug mapping', 'Compounds linked to selected diseases'],
  ['ranking', 'Candidate ranking', 'Candidate sets ordered for review'],
  ['rules', 'Deterministic rules', 'Configured rule check'],
  ['optimization', 'Coverage optimization', 'Graph coverage summary'],
  ['ml', 'Interaction prediction', 'Drug-pair severity prediction'],
  ['evidence', 'Evidence summary', 'Candidate evidence ready for inspection'],
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
  return candidates.flatMap((candidate) => graphPaths(candidate));
}

function mlSummary(candidates) {
  const applied = candidates.filter((candidate) => candidate.mlStatus === 'applied').length;
  const notApplied = candidates.filter((candidate) => candidate.mlStatus !== 'applied').length;
  const pairCount = candidates.reduce((total, candidate) => total + (candidate.mlPrediction?.pairs?.length ?? 0), 0);
  return { applied, notApplied, pairCount, total: candidates.length };
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
  const pairCount = candidate?.mlPrediction?.pairs?.length ?? 0;
  if ((candidate?.drugs?.length ?? 0) < 2) {
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
      label: 'Applied',
      summary: pluralize(pairCount, 'drug-pair prediction'),
      detail: `${pairCount} pair prediction${pairCount === 1 ? '' : 's'} returned.`,
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
      status: 'processing',
      summary: key === 'graph' ? 'Analysis running...' : pending,
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
  const coveredCount = optimization?.coveredDiseaseIds?.length ?? selected?.treatedDiseaseIds?.length ?? 0;
  const targetCount = data.diseaseIds?.length ?? data.diseases?.length ?? state.selectedDiseases.size;
  const selectedPaths = graphPaths(selected);
  const selectedRules = selected?.rejectionReasons?.length ?? 0;
  const selectedMl = candidateMlPresentation(selected);
  const allSingleDrug = candidates.length > 0 && candidates.every((candidate) => (candidate.drugs?.length ?? 0) < 2);

  return [
    {
      key: 'graph',
      name: 'Knowledge graph retrieval',
      status: paths.length ? 'complete' : 'unavailable',
      summary: `${pluralize(data.diseases?.length ?? 0, 'disease')} resolved · ${pluralize(paths.length, 'evidence path')}`,
    },
    {
      key: 'mapping',
      name: 'Drug mapping',
      status: uniqueCompounds.size ? 'complete' : 'unavailable',
      summary: `${pluralize(uniqueCompounds.size, 'compound')} identified`,
    },
    {
      key: 'ranking',
      name: 'Candidate ranking',
      status: candidates.length ? 'complete' : 'unavailable',
      summary: `${pluralize(candidates.length, 'candidate set')} ranked`,
    },
    {
      key: 'rules',
      name: 'Deterministic rules',
      status: rejected ? 'partial' : 'complete',
      summary: `${accepted} accepted · ${rejected} rejected`,
    },
    {
      key: 'optimization',
      name: 'Coverage optimization',
      status: optimization ? 'complete' : 'partial',
      summary: `${coveredCount} / ${targetCount} target diseases covered`,
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
    },
    {
      key: 'evidence',
      name: 'Evidence summary',
      status: selected ? 'ready' : 'pending',
      summary: selected
        ? `${pluralize(selectedPaths.length, 'graph path')} · ${selectedRules || 'no'} rejection reasons · ${selectedMl.summary}`
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
  const candidates = data.candidateSets ?? [];
  const accepted = candidates.filter((candidate) => candidate.status === 'accepted').length;
  const rejected = candidates.filter((candidate) => candidate.status === 'rejected').length;
  const paths = allGraphPaths(candidates).length;
  const ml = mlSummary(candidates);
  const cardData = [
    ['Candidate sets', candidates.length],
    ['Accepted', accepted],
    ['Rejected', rejected],
    ['Graph paths', paths],
    ['ML applied', `${ml.applied} / ${ml.total}`],
    ['Pair predictions', ml.pairCount],
  ];
  cards.innerHTML = cardData.map(([label, value]) => `
    <div class="card"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value)}</div></div>`).join('');
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
          <p class="eyebrow">Rank ${escapeHtml(candidate.rank ?? 'Not provided')}</p>
          <h3>${escapeHtml(candidateLabel(candidate))}</h3>
        </div>
        <span class="status-badge status-${candidate.status === 'rejected' ? 'rejected' : 'accepted'}">${escapeHtml(candidate.status ?? 'Status not provided')}</span>
      </div>
      <ul class="drug-list">${(candidate.drugs ?? []).map((id, index) => `
        <li class="drug-item"><strong>${escapeHtml(candidate.drugNames?.[index] ?? id)}</strong><code>${escapeHtml(id)}</code></li>`).join('')}</ul>
      <div class="result-meta">
        <span><strong>Coverage</strong> ${(candidate.treatedDiseaseIds ?? []).length} of ${data.diseaseIds?.length ?? state.selectedDiseases.size} target diseases</span>
        <span>Covered: ${(candidate.treatedDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None provided'}</span>
        <span>Uncovered: ${(candidate.uncoveredDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None'}</span>
        <span>Drugs: ${escapeHtml(candidate.drugCount ?? candidate.drugs?.length ?? 'Not provided')}</span>
        <span>Interaction prediction: ${escapeHtml(ml.label)}</span>
      </div>
      ${rejectionReasons ? `<p class="inline-warning">${escapeHtml(rejectionReasons)}</p>` : ''}
      <button type="button" class="secondary explanation-button" data-candidate-id="${escapeHtml(candidate.candidateSetId)}">Inspect evidence</button>
    </article>`;
  }).join('');
  results.querySelectorAll('[data-candidate-id]').forEach((button) => {
    button.addEventListener('click', () => selectCandidate(button.dataset.candidateId, true));
  });
}

function renderGraphVisualization(candidate) {
  const paths = graphPaths(candidate).slice(0, 30);
  if (!paths.length) return '<p class="muted">Graph paths are unavailable for this candidate.</p>';
  const nodes = new Map();
  const edges = [];
  for (const path of paths) {
    const source = path.sourceEntity ?? {};
    const target = path.targetEntity ?? {};
    const rel = relationshipType(path);
    if (!source.id || !target.id || !ALLOWED_GRAPH_RELATIONSHIPS.has(rel)) continue;
    nodes.set(source.id, { id: source.id, label: source.name ?? source.id, type: 'compound' });
    nodes.set(target.id, { id: target.id, label: target.name ?? target.id, type: String(target.kind ?? 'entity').toLowerCase().replace(/\s+/g, '-') });
    edges.push({ source: source.id, target: target.id, label: rel, pathId: path.pathId, provenance: path.provenance, semanticType: path.semanticType });
  }
  const grouped = { compound: [], disease: [], gene: [], 'side-effect': [], entity: [] };
  for (const node of nodes.values()) {
    if (node.type.includes('compound')) grouped.compound.push(node);
    else if (node.type.includes('disease')) grouped.disease.push(node);
    else if (node.type.includes('gene')) grouped.gene.push(node);
    else if (node.type.includes('side')) grouped['side-effect'].push(node);
    else grouped.entity.push(node);
  }
  const positioned = new Map();
  const place = (items, x, startY, gap) => {
    items.forEach((node, index) => positioned.set(node.id, { ...node, x, y: startY + index * gap }));
  };
  place(grouped.compound, 90, 70, 72);
  place(grouped.disease, 720, 60, 74);
  place(grouped.gene, 430, 70, 48);
  place(grouped['side-effect'], 430, 330, 48);
  place(grouped.entity, 720, 330, 48);
  const height = Math.max(420, Math.max(...Array.from(positioned.values()).map((node) => node.y), 360) + 60);
  return `<div class="graph-stage">
    <svg class="graph-svg" viewBox="0 0 820 ${height}" role="img" aria-label="Candidate knowledge graph evidence paths">
      <defs><marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z"></path></marker></defs>
      ${edges.map((edge) => {
        const source = positioned.get(edge.source);
        const target = positioned.get(edge.target);
        if (!source || !target) return '';
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        return `<g class="graph-edge-group">
          <line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" marker-end="url(#arrowhead)"></line>
          <text x="${midX}" y="${midY - 6}">${escapeHtml(edge.label)}</text>
          <title>${escapeHtml(edge.pathId)} · ${escapeHtml(edge.semanticType)} · ${escapeHtml(edge.provenance?.source ?? 'source not provided')} · ${escapeHtml(edge.provenance?.graphVersion ?? 'version not provided')}</title>
        </g>`;
      }).join('')}
      ${Array.from(positioned.values()).map((node) => `<g class="graph-node-group graph-node-${escapeHtml(node.type)}" transform="translate(${node.x} ${node.y})">
        <circle r="23"></circle>
        <text y="4">${escapeHtml(node.label).slice(0, 22)}</text>
        <title>${escapeHtml(node.id)} · ${escapeHtml(node.type)}</title>
      </g>`).join('')}
    </svg>
    <div class="graph-legend">
      <span class="legend-compound">Compound</span><span class="legend-disease">Disease</span><span class="legend-gene">Gene</span><span class="legend-side-effect">Side Effect</span>
    </div>
    ${graphPaths(candidate).length > paths.length ? `<p class="muted">Showing ${paths.length} of ${graphPaths(candidate).length} paths to keep the graph readable.</p>` : ''}
  </div>`;
}

function renderPathList(candidate, semanticType, title) {
  const paths = graphPaths(candidate).filter((path) => path.semanticType === semanticType);
  if (!paths.length) return '';
  return `<section class="evidence-section"><h4>${escapeHtml(title)}</h4><ul class="path-list">${paths.slice(0, 12).map((path) => `
    <li><strong>${escapeHtml(path.sourceEntity?.name ?? path.sourceEntity?.id)}</strong>
      <span class="relationship-arrow">-- ${escapeHtml(relationshipType(path))} --></span>
      <strong>${escapeHtml(path.targetEntity?.name ?? path.targetEntity?.id)}</strong>
      <details><summary>Metadata</summary><small>${escapeHtml(path.provenance?.source ?? 'source not provided')} · ${escapeHtml(path.provenance?.graphVersion ?? 'version not provided')} · ${escapeHtml(path.pathId)}</small></details>
    </li>`).join('')}</ul></section>`;
}

function renderSelectedCandidate(candidate, data) {
  const container = document.getElementById('explainability');
  if (!candidate) {
    container.innerHTML = '<div class="empty-state"><span class="empty-icon">ⓘ</span><p>Run a simulation and choose a candidate to inspect its explanations.</p></div>';
    return;
  }
  const diseaseLabels = diseaseLabelMap(data);
  const mlPairs = candidate.mlPrediction?.pairs ?? [];
  const reasons = candidate.rejectionReasons ?? [];
  const ml = candidateMlPresentation(candidate);
  container.innerHTML = `<article class="candidate-explanation">
    <header class="candidate-header">
      <div>
        <span class="rank-badge">#${escapeHtml(candidate.rank ?? '-')}</span>
        <strong>Candidate Explanation</strong>
        <span class="status-badge status-${candidate.status === 'rejected' ? 'rejected' : 'accepted'}">${escapeHtml(candidate.status)}</span>
      </div>
      <div class="drug-list">${(candidate.drugs ?? []).map((drug) => `<code>${escapeHtml(drug)}</code>`).join('')}</div>
    </header>
    <section class="evidence-section section-graph">
      <h4>Graph Evidence</h4>
      <div class="graph-summary">
        <span>Graph coverage: ${(candidate.treatedDiseaseIds ?? []).length} / ${data.diseaseIds?.length ?? data.diseases?.length ?? 0}</span>
        <span>Covered diseases: ${(candidate.treatedDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None provided'}</span>
        <span>Uncovered diseases: ${(candidate.uncoveredDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None'}</span>
      </div>
      ${renderGraphVisualization(candidate)}
      <details class="technical-details"><summary>Graph metadata</summary><p>${escapeHtml(candidate.graphEvidence?.source ?? data.metadata?.graph ?? 'Not provided')} · ${escapeHtml(candidate.graphEvidence?.graphVersion ?? 'Not provided')}</p></details>
    </section>
    ${renderPathList(candidate, 'treatment', 'CtD Treatment Paths')}
    ${renderPathList(candidate, 'gene_context', 'Gene Context')}
    ${renderPathList(candidate, 'side_effect_context', 'Side-Effect Context')}
    <section class="evidence-section section-rules">
      <h4>Deterministic Rules</h4>
      ${reasons.length ? `<ul class="rule-list">${reasons.map((reason) => `<li class="rule-item rule-rejected">
        <strong>Configured rule check · Rejected</strong>
        <p>${escapeHtml(reason.message ?? 'Reason not provided')}</p>
        ${reason.pair?.length ? `<small>Pair: ${reason.pair.map(escapeHtml).join(' + ')}</small>` : ''}
        <small>Stage: ${escapeHtml(reason.stage ?? 'Not provided')} · Source: ${escapeHtml(reason.source ?? 'PolyMerge Safety Rules')}</small>
      </li>`).join('')}</ul>` : '<div class="rule-pass"><strong>Configured rule check</strong><span>Passed</span><p>No configured deterministic hard-rule violation detected.</p></div>'}
    </section>
    <section class="evidence-section section-predictions">
      <h4>Interaction Prediction</h4>
      ${candidate.mlStatus === 'applied' && mlPairs.length ? `<ul class="prediction-list">${mlPairs.map((pair) => `<li class="prediction-item">
        <div class="prediction-grid">
          <span><small>Drug pair</small><strong>${pair.drugPair?.map(escapeHtml).join(' + ') ?? 'Drug pair not provided'}</strong></span>
          <span><small>Predicted severity</small><strong>${escapeHtml(pair.predictedSeverity)}</strong></span>
          <span><small>Model</small><strong>Random Forest · Sprint 5</strong></span>
        </div>
        <details><summary>Technical model details</summary><small>${escapeHtml(pair.model?.name ?? 'Model not provided')} · ${escapeHtml(pair.model?.version ?? 'Version not provided')} · ${escapeHtml(pair.inferenceStatus ?? 'Status not provided')}</small></details>
      </li>`).join('')}</ul>` : `<div class="predictions-unavailable"><strong>${escapeHtml(ml.label)}</strong><p>${escapeHtml(ml.detail)}</p></div>`}
    </section>
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
      <p class="muted">Selected model: Random Forest.</p>
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
        <figure><h4>Class Distribution</h4><img src="/docs/figures/sprint3/severity_distribution.svg" alt="DDInter class distribution" /><figcaption>Moderate interactions make up most labeled DDInter pairs, which creates a class-imbalanced prediction problem.</figcaption></figure>
        <figure><h4>Structure Coverage</h4><img src="/docs/figures/sprint3/pair_structure_coverage.svg" alt="Pair structure coverage" /><figcaption>Molecular descriptors are available for only part of the curated drug set.</figcaption></figure>
        <figure><h4>Graph Mapping Coverage</h4><img src="/docs/figures/sprint3/hetionet_mapping_coverage.svg" alt="Hetionet mapping coverage" /><figcaption>Only a subset of DDInter drugs map to Hetionet, so graph-derived features have explicit missingness.</figcaption></figure>
        <figure><h4>Feature Missingness</h4><img src="/docs/figures/sprint3/feature_missingness.svg" alt="Feature missingness" /><figcaption>Missing values are tracked by source rather than treated as evidence of absence.</figcaption></figure>
      </div>
    </section>`,
    final: `<section class="analysis-section" role="tabpanel">
      <h3>Final Selected Model</h3>
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
};

if (typeof document !== 'undefined') {
  init();
}
