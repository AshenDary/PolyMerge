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
const mlStatusDot      = document.getElementById('ml-status-dot');

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
  statusTag.className   = 'status-pill' + (modifier ? ' ' + modifier : '');
}

function setWorkflowStep(stepId, state) {
  const el = document.getElementById(stepId);
  if (!el) return;
  el.className = 'pipe-step ' + state;
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
  if (!mlStatusDot) return;
  mlStatusDot.className = 'status-dot';
  if (mlStatus === 'applied') {
    mlStatusDot.classList.add('status-dot--green');
    mlStatusLabel.textContent = 'ML predictions: applied';
  } else if (mlStatus === 'unavailable') {
    mlStatusDot.classList.add('status-dot--red');
    mlStatusLabel.textContent = 'ML predictions: unavailable';
  } else {
    mlStatusDot.classList.add('status-dot--grey');
    mlStatusLabel.textContent = 'ML predictions: not applied';
  }
}


/* ─────────────────────────────────────────────
   Disease selection
───────────────────────────────────────────── */
function renderDiseases(diseases) {
  if (!diseases.length) {
    const message = allDiseases.length
      ? 'No diseases match this search. Try a different name or ID.'
      : 'The disease catalog is empty.';
    diseaseList.innerHTML = `<p class="catalog-empty">${message}</p>`;
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
        <div class="stat-card${c.highlight ? ' stat-accent' : ''}">
          <div class="s-label">${escHtml(String(c.label))}</div>
          <div class="s-value">${escHtml(String(c.value))}</div>
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
    resultsContainer.innerHTML = '<p class="results-empty">No candidate sets were found for these diseases. Try changing your selection and search again.</p>';
    return;
  }

  resultsContainer.innerHTML = candidateSets
    .map((c) => buildCandidateCard(c, response))
    .join('');

  resultsContainer.querySelectorAll('[data-explain-candidate]').forEach((button) => {
    button.addEventListener('click', () => {
      const rank = Number(button.dataset.explainCandidate);
      const candidate = candidateSets.find((s) => s.rank === rank);
      if (candidate) loadExplainability(candidate, response);
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

  const mlRowHtml = buildMlStatusRow(mlStatus, c);

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
            🔍 View evidence
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

function buildMlStatusRow(mlStatus, candidate) {
  if (mlStatus === 'applied') {
    const predictions = candidate.predictions ?? [];
    const summary = predictions.length
      ? predictions.map((prediction) => {
          const severity = prediction.severity ?? prediction.predictedSeverity ?? 'No class returned';
          const pair = prediction.drugs ?? prediction.drugPair ?? [];
          const model = prediction.model ?? {};
          const modelName = model.name ?? prediction.modelName;
          const version = model.version ?? prediction.modelVersion;
          return `<div class="ml-result-line"><strong>${escHtml(pair.join(' ↔ ') || 'Drug pair')}</strong><span class="severity-badge severity-${escHtml(String(severity).toLowerCase())}">${escHtml(severity)}</span>${modelName ? `<small>${escHtml(modelName)}${version ? ` · ${escHtml(version)}` : ''}</small>` : ''}</div>`;
        }).join('')
      : '<span>ML applied; no pairwise severity details returned.</span>';
    return `<div class="ml-applied-row"><strong>ML prediction</strong><div>${summary}</div><small>Research prediction only; not a clinical safety determination.</small></div>`;
  }
  const msg =
    mlStatus === 'unavailable'
      ? '🧠 ML DDI prediction unavailable — graph evidence and safety rules remain active.'
      : '🧠 ML predictions were not applied to this search. Graph evidence and deterministic rules remain available.';
  return `<div class="ml-not-applied-row">${escHtml(msg)}</div>`;
}

/* ─────────────────────────────────────────────
   Explainability — three-channel render (Screen 4)
───────────────────────────────────────────── */
async function loadExplainability(candidate, response) {
  explainability.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (!lastQueryId) {
    renderExplainability(candidate, response);
    return;
  }
  explainability.setAttribute('aria-busy', 'true');
  explainability.innerHTML = '<div class="state-box" role="status"><div class="loader-ring" aria-hidden="true"></div><p>Loading evidence channels…</p></div>';
  try {
    const data = await window.PolyMergeExplainability.fetchStructured(lastQueryId);
    const structured = (data.candidateSets ?? []).find((item) => item.rank === candidate.rank);
    if (!structured) throw new Error('No explanation was returned for this candidate.');
    renderExplainability(candidate, response, structured);
  } catch (error) {
    explainability.innerHTML = `<div class="state-box state-error" role="alert"><p>Unable to load explainability: ${escHtml(error.message)}</p></div>`;
  } finally {
    explainability.removeAttribute('aria-busy');
  }
}

function renderExplainability(candidate, response, structured = null) {
  const evidenceCandidate = structured ? {
    ...candidate,
    ...structured,
    // The explainability route supplies the channel structure; retain concrete
    // pairwise outputs from the search response when the structured view is a stub.
    predictions: candidate.predictions?.length ? candidate.predictions : structured.predictions,
  } : candidate;
  const isRejected = candidate.status === 'rejected';
  const mlStatus   = evidenceCandidate.mlStatus ?? response.metadata?.mlStatus ?? 'not_applied';
  const drugNames  = candidate.drugNames ?? candidate.drugs ?? [];
  const drugIds    = candidate.drugs ?? [];

  const headerHtml = buildExplainHeader(evidenceCandidate, drugNames, drugIds, isRejected);
  const graphHtml  = buildGraphSection(evidenceCandidate, response);
  const rulesHtml  = buildRulesSection(evidenceCandidate, isRejected);
  const mlHtml     = buildMlSection(evidenceCandidate, mlStatus);

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
  const paths = normalizeGraphPaths(graphEvidence);
  const source        = graphEvidence.source ?? graphEvidence.provenance?.source ?? 'Hetionet';
  const graphVersion  = graphEvidence.graphVersion ?? graphEvidence.provenance?.version ?? response.metadata?.graph ?? 'Hetionet v1.0';
  const coverage      = candidate.coverage ?? 0;
  const treated       = (graphEvidence.treatedDiseaseIds ?? candidate.treatedDiseaseIds ?? []).length;
  const uncovered     = (graphEvidence.uncoveredDiseaseIds ?? candidate.uncoveredDiseaseIds ?? []).length;
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

function normalizeGraphPaths(evidence) {
  const paths = [...(evidence.paths ?? [])];
  for (const path of evidence.treatmentPaths ?? []) paths.push({
    semanticType: 'treatment', pathId: path.pathId,
    sourceEntity: { name: path.drugName ?? path.drugId },
    relationship: { type: path.relationship ?? 'CtD', metaedge: 'CtD' },
    targetEntity: { name: path.diseaseName ?? path.diseaseId, kind: 'Disease' },
    provenance: { source: path.source, evidenceType: path.evidenceType },
  });
  for (const path of evidence.geneContext ?? []) paths.push({
    semanticType: 'gene_context', pathId: path.pathId,
    sourceEntity: { name: path.drugName ?? path.drugId },
    relationship: { type: path.relationship, metaedge: path.relationship },
    targetEntity: { name: path.geneName ?? path.geneId, kind: 'Gene' },
    provenance: { source: path.source, evidenceType: path.evidenceType },
  });
  for (const path of evidence.sideEffectContext ?? []) paths.push({
    semanticType: 'side_effect_context', pathId: path.pathId,
    sourceEntity: { name: path.drugName ?? path.drugId },
    relationship: { type: path.relationship, metaedge: path.relationship },
    targetEntity: { name: path.sideEffectName ?? path.sideEffectId, kind: 'Side Effect' },
    provenance: { source: path.source, evidenceType: path.evidenceType },
  });
  return paths.filter((path) => {
    const rel = String(path.relationship?.metaedge ?? path.relationship?.type ?? '');
    return ['CtD', 'treats', 'CbG', 'CuG', 'CdG', 'CcSE'].includes(rel);
  });
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
  const rejectionReasons = candidate.rejectionReasons ?? (candidate.rules ?? []).filter((rule) => rule.status === 'rejected').map((rule) => ({
    ...rule, pair: rule.pair ?? rule.affectedDrugs,
  })) ?? (candidate.reason ? [candidate.reason] : []);
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
  } else if (mlStatus === 'applied') {
    contentHtml = '<div class="ml-unavailable-box"><p>The service reported ML as applied but returned no pairwise predictions.</p></div>';
  } else {
    const mlMsg =
      mlStatus === 'unavailable'
        ? 'ML DDI prediction service is currently unavailable. Graph evidence and safety rules remain active.'
        : 'ML predictions were not applied to this search. Graph evidence and deterministic rules remain available.';
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
        ${mlStatus === 'applied' ? `Model: ${escHtml(candidate.predictions?.[0]?.model?.name ?? candidate.predictions?.[0]?.modelName ?? 'Not reported')} · Version: ${escHtml(candidate.predictions?.[0]?.model?.version ?? candidate.predictions?.[0]?.modelVersion ?? 'Not reported')}` : ''}
      </div>
    </div>`;
}

function buildPredictionItem(pred) {
  const drugs    = pred.drugs ?? pred.drugPair ?? [];
  const rawSeverity = pred.severity ?? pred.predictedSeverity;
  const severity = rawSeverity ?? 'No class returned';
  const probs    = pred.probabilities ?? pred.severityProbabilities ?? {};
  const model    = pred.model ?? { name: pred.modelName, version: pred.modelVersion };
  const severityClass = ['major', 'moderate', 'minor'].includes(String(severity).toLowerCase())
    ? String(severity).toLowerCase()
    : 'unknown';
  const knownProbabilities = Object.entries(probs).filter(([, value]) => value != null && Number.isFinite(Number(value)));

  const probBars = knownProbabilities.length
    ? `
      <div class="prob-bars">
        ${knownProbabilities
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
        <span class="severity-badge severity-${severityClass}">${escHtml(severity)}</span>
      </div>
      ${probBars}
      <div class="prediction-meta">
        Model: ${escHtml(model.name ?? 'N/A')} ${escHtml(model.version ?? '')}
        ${pred.datasetVersion ? ` · Dataset: ${escHtml(pred.datasetVersion)}` : ''}
        ${pred.confidence != null ? ` · Confidence: ${(Number(pred.confidence) * 100).toFixed(0)}%` : ''}
      </div>
    </div>`;
}

/* ─────────────────────────────────────────────
   API calls
───────────────────────────────────────────── */
async function loadDiseases() {
  setStatusTag('Loading catalog', 'running');
  diseaseSearch.disabled = true;
  diseaseList.innerHTML = '<div class="chip-skeleton"></div><div class="chip-skeleton" style="width:100px"></div><div class="chip-skeleton" style="width:130px"></div>';
  try {
    const response = await fetch('/api/diseases');
    const data     = await response.json();

    if (!response.ok) {
      renderCatalogError(response.status === 503
        ? 'The knowledge graph service is unavailable, so the disease list could not load.'
        : 'The disease list could not load. Check the service and try again.');
      return;
    }

    allDiseases = data.diseases ?? [];
    diseaseSearch.disabled = false;
    renderDiseases(allDiseases);
    setStatusTag('Catalog ready', 'complete');
  } catch (err) {
    renderCatalogError('The dashboard could not connect to the disease catalog. Check the service and try again.');
  }
}

function renderCatalogError(message) {
  diseaseList.innerHTML = '<div class="catalog-error" role="alert">' +
    '<div class="catalog-error-copy"><strong>Disease catalog unavailable</strong>' +
    '<p>' + escHtml(message) + '</p>' +
    '<small>Candidate search will be available when the graph service responds.</small></div>' +
    '<button class="retry-btn" id="retry-diseases" type="button">Try again</button></div>';
  setStatusTag('Catalog unavailable', 'error');
  document.getElementById('retry-diseases')?.addEventListener('click', loadDiseases);
}

async function analyzeCombination() {
  if (!selectedDiseases.size) return;

  // Reset UI
  document.getElementById('screen-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  showState('state-loading');
  setStatusTag('Running…', 'running');
  setWorkflowRunning();
  summaryCards.hidden = true;
  resultsContainer.innerHTML = '';
  explainability.innerHTML = '<div class="state-box" role="status"><div class="loader-ring" aria-hidden="true"></div><p>Preparing graph evidence and channel summaries…</p></div>';
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

    // The canonical candidate-set route can return an explicit empty fallback
    // with HTTP 200 when its graph dependency is unavailable.
    if (data.metadata?.dataStatus === 'graph_unavailable') {
      showState('state-graph-unavailable');
      setStatusTag('Graph offline', 'error');
      updateMlStatusNote(data.metadata.mlStatus ?? 'unavailable');
      setWorkflowError();
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
    analyzeBtn.disabled = false;

    // Reset explainability prompt
    explainability.innerHTML = `
      <div class="state-box">
        <p class="muted">Choose <strong>View evidence</strong> on a candidate to inspect graph evidence, safety rules, and any ML predictions.</p>
      </div>`;

  } catch (err) {
    document.getElementById('error-message').textContent =
      `Unable to reach the backend: ${escHtml(err.message)}`;
    showState('state-error');
    setStatusTag('Error', 'error');
    setWorkflowError();
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
document.getElementById('retry-graph-search')?.addEventListener('click', analyzeCombination);

clearBtn.addEventListener('click', () => {
  selectedDiseases.clear();
  renderDiseases(getFilteredDiseases(diseaseSearch.value));
  updateSelectionState();
});

diseaseSearch.addEventListener('input', () => {
  renderDiseases(getFilteredDiseases(diseaseSearch.value));
});

document.querySelectorAll('.nav-item[data-panel]').forEach((button) => {
  button.addEventListener('click', () => {
    const targetId = {
      disease: 'screen-disease',
      workflow: 'screen-workflow',
      results: 'screen-results',
      explain: 'screen-explainability',
    }[button.dataset.panel];
    const target = targetId && document.getElementById(targetId);
    if (!target) return;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.querySelectorAll('.nav-item[data-panel]').forEach((item) => {
      item.classList.toggle('active', item === button);
      if (item === button) item.setAttribute('aria-current', 'location');
      else item.removeAttribute('aria-current');
    });
  });
});

const sidebarToggle = document.querySelector('.sidebar-toggle');
function setSidebarExpanded(expanded) {
  const shouldExpand = expanded && window.innerWidth > 700;
  document.body.classList.toggle('sidebar-expanded', shouldExpand);
  if (!sidebarToggle) return;
  const label = shouldExpand ? 'Collapse navigation' : 'Expand navigation';
  sidebarToggle.setAttribute('aria-expanded', String(shouldExpand));
  sidebarToggle.setAttribute('aria-label', label);
  sidebarToggle.title = label;
}

sidebarToggle?.addEventListener('click', () => {
  setSidebarExpanded(sidebarToggle.getAttribute('aria-expanded') !== 'true');
});
window.addEventListener('resize', () => {
  if (window.innerWidth <= 700) setSidebarExpanded(false);
});
if (window.innerWidth <= 700) setSidebarExpanded(false);

/* ─────────────────────────────────────────────
   Init
───────────────────────────────────────────── */
showState('state-empty');
loadDiseases();
