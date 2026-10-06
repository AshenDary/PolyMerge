/**
 * PolyMerge Research Dashboard — Sprint 6
 * app.js  ·  Primary frontend controller
 *
 * API surface (canonical):
 *   GET  /api/diseases
 *   POST /api/candidate-sets/search
 *   GET  /api/candidate-sets/:queryId/explain?format=detailed
 *
 * Three evidence channels — NEVER combined into one score:
 *   Graph Evidence   (#1d6ae5)
 *   Deterministic Rules (#2e7d32 / #b91c1c)
 *   ML Predictions   (#7c3aed)
 */

/* ─────────────────────────────────────────────
   DOM refs
───────────────────────────────────────────── */
const diseaseSearch    = document.getElementById('disease-search');
const diseaseList      = document.getElementById('disease-list');
const selectedSummary  = document.getElementById('selected-summary');
const selectedCount    = document.getElementById('selected-count');
const clearBtn         = document.getElementById('clear-btn');
const analyzeBtn       = document.getElementById('analyze-btn');
const statusTag        = document.getElementById('status-tag');
const summaryCards     = document.getElementById('summary-cards');
const resultsContainer = document.getElementById('results');
const explainability   = document.getElementById('explainability');
const mlStatusLabel    = document.getElementById('ml-status-label');
const mlStatusNote     = document.getElementById('ml-status-note');

/* ─────────────────────────────────────────────
   State
───────────────────────────────────────────── */
const selectedDiseases = new Set();
let allDiseases        = [];
let lastQueryId        = null;
let lastCandidates     = [];

/* ─────────────────────────────────────────────
   Helpers — UI state
───────────────────────────────────────────── */
function showState(id) {
  ['state-empty', 'state-loading', 'state-error', 'state-graph-unavailable'].forEach((stateId) => {
    const el = document.getElementById(stateId);
    if (el) el.hidden = stateId !== id;
  });
}

function setStatusTag(text, modifier) {
  statusTag.textContent = text;
  statusTag.className   = 'status-tag' + (modifier ? ' ' + modifier : '');
}

function setWorkflowStep(stepId, state) {
  const el = document.getElementById(stepId);
  if (!el) return;
  el.className = 'step ' + state;
}

function setWorkflowRunning() {
  setWorkflowStep('step-graph',    'done');
  setWorkflowStep('step-mapping',  'done');
  setWorkflowStep('step-ranking',  'active');
  setWorkflowStep('step-rules',    'active');
  setWorkflowStep('step-setcover', 'active');
  setWorkflowStep('step-ml',       'pending');
  setWorkflowStep('step-explain',  'pending');
}

function setWorkflowComplete(mlApplied) {
  setWorkflowStep('step-graph',    'done');
  setWorkflowStep('step-mapping',  'done');
  setWorkflowStep('step-ranking',  'done');
  setWorkflowStep('step-rules',    'done');
  setWorkflowStep('step-setcover', 'done');
  setWorkflowStep('step-ml',       mlApplied ? 'done' : 'pending');
  setWorkflowStep('step-explain',  'done');
}

function setWorkflowError() {
  setWorkflowStep('step-ranking',  'error');
  setWorkflowStep('step-rules',    'error');
  setWorkflowStep('step-setcover', 'error');
  setWorkflowStep('step-ml',       'pending');
  setWorkflowStep('step-explain',  'pending');
}

function updateMlStatusNote(mlStatus) {
  const dot = mlStatusNote.querySelector('.status-dot');
  dot.className = 'status-dot';
  if (mlStatus === 'applied') {
    dot.classList.add('status-dot--green');
    mlStatusLabel.textContent = 'applied';
  } else if (mlStatus === 'unavailable') {
    dot.classList.add('status-dot--red');
    mlStatusLabel.textContent = 'unavailable';
  } else {
    dot.classList.add('status-dot--grey');
    mlStatusLabel.textContent = 'not applied (graph-only mode)';
  }
}

/* ─────────────────────────────────────────────
   Disease selection
───────────────────────────────────────────── */
function renderDiseases(diseases) {
  if (!diseases.length) {
    diseaseList.innerHTML = '<p class="muted skeleton-text">No diseases match your search.</p>';
    return;
  }
  diseaseList.innerHTML = diseases
    .map(
      (disease) => `
        <button
          class="disease-chip${selectedDiseases.has(disease.id) ? ' selected' : ''}"
          data-id="${escHtml(disease.id)}"
          aria-pressed="${selectedDiseases.has(disease.id)}"
          role="listitem"
        >
          ${escHtml(disease.name)}
        </button>
      `,
    )
    .join('');

  diseaseList.querySelectorAll('.disease-chip').forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.dataset.id;
      if (selectedDiseases.has(id)) {
        selectedDiseases.delete(id);
      } else {
        selectedDiseases.add(id);
      }
      renderDiseases(diseases);
      updateSelectionState();
    });
  });
}

function updateSelectionState() {
  const count = selectedDiseases.size;
  analyzeBtn.disabled = count === 0;
  selectedSummary.hidden = count === 0;
  selectedCount.textContent = count;
}

function getFilteredDiseases(query) {
  if (!query.trim()) return allDiseases;
  const q = query.trim().toLowerCase();
  return allDiseases.filter(
    (d) => d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q),
  );
}

/* ─────────────────────────────────────────────
   Summary cards (Screen 3 top)
───────────────────────────────────────────── */
function renderSummaryCards(response) {
  const sets        = response.candidateSets ?? [];
  const metadata    = response.metadata      ?? {};
  const accepted    = sets.filter((s) => s.status === 'accepted').length;
  const rejected    = sets.filter((s) => s.status === 'rejected').length;
  const topCandidate = sets.find((s) => s.status === 'accepted') ?? sets[0] ?? {};
  const coverage    = topCandidate.coverage ?? 0;
  const diseases    = response.diseases ?? [];

  const cards = [
    { label: 'Diseases Searched', value: diseases.length, highlight: false },
    { label: 'Candidate Sets',    value: sets.length,     highlight: false },
    { label: 'Accepted',          value: accepted,        highlight: true },
    { label: 'Rejected',          value: rejected,        highlight: false },
    { label: 'Best KG Coverage',  value: `${(coverage * 100).toFixed(0)}%`, highlight: coverage === 1 },
  ];

  summaryCards.innerHTML = cards
    .map(
      (c) => `
        <div class="card${c.highlight ? ' highlight' : ''}">
          <div class="label">${escHtml(String(c.label))}</div>
          <div class="value">${escHtml(String(c.value))}</div>
        </div>
      `,
    )
    .join('');

  summaryCards.hidden = false;
}

/* ─────────────────────────────────────────────
   Candidate result cards (Screen 3)
───────────────────────────────────────────── */
function renderResults(response) {
  const candidateSets = response.candidateSets ?? [];

  renderSummaryCards(response);

  if (!candidateSets.length) {
    resultsContainer.innerHTML = '<p class="muted">No candidates returned for the selected diseases.</p>';
    return;
  }

  resultsContainer.innerHTML = candidateSets
    .map((c) => buildCandidateCard(c, response))
    .join('');

  resultsContainer.querySelectorAll('[data-explain-candidate]').forEach((button) => {
    button.addEventListener('click', () => {
      const rank = Number(button.dataset.explainCandidate);
      const candidate = candidateSets.find((s) => s.rank === rank);
      if (candidate) renderExplainability(candidate, response);
    });
  });
}

function buildCandidateCard(c, response) {
  const isRejected   = c.status === 'rejected';
  const coverage     = c.coverage ?? 0;
  const drugNames    = c.drugNames ?? c.drugs ?? [];
  const drugIds      = c.drugs    ?? [];
  const mlStatus     = c.mlStatus ?? response.metadata?.mlStatus ?? 'not_applied';
  const dataStatus   = c.dataStatus ?? 'real_graph';

  const statusBadge = isRejected
    ? '<span class="rejected-badge">✗ Rejected</span>'
    : '<span class="accepted-badge">✓ Accepted</span>';

  const drugsHtml = drugNames
    .map((name, i) => {
      const id = drugIds[i] ?? '';
      return `<span class="drug-tag">${escHtml(name)}${id && id !== name ? ` <span class="drug-id-sub">${escHtml(id)}</span>` : ''}</span>`;
    })
    .join('');

  const coverageBar = `
    <div class="coverage-bar-wrap">
      <div class="coverage-bar-label">KG Treatment Coverage: ${(coverage * 100).toFixed(0)}%</div>
      <div class="coverage-bar-track">
        <div class="coverage-bar-fill" style="width:${(coverage * 100).toFixed(1)}%"></div>
      </div>
    </div>`;

  const metaHtml = `
    <div class="result-meta">
      <span class="meta-chip">Drugs: ${escHtml(String(c.drugCount ?? drugIds.length))}</span>
      <span class="meta-chip">Covered: ${escHtml(String((c.treatedDiseaseIds ?? []).length))} / ${escHtml(String(c.targetDiseaseCount ?? '?'))}</span>
      <span class="meta-chip">Data: ${escHtml(dataStatus)}</span>
    </div>`;

  const rejectionHtml = isRejected
    ? buildRejectionBox(c)
    : '';

  const mlRowHtml = buildMlStatusRow(mlStatus);

  return `
    <article class="result-card ${isRejected ? 'rejected' : 'accepted'}">
      <div class="result-header">
        <div class="result-header-left">
          <div class="rank-badge">${escHtml(String(c.rank))}</div>
          <h3>Candidate #${escHtml(String(c.rank))}</h3>
          ${statusBadge}
        </div>
        <div class="result-header-right">
          <button class="secondary" data-explain-candidate="${c.rank}">
            🔍 View Explainability
          </button>
        </div>
      </div>
      <div class="result-drugs">${drugsHtml}</div>
      ${metaHtml}
      ${coverageBar}
      ${rejectionHtml}
      ${mlRowHtml}
    </article>
  `;
}

function buildRejectionBox(c) {
  const reasons = c.rejectionReasons ?? (c.reason ? [c.reason] : []);
  const lines = reasons
    .map((r) => {
      const msg  = escHtml(r.message ?? r.type ?? 'Rule violation');
      const pair = (r.pair ?? []).map((d) => `<span class="drug-tag">${escHtml(d)}</span>`).join('');
      const stage = r.stage ? `<span class="rule-stage"> · ${escHtml(r.stage)}</span>` : '';
      return `<div><strong>✗ ${msg}</strong>${stage}${pair ? `<div class="rejection-pair">${pair}</div>` : ''}</div>`;
    })
    .join('');
  return `<div class="rejection-box">${lines || '<p>No specific reason provided.</p>'}</div>`;
}

function buildMlStatusRow(mlStatus) {
  if (mlStatus === 'applied') return '';   // rendered in explainability only
  const msg =
    mlStatus === 'unavailable'
      ? '🧠 ML DDI prediction unavailable — graph evidence and safety rules remain active.'
      : '🧠 ML DDI prediction not applied in this build — graph-only mode.';
  return `<div class="ml-not-applied-row">${escHtml(msg)}</div>`;
}

/* ─────────────────────────────────────────────
   Explainability — three-channel render (Screen 4)
───────────────────────────────────────────── */
function renderExplainability(candidate, response) {
  const isRejected = candidate.status === 'rejected';
  const mlStatus   = candidate.mlStatus ?? response.metadata?.mlStatus ?? 'not_applied';
  const drugNames  = candidate.drugNames ?? candidate.drugs ?? [];
  const drugIds    = candidate.drugs ?? [];

  const headerHtml = buildExplainHeader(candidate, drugNames, drugIds, isRejected);
  const graphHtml  = buildGraphSection(candidate, response);
  const rulesHtml  = buildRulesSection(candidate, isRejected);
  const mlHtml     = buildMlSection(candidate, mlStatus);

  const overallDisclaimer = `
    <div class="candidate-disclaimer">
      <strong>Research Use Only:</strong>
      Graph coverage measures knowledge-graph representation, not clinical efficacy.
      Deterministic rules are hard-coded safety checks, not a comprehensive drug interaction database.
      ML predictions are statistical estimates, not clinical validation.
      All evidence channels require expert review.
    </div>`;

  const html = `
    <div class="candidate-explanation candidate-${isRejected ? 'rejected' : 'accepted'}">
      ${headerHtml}
      <div class="evidence-sections">
        ${graphHtml}
        ${rulesHtml}
        ${mlHtml}
      </div>
      ${overallDisclaimer}
    </div>`;

  explainability.innerHTML = html;
  explainability.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildExplainHeader(candidate, drugNames, drugIds, isRejected) {
  const statusBadge = isRejected
    ? '<span class="rejected-badge">✗ Rejected</span>'
    : '<span class="accepted-badge">✓ Accepted</span>';

  const drugsHtml = drugNames
    .map((name, i) => {
      const id = drugIds[i] ?? '';
      return `<span class="drug-chip-explain">${escHtml(name)}${id && id !== name ? ` (${escHtml(id)})` : ''}</span>`;
    })
    .join('');

  return `
    <div class="candidate-header">
      <div>
        <h3>
          <span class="rank-badge">${escHtml(String(candidate.rank))}</span>
          Candidate #${escHtml(String(candidate.rank))}
          ${statusBadge}
        </h3>
        <div class="drug-list-explain">${drugsHtml}</div>
      </div>
    </div>`;
}

/* ── Graph Evidence channel ── */
function buildGraphSection(candidate, response) {
  const graphEvidence = candidate.graphEvidence ?? {};
  const paths         = graphEvidence.paths ?? [];
  const source        = graphEvidence.source ?? 'Hetionet';
  const graphVersion  = graphEvidence.graphVersion ?? response.metadata?.graph ?? 'Hetionet v1.0';
  const coverage      = candidate.coverage ?? 0;
  const treated       = (candidate.treatedDiseaseIds ?? []).length;
  const uncovered     = (candidate.uncoveredDiseaseIds ?? []).length;
  const dataStatus    = candidate.dataStatus ?? 'real_graph';

  const metricsHtml = `
    <div class="graph-metrics">
      <div class="graph-metric-item">
        <div class="g-label">KG Coverage</div>
        <div class="g-value">${(coverage * 100).toFixed(0)}%</div>
      </div>
      <div class="graph-metric-item">
        <div class="g-label">Treated</div>
        <div class="g-value">${treated}</div>
      </div>
      <div class="graph-metric-item">
        <div class="g-label">Uncovered</div>
        <div class="g-value">${uncovered}</div>
      </div>
      <div class="graph-metric-item">
        <div class="g-label">Data Status</div>
        <div class="g-value" style="font-size:.85rem">${escHtml(dataStatus)}</div>
      </div>
    </div>`;

  const pathsHtml = paths.length
    ? `<div class="graph-paths-list">${paths.map((p) => buildPathItem(p)).join('')}</div>`
    : `<div class="no-paths-note">No graph paths available for this candidate.</div>`;

  return `
    <div class="evidence-section section-graph">
      <div class="section-header">
        <span class="section-icon-text">🗄️</span>
        <h4>Graph Evidence</h4>
      </div>
      <div class="section-content">
        ${metricsHtml}
        <p style="font-size:.82rem;color:var(--muted);margin-bottom:10px">Evidence paths (${paths.length}):</p>
        ${pathsHtml}
      </div>
      <div class="section-disclaimer">
        Source: <strong>${escHtml(source)}</strong> · ${escHtml(graphVersion)} ·
        Coverage measures knowledge-graph representation, not clinical efficacy.
      </div>
    </div>`;
}

function buildPathItem(path) {
  const semType  = path.semanticType ?? 'unknown';
  const srcName  = path.sourceEntity?.name ?? path.sourceEntity?.id ?? '?';
  const relType  = path.relationship?.type ?? '?';
  const relMeta  = path.relationship?.metaedge ?? relType;
  const tgtName  = path.targetEntity?.name ?? path.targetEntity?.id ?? '?';
  const tgtKind  = path.targetEntity?.kind ?? '';
  const evType   = path.provenance?.evidenceType ?? 'known';
  const pathId   = (path.pathId ?? '').slice(0, 16);

  const badgeClass = semType === 'treatment'
    ? 'treatment'
    : semType === 'gene_context'
    ? 'gene_context'
    : 'side_effect_context';

  const badgeLabel = semType === 'treatment'
    ? 'CtD'
    : semType === 'gene_context'
    ? 'Gene'
    : 'Side Effect';

  return `
    <div class="path-item">
      <span class="path-type-badge ${badgeClass}">${escHtml(badgeLabel)}</span>
      <div>
        <div class="path-flow">
          <span class="path-node">${escHtml(srcName)}</span>
          <span class="path-arrow">→</span>
          <span class="path-rel">${escHtml(relMeta)}</span>
          <span class="path-arrow">→</span>
          <span class="path-node">${escHtml(tgtName)}</span>
          ${tgtKind ? `<span style="font-size:.72rem;color:var(--muted)">(${escHtml(tgtKind)})</span>` : ''}
        </div>
        <div class="path-provenance">
          evidenceType: ${escHtml(evType)}${pathId ? ` · id: …${escHtml(pathId)}` : ''}
        </div>
      </div>
    </div>`;
}

/* ── Deterministic Rules channel ── */
function buildRulesSection(candidate, isRejected) {
  const rejectionReasons = candidate.rejectionReasons ?? (candidate.reason ? [candidate.reason] : []);
  const channelClass = isRejected ? 'channel-rejected' : '';

  let contentHtml;
  if (isRejected && rejectionReasons.length) {
    contentHtml = `
      <div class="rules-list">
        ${rejectionReasons.map((r) => buildRuleItem(r, 'rejected')).join('')}
      </div>`;
  } else {
    contentHtml = `
      <div class="rules-list">
        <div class="rule-item rule-accepted">
          <div class="rule-header">
            <span class="rule-icon">✓</span>
            <strong>No contraindications detected</strong>
          </div>
          <p>All drug pairs in this candidate set passed hard-coded safety rule checks.</p>
          <div class="rule-source">Source: PolyMerge Safety Rules · Stage: pre_optimization</div>
        </div>
      </div>`;
  }

  return `
    <div class="evidence-section section-rules ${channelClass}">
      <div class="section-header">
        <span class="section-icon-text">🛡️</span>
        <h4>Deterministic Safety Rules</h4>
      </div>
      <div class="section-content">${contentHtml}</div>
      <div class="section-disclaimer">
        Hard-coded safety checks only. Not a comprehensive drug interaction database.
        Rejection is deterministic — not influenced by ML predictions.
      </div>
    </div>`;
}

function buildRuleItem(rule, forceStatus) {
  const status = forceStatus ?? (rule.status ?? 'rejected');
  const itemClass = `rule-item rule-${status}`;
  const icon = status === 'accepted' ? '✓' : '✗';
  const type = escHtml(rule.type ?? 'hard_contraindication');
  const msg  = escHtml(rule.message ?? 'Safety rule violation');
  const pair = (rule.pair ?? rule.affectedDrugs ?? [])
    .map((d) => `<span class="drug-tag">${escHtml(d)}</span>`)
    .join('');
  const source = rule.source ?? 'PolyMerge Safety Rules';
  const stage  = rule.stage ? ` · Stage: ${escHtml(rule.stage)}` : '';

  return `
    <div class="${itemClass}">
      <div class="rule-header">
        <span class="rule-icon">${icon}</span>
        <strong>${type}</strong>
      </div>
      <p>${msg}</p>
      ${pair ? `<div class="affected-pair">${pair}</div>` : ''}
      <div class="rule-source">Source: ${escHtml(source)}${stage}</div>
    </div>`;
}

/* ── ML Prediction channel ── */
function buildMlSection(candidate, mlStatus) {
  const predictions = candidate.predictions ?? [];

  let contentHtml;
  if (mlStatus === 'applied' && predictions.length) {
    contentHtml = `
      <div class="predictions-list">
        ${predictions.map((pred) => buildPredictionItem(pred)).join('')}
      </div>`;
  } else {
    const mlMsg =
      mlStatus === 'unavailable'
        ? 'ML DDI prediction service is currently unavailable. Graph evidence and safety rules remain active.'
        : 'ML DDI predictions are not applied in this build. The pipeline is running in graph-only mode.';
    contentHtml = `
      <div class="ml-unavailable-box">
        <p>🧠 ${escHtml(mlMsg)}</p>
        <small style="color:var(--muted)">Graph evidence and safety rules remain available.</small>
      </div>`;
  }

  return `
    <div class="evidence-section section-predictions">
      <div class="section-header">
        <span class="section-icon-text">🧠</span>
        <h4>ML Prediction</h4>
        ${mlStatus === 'applied' ? '' : `<span style="font-size:.78rem;color:var(--ch-ml);font-weight:600">${mlStatus === 'unavailable' ? '(unavailable)' : '(not applied)'}</span>`}
      </div>
      <div class="section-content">${contentHtml}</div>
      <div class="section-disclaimer">
        ML predictions are statistical estimates from research models — not clinical validation.
        Do not use predicted severity as a clinical safety determination.
        ${mlStatus === 'applied' ? `Model: ${escHtml(candidate.predictions?.[0]?.model?.name ?? 'N/A')}` : ''}
      </div>
    </div>`;
}

function buildPredictionItem(pred) {
  const drugs    = pred.drugs ?? [];
  const severity = pred.severity ?? pred.predictedSeverity ?? 'Unknown';
  const probs    = pred.probabilities ?? pred.severityProbabilities ?? {};
  const model    = pred.model ?? {};
  const visualStyle = pred.visualStyle ?? severity.toLowerCase();

  const probBars = Object.keys(probs).length
    ? `
      <div class="prob-bars">
        ${Object.entries(probs)
          .map(
            ([label, val]) => `
              <div class="prob-bar">
                <span class="prob-label">${escHtml(label)}:</span>
                <div class="prob-track">
                  <div class="prob-fill" style="width:${(Number(val) * 100).toFixed(1)}%"></div>
                </div>
                <span class="prob-value">${(Number(val) * 100).toFixed(0)}%</span>
              </div>`,
          )
          .join('')}
      </div>`
    : '';

  return `
    <div class="prediction-item">
      <div class="prediction-header">
        <strong>${drugs.map(escHtml).join(' ↔ ')}</strong>
        <span class="severity-badge severity-${escHtml(severity.toLowerCase())}">${escHtml(severity)}</span>
      </div>
      ${probBars}
      <div class="prediction-meta">
        Model: ${escHtml(model.name ?? 'N/A')} ${escHtml(model.version ?? '')}
        ${pred.confidence != null ? ` · Confidence: ${(Number(pred.confidence) * 100).toFixed(0)}%` : ''}
      </div>
    </div>`;
}

/* ─────────────────────────────────────────────
   API calls
───────────────────────────────────────────── */
async function loadDiseases() {
  try {
    const response = await fetch('/api/diseases');
    const data     = await response.json();

    if (!response.ok) {
      diseaseList.innerHTML = `<p class="muted">Unable to load disease catalog: ${escHtml(data.error ?? 'unknown error')}</p>`;
      setStatusTag('Catalog error', 'error');
      return;
    }

    allDiseases = data.diseases ?? [];
    renderDiseases(allDiseases);
  } catch (err) {
    diseaseList.innerHTML = `<p class="muted">Cannot reach server: ${escHtml(err.message)}</p>`;
    setStatusTag('Offline', 'error');
  }
}

async function analyzeCombination() {
  if (!selectedDiseases.size) return;

  // Reset UI
  showState('state-loading');
  setStatusTag('Running…', 'running');
  setWorkflowRunning();
  summaryCards.hidden = true;
  resultsContainer.innerHTML = '';
  explainability.innerHTML = '<div class="state-card state-empty"><p class="muted">Running analysis…</p></div>';
  lastQueryId  = null;
  lastCandidates = [];
  analyzeBtn.disabled = true;

  try {
    const res = await fetch('/api/candidate-sets/search', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ diseaseIds: Array.from(selectedDiseases) }),
    });

    const data = await res.json();

    // Graph unavailable (503)
    if (res.status === 503) {
      showState('state-graph-unavailable');
      setStatusTag('Graph offline', 'error');
      setWorkflowError();
      analyzeBtn.disabled = false;
      return;
    }

    // Other HTTP error
    if (!res.ok) {
      document.getElementById('error-message').textContent =
        data.detail?.error ?? data.error ?? `Server error (${res.status}).`;
      showState('state-error');
      setStatusTag('Error', 'error');
      setWorkflowError();
      analyzeBtn.disabled = false;
      return;
    }

    // Success
    const mlStatus = data.metadata?.mlStatus ?? 'not_applied';
    lastQueryId    = data.queryId;
    lastCandidates = data.candidateSets ?? [];

    showState(null);          // hide all state cards
    setStatusTag('Complete', 'complete');
    setWorkflowComplete(mlStatus === 'applied');
    updateMlStatusNote(mlStatus);
    renderResults(data);

    // Reset explainability prompt
    explainability.innerHTML = `
      <div class="state-card state-empty">
        <p class="muted">Click <strong>View Explainability</strong> on any candidate above to inspect its three evidence channels.</p>
      </div>`;

  } catch (err) {
    document.getElementById('error-message').textContent =
      `Unable to reach the backend: ${escHtml(err.message)}`;
    showState('state-error');
    setStatusTag('Error', 'error');
    setWorkflowError();
  } finally {
    analyzeBtn.disabled = selectedDiseases.size === 0;
  }
}

/* ─────────────────────────────────────────────
   Utility
───────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ─────────────────────────────────────────────
   Event wiring
───────────────────────────────────────────── */
analyzeBtn.addEventListener('click', analyzeCombination);

clearBtn.addEventListener('click', () => {
  selectedDiseases.clear();
  renderDiseases(getFilteredDiseases(diseaseSearch.value));
  updateSelectionState();
});

diseaseSearch.addEventListener('input', () => {
  renderDiseases(getFilteredDiseases(diseaseSearch.value));
});

/* ─────────────────────────────────────────────
   Init
───────────────────────────────────────────── */
showState('state-empty');
loadDiseases();
