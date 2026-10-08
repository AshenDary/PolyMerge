const diseaseList = document.getElementById('disease-list');
const analyzeBtn = document.getElementById('analyze-btn');
const resultsContainer = document.getElementById('results');
const summaryCards = document.getElementById('summary-cards');
const explainability = document.getElementById('explainability');
const catalogTag = document.getElementById('catalog-tag');
const catalogMessage = document.getElementById('catalog-message');
const diseaseSearch = document.getElementById('disease-search');
const selectionCount = document.getElementById('selection-count');

const selectedDiseases = new Set();
let availableDiseases = [];
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));
const percent = (value) => Number.isFinite(value) ? `${Math.round(value * 100)}%` : 'Not provided';

function setMessage(container, message, kind = 'info') {
  container.innerHTML = `<p class="state-message state-${kind}" role="status">${escapeHtml(message)}</p>`;
}

function renderDiseases(diseases) {
  const query = diseaseSearch.value.trim().toLocaleLowerCase();
  diseases = diseases.filter((disease) => `${disease.name} ${disease.id}`.toLocaleLowerCase().includes(query));
  if (!diseases.length) {
    setMessage(diseaseList, query ? 'No diseases match this search.' : 'No diseases are available from the graph service.', 'warning');
    return;
  }
  diseaseList.innerHTML = diseases.map((disease) => `
    <button type="button" class="disease-chip ${selectedDiseases.has(disease.id) ? 'selected' : ''}"
      data-id="${escapeHtml(disease.id)}" aria-pressed="${selectedDiseases.has(disease.id)}">
      <span>${escapeHtml(disease.name)}</span><small>${escapeHtml(disease.id)}</small>
    </button>`).join('');
  diseaseList.querySelectorAll('.disease-chip').forEach((button) => button.addEventListener('click', () => {
    const id = button.dataset.id;
    if (selectedDiseases.has(id)) selectedDiseases.delete(id);
    else selectedDiseases.add(id);
    selectionCount.textContent = `${selectedDiseases.size} disease${selectedDiseases.size === 1 ? '' : 's'} selected`;
    analyzeBtn.disabled = selectedDiseases.size === 0;
    renderDiseases(diseases);
  }));
}

function renderSummary(data, candidates) {
  const accepted = candidates.filter((candidate) => candidate.status === 'accepted').length;
  const rejected = candidates.filter((candidate) => candidate.status === 'rejected').length;
  const ml = data.metadata?.mlStatus === 'applied' ? 'Applied' : 'Not applied';
  const cards = [
    ['Candidate sets', candidates.length], ['Accepted', accepted], ['Rejected', rejected],
    ['ML status', ml], ['Graph status', data.metadata?.dataStatus ?? 'Not provided'],
  ];
  summaryCards.innerHTML = cards.map(([label, value]) => `
    <div class="card"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value)}</div></div>`).join('');
}

function renderResults(data) {
  const candidates = data.candidateSets ?? [];
  renderSummary(data, candidates);
  if (data.metadata?.dataStatus === 'graph_unavailable') {
    setMessage(resultsContainer, data.metadata.warning || 'Graph evidence is unavailable; no candidate sets were returned.', 'warning');
    return;
  }
  if (!candidates.length) {
    setMessage(resultsContainer, 'No candidate sets were returned for this selection.', 'empty');
    return;
  }

  resultsContainer.innerHTML = candidates.map((candidate, index) => {
    const names = candidate.drugNames ?? [];
    const drugs = (candidate.drugs ?? []).map((id, drugIndex) => `
      <li class="drug-item"><strong>${escapeHtml(names[drugIndex] ?? id)}</strong><code>${escapeHtml(id)}</code></li>`).join('');
    const coveredIds = candidate.treatedDiseaseIds ?? [];
    const uncoveredIds = candidate.uncoveredDiseaseIds ?? [];
    const diseaseLabels = new Map((data.diseases ?? []).map((disease) => [disease.id, disease.name]));
    const rejectionReasons = (candidate.rejectionReasons ?? []).map((reason) => `
      <li><strong>${escapeHtml(reason.type ?? 'Rule')}</strong>: ${escapeHtml(reason.message ?? 'Reason not provided')}
      ${reason.pair?.length ? `<small>Pair: ${reason.pair.map(escapeHtml).join(' + ')}</small>` : ''}</li>`).join('');
    const ml = candidate.mlStatus === 'applied' ? 'Research prediction applied' : 'Not applied or unavailable';
    const pairPredictions = (candidate.mlPrediction?.pairs ?? []).map((pair) => `
      <span>${escapeHtml(pair.predictedSeverity ?? pair.predictedClass ?? 'Prediction class not provided')} · ${escapeHtml(pair.model?.version ?? pair.model?.name ?? 'Model version not provided')}</span>`).join('');
    return `<article class="result-card" id="candidate-${index}">
      <div class="result-header"><div><p class="eyebrow">Rank ${escapeHtml(candidate.rank ?? 'Not provided')}</p>
      <h3>Candidate set</h3></div><span class="status-badge status-${candidate.status === 'rejected' ? 'rejected' : 'accepted'}">${escapeHtml(candidate.status ?? 'Status not provided')}</span></div>
      <ul class="drug-list">${drugs}</ul>
      <div class="result-meta"><span>Disease coverage: ${coveredIds.length} / ${selectedDiseases.size || (data.diseases ?? []).length} (${percent(candidate.coverage)})</span><span>Covered diseases: ${coveredIds.map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None provided'}</span>
      <span>Uncovered: ${uncoveredIds.map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None'}</span><span>ML: ${ml}</span></div>
      ${rejectionReasons ? `<div class="rejection-reasons"><h4>Deterministic rejection reasons</h4><ul>${rejectionReasons}</ul></div>` : ''}
      ${pairPredictions ? `<div class="prediction-summary"><h4>Research ML prediction</h4>${pairPredictions}</div>` : ''}
      <button type="button" class="secondary explanation-button" data-candidate-id="${escapeHtml(candidate.candidateSetId)}">View explanation</button>
    </article>`;
  }).join('');

  resultsContainer.querySelectorAll('[data-candidate-id]').forEach((button) => button.addEventListener('click', async () => {
    await window.PolyMergeExplainability?.loadExplainability(data.queryId, 'detailed', button.dataset.candidateId);
    window.location.hash = 'explainability-panel';
  }));
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;
  const status = response.status === 401 || response.status === 403 ? 'Unauthorized' : response.status === 409 ? 'Conflict' : `System error (${response.status})`;
  throw new Error(`${status}: ${data.error ?? data.detail ?? 'The request could not be completed.'}`);
}

async function loadDiseases() {
  catalogTag.textContent = 'Loading catalog';
  catalogMessage.hidden = false;
  catalogMessage.className = 'catalog-message loading-message';
  catalogMessage.innerHTML = '<strong>Loading disease catalog</strong><p>Connecting to the knowledge graph service…</p>';
  diseaseList.replaceChildren();
  try {
    const data = await readResponse(await fetch('/api/diseases'));
    availableDiseases = data.diseases ?? [];
    catalogMessage.hidden = true;
    catalogTag.textContent = 'Catalog ready';
    renderDiseases(availableDiseases);
  } catch (error) {
    catalogTag.textContent = 'Catalog unavailable';
    catalogMessage.className = 'catalog-message unavailable-message';
    catalogMessage.innerHTML = `<div><strong>Disease catalog unavailable</strong><p>The knowledge graph service is unavailable, so the disease list could not load.</p><small>Candidate search will be available when the graph service responds.</small></div><button type="button" id="retry-catalog" class="retry-button">Try again</button>`;
    catalogMessage.hidden = false;
    diseaseList.replaceChildren();
    document.getElementById('retry-catalog').addEventListener('click', loadDiseases);
  }
}

async function analyzeCombination() {
  if (!selectedDiseases.size) return;
  analyzeBtn.disabled = true;
  catalogTag.textContent = 'Search in progress';
  setMessage(resultsContainer, 'Searching graph evidence and evaluating candidate sets…');
  setMessage(explainability, 'Choose a candidate after results load to inspect its explanations.');
  summaryCards.replaceChildren();
  try {
    const response = await fetch('/api/candidate-sets/search', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseaseIds: Array.from(selectedDiseases) }),
    });
    const data = await readResponse(response);
    renderResults(data);
    catalogTag.textContent = data.metadata?.dataStatus === 'graph_unavailable' ? 'Graph unavailable' : 'Search complete';
    document.getElementById('ml-tag').textContent = `● ML predictions: ${data.metadata?.mlStatus === 'applied' ? 'applied' : 'not applied'}`;
  } catch (error) {
    setMessage(resultsContainer, error.message, 'error');
    catalogTag.textContent = error.message.startsWith('Unauthorized') ? 'Unauthorized' : error.message.startsWith('Conflict') ? 'Conflict' : 'System error';
  } finally {
    analyzeBtn.disabled = selectedDiseases.size === 0;
  }
}

analyzeBtn.addEventListener('click', analyzeCombination);
diseaseSearch.addEventListener('input', () => renderDiseases(availableDiseases));
const sidebar = document.querySelector('.sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const viewIds = ['disease-selection', 'workflow', 'candidate-sets', 'explainability-panel', 'model-comparison', 'research-note'];
const comparisonContent = document.getElementById('model-comparison-content');
let comparisonLoaded = false;

async function loadModelComparison() {
  comparisonContent.innerHTML = '<p class="state-message" role="status">Loading the preserved model comparison…</p>';
  try {
    const data = await readResponse(await fetch('/api/model-comparison'));
    const renderTable = (rows) => {
      if (!rows?.length) return '<p class="muted">No comparison data is available.</p>';
      const columns = Object.keys(rows[0]);
      return `<div class="comparison-table-wrap"><table class="comparison-table"><thead><tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(row[column])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    };
    comparisonContent.innerHTML = `<p class="comparison-disclaimer">${escapeHtml(data.disclaimer ?? 'Research classification results only; not clinical validation.')}</p>
      <h3>Validation results</h3>${renderTable(data.rows)}<p class="muted">Source: ${escapeHtml(data.source ?? 'Sprint 4 model-comparison report')}</p>
      <h3>Fixed model parameters</h3>${renderTable(data.parameters)}
      <details class="comparison-details"><summary>Experiment and limitations</summary><pre>${escapeHtml([data.experiment, data.limitations].filter(Boolean).join('\n\n'))}</pre></details>`;
    comparisonLoaded = true;
  } catch (error) {
    comparisonContent.innerHTML = `<p class="state-message state-error" role="alert">Model comparison unavailable: ${escapeHtml(error.message)}</p><button type="button" class="secondary" id="retry-model-comparison">Try again</button>`;
    document.getElementById('retry-model-comparison').addEventListener('click', loadModelComparison);
  }
}

function showView() {
  const requested = window.location.hash.slice(1) || 'disease-selection';
  const view = viewIds.includes(requested) ? requested : 'disease-selection';
  document.body.dataset.view = view;
  sidebar.querySelectorAll('nav a').forEach((link) => {
    if (link.hash === `#${view}`) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  if (view === 'model-comparison' && !comparisonLoaded) loadModelComparison();
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', showView);
showView();
sidebarToggle.addEventListener('click', () => {
  const collapsed = document.body.classList.toggle('sidebar-collapsed');
  sidebarToggle.setAttribute('aria-expanded', String(!collapsed));
  sidebarToggle.setAttribute('aria-label', collapsed ? 'Expand navigation' : 'Collapse navigation');
});
loadDiseases();
