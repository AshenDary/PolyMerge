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
const CANDIDATE_DISPLAY_LIMIT = 5;

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
  catalogStatus: 'loading',
  showAllCandidates: false,
  requestGeneration: 0,
  candidateController: null,
  simulationStep: 1,
  displayMode: 'simple',
  candidateOffset: 0,
};

function setSimulationStep(step, navigate = false) {
  if ((step === 2 && !state.analysisStartedAt) || (step >= 3 && !state.currentResult)) return;
  state.simulationStep = step;
  document.body.dataset.step = String(step);
  for (let number = 1; number <= 4; number += 1) {
    const button = document.getElementById(`step-${number}`);
    button.disabled = number === 2 ? !state.analysisStartedAt : number >= 3 ? !state.currentResult : Boolean(state.analysisStartedAt);
    if (number === step) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  }
  if (navigate) {
    window.location.hash = step === 4 ? 'explainability-panel' : 'simulation';
    document.body.dataset.view = step === 4 ? 'explainability-panel' : 'simulation';
    document.getElementById(`step-${step}`).focus();
  }
}

function setDisplayMode(mode) {
  state.displayMode = mode === 'researcher' ? 'researcher' : 'simple';
  document.body.dataset.mode = state.displayMode;
  document.getElementById('simple-view').setAttribute('aria-pressed', String(state.displayMode === 'simple'));
  document.getElementById('researcher-view').setAttribute('aria-pressed', String(state.displayMode === 'researcher'));
  document.getElementById('technical-pipeline').open = state.displayMode === 'researcher';
  if (state.currentResult) {
    renderResults(state.currentResult);
    renderSelectedCandidate(state.currentResult.candidateSets?.find(c => c.candidateSetId === state.selectedCandidateId), state.currentResult);
  }
}

function changeCandidatePage(direction) {
  const count = state.currentResult?.candidateSets?.length ?? 0;
  state.candidateOffset = Math.max(0, Math.min(Math.max(0, Math.ceil(count / CANDIDATE_DISPLAY_LIMIT) - 1) * CANDIDATE_DISPLAY_LIMIT,
    state.candidateOffset + direction * CANDIDATE_DISPLAY_LIMIT));
  if (state.currentResult) renderResults(state.currentResult);
}

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

function withTimeout(ms, externalSignal) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ms);
  const abort = () => { clearTimeout(timeout); controller.abort(); };
  if (externalSignal?.aborted) abort();
  else externalSignal?.addEventListener('abort', abort, { once: true });
  return { signal: controller.signal, clear: () => {
    clearTimeout(timeout);
    externalSignal?.removeEventListener('abort', abort);
  } };
}

async function readJsonResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;
  const message = data.error ?? data.detail ?? 'The request could not be completed.';
  throw new Error(`${response.status}: ${message}`);
}

async function fetchJson(url, options = {}, timeoutMs = DEFAULT_CATALOG_TIMEOUT_MS) {
  const timeout = withTimeout(timeoutMs, options.signal);
  try {
    const response = await fetch(url, { ...options, signal: timeout.signal });
    return await readJsonResponse(response);
  } catch (error) {
    if (error.name === 'AbortError' && !options.signal?.aborted) {
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
  return ['applied', 'partial'].includes(candidate?.mlStatus) && candidate.drugs?.length > 1
    ? (candidate.mlPrediction?.pairs ?? []).filter((pair) => pair.inferenceStatus === 'applied' && pair.predictedSeverity)
    : [];
}

function ruleLabel(candidate) {
  if (candidate?.status === 'rejected') return 'Rejected by research rule';
  return candidate?.ruleEvaluation?.status === 'evaluated' ? 'Evaluated; no configured rule triggered'
    : candidate?.ruleEvaluation?.status === 'partially_evaluated' ? 'Partial mapping coverage' : 'Insufficient verified mapping';
}

function analysisMetrics(data) {
  const candidates = data.candidateSets ?? [];
  return [
    ['Selected diseases', new Set(data.diseaseIds ?? (data.diseases ?? []).map((disease) => disease.id)).size],
    ['Mapped drugs in results', new Set(candidates.flatMap((candidate) => candidate.drugs ?? [])).size],
    ['Returned candidate sets', candidates.length],
    ['Rules evaluated', candidates.filter((candidate) => candidate.ruleEvaluation?.status === 'evaluated').length],
    ['Rejected by rules', candidates.filter((candidate) => candidate.status === 'rejected').length],
    ['Pair predictions across results', mlSummary(candidates).pairCount],
  ];
}

function mappingMarkup(paths) {
  const treatments = paths.filter((path) => relationshipType(path) === 'CtD');
  return treatments.length ? `<ul class="mapping-list">${treatments.map((path) => `<li>${escapeHtml(path.sourceEntity?.name ?? path.sourceEntity?.id)} → ${escapeHtml(path.targetEntity?.name ?? path.targetEntity?.id)} <small>CtD</small></li>`).join('')}</ul>` : '<p>No treatment mapping paths were returned.</p>';
}

const RANK_EXPLANATION = 'At generation, sets are ordered by configured exclusion status (not rejected first), then more selected diseases represented, then fewer drugs. Candidate set ID breaks remaining ties. Backend validation can add a rejection without changing that rank. Interaction severity does not determine this rank; an untriggered rule does not establish mapping coverage.';

function pairLabel(pair, candidate) {
  return (pair.drugPair ?? []).map((id) => candidate.drugNames?.[candidate.drugs.indexOf(id)] ?? id).join(' + ');
}

function understandingGuide() {
  const definitions = [
    ['Candidate set', 'A group of existing drugs considered together by the system.'],
    ['Compound', 'A drug or chemical entity represented in the knowledge graph.'],
    ['Knowledge graph', 'A network of stored relationships between biomedical entities.'],
    ['CtD', 'Compound treats Disease: a treatment relationship represented in the graph.'],
    ['CbG', 'Compound binds Gene: a represented compound-gene relationship.'],
    ['CuG', 'Compound upregulates Gene: a represented gene-activity relationship.'],
    ['CdG', 'Compound downregulates Gene: a represented gene-activity relationship.'],
    ['CcSE', 'Compound causes Side Effect: a side-effect relationship recorded in the graph.'],
    ['Gene context', 'Information about how a compound is connected to genes in the graph. This does not establish clinical mechanism or benefit.'],
    ['Graph coverage', 'The share of selected diseases with represented CtD treatment connections from the candidate drugs.'],
    ['Deterministic rule', 'A predefined system check that accepts or rejects a candidate according to configured conditions.'],
    ['ML prediction', 'A classification produced from the frozen drug-pair feature representation.'],
    ['Major / Moderate / Minor', 'Interaction-severity categories learned from the curated DDInter dataset, not independent clinical verification.'],
  ];
  return `<aside class="reading-guide"><h4>Understanding your result</h4>
    <dl class="result-guide"><div><dt>Graph evidence</dt><dd>Shows which drugs are connected to diseases, genes, or side effects in the knowledge graph.</dd></div>
    <div><dt>Rule check</dt><dd>Shows whether the candidate triggered any of the system's configured exclusion rules.</dd></div>
    <div><dt>Interaction prediction</dt><dd>Shows the severity class predicted for supported drug pairs by the Random Forest model.</dd></div>
    <div><dt>Coverage</dt><dd>Shows how many selected diseases have represented treatment relationships in the graph.</dd></div></dl>
    <details><summary>Terms and relationship definitions</summary><dl class="result-glossary">${definitions.map(([term, definition]) => `<dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd>`).join('')}</dl><p>Side-effect context is not a complete side-effect profile. Compound resemblance is not drug-drug interaction evidence.</p></details>
  </aside>`;
}

function finalCandidateSummary(candidate, data) {
  const targets = data.diseaseIds ?? (data.diseases ?? []).map((disease) => disease.id);
  const covered = (candidate.treatedDiseaseIds ?? []).filter((id) => targets.includes(id));
  const treatments = graphPaths(candidate).filter((path) => relationshipType(path) === 'CtD' && targets.includes(path.targetEntity?.id));
  const pairs = appliedPairs(candidate);
  const ml = candidateMlPresentation(candidate);
  const ruleOutcome = candidate.status === 'accepted'
    ? ruleLabel(candidate)
    : candidate.status === 'rejected'
      ? `Rejected by configured rules. ${(candidate.rejectionReasons ?? []).map((reason) => reason.message ?? 'Reason not provided').join(' ')}`
      : 'No rule outcome was returned.';
  return `<section class="candidate-conclusion"><h4>What this result tells us</h4>
    <dl class="result-guide"><div><dt>Why these drugs were included</dt><dd>This candidate contains ${escapeHtml(candidateLabel(candidate))}. ${treatments.length ? `${treatments.length} returned CtD treatment connections link its drugs to selected diseases.` : 'No CtD treatment connections to the selected diseases were returned for inspection.'}</dd></div>
    <div><dt>Disease coverage</dt><dd>${covered.length} of ${targets.length} selected diseases are represented in the reported graph coverage.</dd></div>
    <div><dt>Rule-check outcome</dt><dd>${escapeHtml(ruleOutcome)}</dd></div>
    <div><dt>Interaction prediction</dt><dd>${pairs.length ? `<ul>${pairs.map((pair) => `<li>Random Forest classified ${escapeHtml(pairLabel(pair, candidate))} as ${escapeHtml(pair.predictedSeverity)}.</li>`).join('')}</ul>` : escapeHtml(ml.detail)}</dd></div>
    <div><dt>Ranking explanation</dt><dd>Rank ${escapeHtml(candidate.rank ?? 'not provided')}, with ${candidate.drugs?.length ?? 0} drugs and rule status ${ruleLabel(candidate)}. This follows configured graph-coverage ordering, not an ML prediction of clinical benefit.</dd></div>
    <div><dt>Research interpretation</dt><dd>These separate outputs support further research review. They do not establish clinical safety, effectiveness, or suitability for manufacturing.</dd></div></dl>
  </section>`;
}

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
  if (pairCount > 0) {
    const partial = candidate.mlStatus === 'partial';
    return {
      status: partial ? 'partial' : 'complete',
      label: `${partial ? 'Partial predictions available' : 'Prediction available'}: ${pairCount === 1 ? pairs[0].predictedSeverity : `${pairCount} pairs classified`}`,
      summary: pluralize(pairCount, 'drug-pair prediction'),
      detail: pairs.map((pair) => `${pairLabel(pair, candidate)}: ${pair.predictedSeverity}`).join('; '),
    };
  }
  return {
    status: 'unavailable',
    label: 'Prediction unavailable',
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
      status: !candidates.length || candidates.every(candidate => !candidate.ruleEvaluation || candidate.ruleEvaluation.status === 'not_evaluable') ? 'unavailable'
        : candidates.every(candidate => candidate.ruleEvaluation?.status === 'evaluated') ? 'complete' : 'partial',
      summary: `${candidates.filter(candidate => candidate.ruleEvaluation?.status === 'evaluated').length} fully evaluated · ${candidates.filter(candidate => candidate.ruleEvaluation?.status === 'partially_evaluated').length} partial · ${rejected} rejected by research rules; ${candidates.filter(candidate => !candidate.ruleEvaluation || candidate.ruleEvaluation.status === 'not_evaluable').length} lack sufficient mappings.`,
      detail: 'Missing verified identity or category mappings prevent evaluation; no rejection is not a passed clinical safety check.',
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
      status: allSingleDrug ? 'not_applicable' : ml.applied ? (candidates.some(candidate => candidate.drugs?.length > 1 && candidate.mlStatus !== 'applied') ? 'partial' : 'complete') : 'unavailable',
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
  const warning = document.getElementById('workflow-warning');
  const problems = stages.filter(stage => ['unavailable', 'error', 'partial'].includes(stage.status));
  warning.hidden = problems.length === 0;
  warning.textContent = problems.map(stage => `${stage.name}: ${stage.summary}`).join(' · ');
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
  state.catalogStatus = 'loading';
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
    state.catalogStatus = 'ready';
    catalogMessage.hidden = true;
    catalogTag.textContent = 'Catalog ready';
    renderDiseases();
  } catch (error) {
    state.catalogStatus = 'unavailable';
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
  document.getElementById('your-analysis').innerHTML = `<p>${(data.diseaseIds ?? [...labels.keys()]).map((id) => escapeHtml(labels.get(id) ?? id)).join(' + ')}</p>`;
  const cardData = [['Diseases selected', data.diseaseIds?.length ?? data.diseases?.length ?? 0],
    ['Returned candidate sets', data.candidateSets?.length ?? 0], ['Candidates with predictions', mlSummary(data.candidateSets ?? []).applied]];
  cards.innerHTML = cardData.map(([label, value]) => `
    <div class="funnel-step"><div class="value">${escapeHtml(value)}</div><div class="label">${escapeHtml(label)}</div></div>`).join('');
}

function renderResults(data) {
  const results = document.getElementById('results');
  const candidates = data.candidateSets ?? [];
  const showAll = state.displayMode === 'researcher' && state.showAllCandidates;
  const visible = showAll ? candidates : candidates.slice(state.candidateOffset, state.candidateOffset + CANDIDATE_DISPLAY_LIMIT);
  const display = document.getElementById('result-display');
  display.hidden = candidates.length === 0;
  document.getElementById('show-all-candidates').checked = state.showAllCandidates;
  document.getElementById('show-all-control').hidden = state.displayMode !== 'researcher' || candidates.length <= CANDIDATE_DISPLAY_LIMIT;
  document.getElementById('result-count').textContent = showAll ? `Showing all ${candidates.length} returned candidates` : `Showing ${visible.length ? state.candidateOffset + 1 : 0}-${state.candidateOffset + visible.length} of ${candidates.length} returned candidates`;
  document.getElementById('result-limit-note').textContent = '';
  document.getElementById('next-candidates').disabled = showAll || state.candidateOffset + CANDIDATE_DISPLAY_LIMIT >= candidates.length;
  document.getElementById('previous-candidates').disabled = showAll || state.candidateOffset === 0;
  const selectedCandidate = candidates.find((candidate) => candidate.candidateSetId === state.selectedCandidateId);
  document.getElementById('selected-result-link').innerHTML = selectedCandidate
    ? `<a href="#explainability-panel">Selected: Candidate #${escapeHtml(selectedCandidate.rank ?? 'Not provided')} · ${escapeHtml(candidateLabel(selectedCandidate))}</a>` : '';
  renderSummary(data);
  if (data.metadata?.dataStatus === 'graph_unavailable') {
    setMessage(results, data.metadata.warning || 'Graph evidence is unavailable; no candidate sets were returned.', 'warning');
    return;
  }
  if (!candidates.length) {
    setMessage(results, 'No represented treatment connections were found for this selection; no candidate sets can be built from this graph fragment.', 'empty');
    return;
  }

  const diseaseLabels = diseaseLabelMap(data);
  results.innerHTML = visible.map((candidate) => {
    const selected = candidate.candidateSetId === state.selectedCandidateId;
    const rejectionReasons = (candidate.rejectionReasons ?? []).map((reason) => reason.message).join('; ');
    const ml = candidateMlPresentation(candidate);
    return `<article class="result-card ${selected ? 'selected-result' : ''}">
      <div class="result-header">
        <div>
          <p class="eyebrow">Candidate #${escapeHtml(candidate.rank ?? 'Not provided')}</p>
          <h3>${escapeHtml(candidateLabel(candidate))}</h3>
        </div>
        <span class="status-badge status-${candidate.status === 'rejected' ? 'rejected' : candidate.ruleEvaluation?.status === 'evaluated' ? 'accepted' : 'unknown'}">Rule check: ${ruleLabel(candidate)}</span>
      </div>
      <ul class="drug-list researcher-only">${(candidate.drugs ?? []).map((id, index) => `
        <li class="drug-item"><strong>${escapeHtml(candidate.drugNames?.[index] ?? id)}</strong><code>${escapeHtml(id)}</code></li>`).join('')}</ul>
      <div class="result-meta">
        <span><strong>Graph coverage</strong> ${(candidate.treatedDiseaseIds ?? []).length} of ${data.diseaseIds?.length ?? data.diseases?.length ?? 0} selected diseases represented</span>
        <span class="researcher-only">Covered: ${(candidate.treatedDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None provided'}</span>
        <span class="researcher-only">Uncovered: ${(candidate.uncoveredDiseaseIds ?? []).map((id) => escapeHtml(diseaseLabels.get(id) ?? id)).join(', ') || 'None'}</span>
        <span>Interaction prediction: ${escapeHtml(ml.label)}</span>
      </div>
      ${rejectionReasons ? `<p class="inline-warning">${escapeHtml(rejectionReasons)}</p>` : ''}
      <button type="button" class="secondary explanation-button" data-candidate-id="${escapeHtml(candidate.candidateSetId)}" aria-pressed="${selected}">Understand this candidate</button>
    </article>`;
  }).join('');
  results.querySelectorAll('[data-candidate-id]').forEach((button) => {
    button.addEventListener('click', () => selectCandidate(button.dataset.candidateId, true));
  });
}

function renderGraphVisualization(candidate, advanced = state.displayMode === 'researcher') {
  const priority = { CtD: 0, CbG: 1, CuG: 1, CdG: 1, CcSE: 2 };
  const paths = graphPaths(candidate).filter(path => advanced || relationshipType(path) === 'CtD').slice().sort((a, b) => priority[relationshipType(a)] - priority[relationshipType(b)]).slice(0, 30);
  if (!paths.length) return '<p class="muted">Graph paths are unavailable for this candidate.</p>';
  return `<div class="graph-stage">
    <div class="evidence-diagram" aria-label="Candidate knowledge graph evidence paths">
      ${paths.map((path) => {
        const rel = relationshipType(path);
        const type = rel === 'CtD' ? 'disease' : rel === 'CcSE' ? 'side-effect' : 'gene';
        return `<div class="evidence-edge">
          <div class="evidence-node node-compound"><small>Drug</small><strong>${escapeHtml(path.sourceEntity?.name ?? path.sourceEntity?.id)}</strong></div>
          <span class="evidence-connector" title="${advanced ? `${escapeHtml(path.pathId)} · ${escapeHtml(path.provenance?.source)} · ${escapeHtml(path.provenance?.graphVersion)}` : 'Represented treatment relationship'}">${escapeHtml(rel)} <span aria-hidden="true">→</span></span>
          <div class="evidence-node node-${type}"><small>${type === 'side-effect' ? 'Side Effect' : type === 'disease' ? 'Disease' : 'Gene'}</small><strong>${escapeHtml(path.targetEntity?.name ?? path.targetEntity?.id)}</strong></div>
        </div>`;
      }).join('')}
    </div>
    <div class="graph-legend">
      <span class="legend-compound">Drug</span><span class="legend-disease">Disease</span><span>Relationship</span>${advanced ? '<span class="legend-gene">Gene</span><span class="legend-side-effect">Side Effect</span>' : ''}
    </div>
    ${advanced ? '<dl class="relationship-legend"><div><dt>CtD</dt><dd>Compound treats Disease</dd></div><div><dt>CbG</dt><dd>Compound binds Gene</dd></div><div><dt>CuG</dt><dd>Compound upregulates Gene</dd></div><div><dt>CdG</dt><dd>Compound downregulates Gene</dd></div><div><dt>CcSE</dt><dd>Compound causes Side Effect</dd></div></dl>' : ''}
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
  const labels = diseaseLabelMap(data);
  const { targets, covered, uncovered } = candidateCoverage(candidate, data);
  const pairs = appliedPairs(candidate);
  const unavailable = candidate.mlPrediction?.unavailablePairs ?? [];
  const evaluation = candidate.ruleEvaluation;
  const rules = evaluation?.rules ?? [];
  const reasons = candidate.rejectionReasons ?? [];
  const triggered = candidate.status === 'rejected' || rules.some(rule => rule.triggered);
  const fullyEvaluated = evaluation?.status === 'evaluated';
  const optimizer = data.metadata?.optimization;
  container.innerHTML = `<article class="candidate-explanation candidate-overview">
    <header class="overview-heading">
      <p class="eyebrow">Candidate #${escapeHtml(candidate.rank ?? 'Not provided')}</p>
      <h3>${escapeHtml(candidateLabel(candidate))}</h3>
    </header>
    <section class="overview-section overview-coverage" aria-label="Why these drugs?">
      <h4>Why these drugs?</h4><p>${shortCandidateSummary(candidate, data)}</p>
      <ul class="covered-diseases" aria-label="Covered diseases">${covered.map(id => `<li>${escapeHtml(labels.get(id) ?? id)}</li>`).join('')}</ul>
      <div class="coverage-measure"><span>Graph coverage: ${covered.length} of ${targets.length} diseases</span>
        ${targets.length ? `<meter min="0" max="${targets.length}" value="${covered.length}" aria-label="Represented graph coverage">${covered.length} of ${targets.length}</meter>` : ''}</div>
      ${uncovered.length ? `<details class="uncovered-diseases"><summary>Not covered (${uncovered.length})</summary><ul>${uncovered.map(id => `<li>${escapeHtml(labels.get(id) ?? id)}</li>`).join('')}</ul></details>` : ''}
    </section>
    <section class="overview-section overview-rules" aria-label="Rule check">
      <h4>Rule check</h4>
      <strong>${fullyEvaluated ? (triggered ? 'Configured rule triggered' : 'Evaluated; no configured rule triggered') : 'Not fully evaluated'}</strong>
      ${!fullyEvaluated ? `<p>${evaluation?.status ? 'Some drug-category mappings are missing, so the configured research rules could not be fully checked.' : 'Rule applicability information was not returned, so evaluation cannot be confirmed.'}</p>` : ''}
      ${rules.length ? `<p class="rule-coverage">${rules.filter(rule => rule.status === 'evaluated').length} of ${rules.length} configured rules evaluated${fullyEvaluated ? '' : `; ${rules.filter(rule => rule.status === 'partially_evaluated').length} with partial coverage, ${rules.filter(rule => rule.status === 'not_evaluable').length} not evaluable`}.</p>` : ''}
      ${triggered ? `<p class="rule-triggered">${fullyEvaluated ? 'Research exclusion applies.' : 'A configured research exclusion was triggered despite incomplete coverage.'}</p>` : ''}
      ${reasons.length ? `<ul>${reasons.map(reason => `<li>${escapeHtml(reason.message ?? 'Reason not provided')}</li>`).join('')}</ul>` : ''}
    </section>
    <section class="overview-section overview-predictions" aria-label="Random Forest predictions">
      <h4>Random Forest predictions</h4>
      ${candidate.drugs?.length === 1 ? '<p>Not applicable: this candidate contains one drug.</p>' : `
        ${candidate.mlStatus === 'partial' ? '<p>Partial predictions available</p>' : ''}
        ${pairs.length ? `<ul class="pair-results" aria-label="Available pair predictions">${pairs.map(pair => `<li class="pair-result"><span class="pair-name">${escapeHtml(pairLabel(pair, candidate))}</span><strong class="pair-severity">${escapeHtml(pair.predictedSeverity)}</strong></li>`).join('')}</ul>` : ''}
        ${unavailable.length ? `<h5>Unavailable pairs</h5><ul class="pair-results" aria-label="Unavailable pair predictions">${unavailable.map(pair => `<li class="pair-result pair-unavailable"><span class="pair-name">${escapeHtml(pairLabel(pair, candidate))}</span><span class="pair-severity">Unavailable</span><p class="pair-reason">${escapeHtml(pair.reason ?? 'No reason provided.')}</p></li>`).join('')}</ul>` : ''}
        ${!pairs.length && !unavailable.length ? `<p>Prediction unavailable</p><p>${escapeHtml(candidate.mlPrediction?.reason ?? 'No pair-level prediction was returned.')}</p>` : ''}`}
    </section>
    <section class="overview-section overview-ranking" aria-label="Ranking explanation">
      <h4>Why rank #${escapeHtml(candidate.rank ?? 'Not provided')}?</h4>
      <p>This rank reflects configured exclusion status, graph coverage and drug count, not clinical superiority.</p>
    </section>
    <div class="overview-details">
      <details class="technical-details"><summary>Graph evidence and connections</summary>
        <p>${escapeHtml(candidate.graphEvidence?.source ?? data.metadata?.graph ?? 'Source not provided')} · ${escapeHtml(candidate.graphEvidence?.graphVersion ?? 'Version not provided')}</p>
        ${renderGraphVisualization(candidate, true)}
        ${renderPathList(candidate, 'treatment', 'CtD Treatment Paths')}
        ${renderPathList(candidate, 'gene_context', 'Gene Context')}
        ${renderPathList(candidate, 'side_effect_context', 'Side-Effect Context')}
      </details>
      <details class="technical-details"><summary>Rule mapping coverage and provenance</summary>
        <p>${escapeHtml(evaluation?.source ?? 'Verified rule mappings were not provided.')}</p><p>Mapping version: ${escapeHtml(evaluation?.mappingVersion ?? 'Not provided')}</p>
        <ul>${(evaluation?.identities ?? []).map(identity => `<li>${escapeHtml(identity.drugId)}: ${escapeHtml(identity.tokens?.join(', ') || 'No verified category mapping')} · ${escapeHtml(identity.source ?? 'No source')}${identity.classId ? ` · ${escapeHtml(identity.classId)}` : ''}</li>`).join('')}</ul>
        <ul>${rules.map(rule => `<li>${(rule.pair ?? []).map(escapeHtml).join(' + ')}: ${escapeHtml(rule.status)}${rule.triggered ? ' (triggered)' : ''}</li>`).join('')}</ul>
        ${reasons.length ? `<ul>${reasons.map(reason => `<li>${(reason.pair ?? []).map(escapeHtml).join(' + ')} · Stage: ${escapeHtml(reason.stage ?? 'Not provided')} · Source: ${escapeHtml(reason.source ?? 'PolyMerge research rules')}</li>`).join('')}</ul>` : ''}
      </details>
      <details class="technical-details"><summary>ML details and model provenance</summary>
        ${pairs.length ? `<ul>${pairs.map(pair => `<li>${(pair.drugPair ?? []).map(escapeHtml).join(' + ')}<br>${escapeHtml(pair.model?.name ?? 'Model not provided')} · ${escapeHtml(pair.model?.version ?? 'Version not provided')} · ${escapeHtml(pair.inferenceStatus ?? 'Status not provided')}</li>`).join('')}</ul>` : '<p>No model prediction was applied.</p>'}
        ${unavailable.length ? `<ul>${unavailable.map(pair => `<li>${(pair.drugPair ?? []).map(escapeHtml).join(' + ')} · ${escapeHtml(pair.reasonCode)}${pair.missingDrugIds?.length ? ` · Missing: ${pair.missingDrugIds.map(escapeHtml).join(', ')}` : ''}</li>`).join('')}</ul>` : ''}
      </details>
      <details class="technical-details"><summary>Ranking and optimizer details</summary><p>${RANK_EXPLANATION}</p>
        ${optimizer ? `<p>Greedy coverage selection: ${(optimizer.selectedDrugs ?? []).map(escapeHtml).join(', ') || 'No drugs selected'}.</p><p>Selected candidate sets: ${(optimizer.selectedCandidateSetIds ?? []).map(escapeHtml).join(', ') || 'None provided'}.</p><p>Covered diseases: ${(optimizer.coveredDiseaseIds ?? []).map(escapeHtml).join(', ') || 'None provided'}.</p><p>Rule applicability: ${escapeHtml(optimizer.ruleEvaluation?.status ?? 'Not provided')}.</p>` : '<p>No optimizer details were returned.</p>'}
      </details>
      <details class="technical-details"${state.displayMode === 'researcher' ? ' open' : ''}><summary>Candidate identifiers</summary><p>${escapeHtml(candidate.candidateSetId)} · Raw status: ${escapeHtml(candidate.status)}</p><p>${(candidate.drugs ?? []).map(escapeHtml).join(', ')}</p><p>Selected diseases: ${targets.map(escapeHtml).join(', ') || 'None provided'}</p></details>
      <details><summary>Terms and evidence guide</summary>${understandingGuide()}</details>
    </div>
  </article>`;
}

function candidateCoverage(candidate, data) {
  const targets = [...new Set(data.diseaseIds ?? (data.diseases ?? []).map(disease => disease.id))];
  const covered = targets.filter(id => (candidate.treatedDiseaseIds ?? []).includes(id));
  return { targets, covered, uncovered: targets.filter(id => !covered.includes(id)) };
}

function shortCandidateSummary(candidate, data) {
  const { targets, covered } = candidateCoverage(candidate, data);
  const paths = graphPaths(candidate).filter(path => relationshipType(path) === 'CtD');
  return paths.length && covered.length
    ? `These drugs have represented treatment connections for ${covered.length} of your ${targets.length} selected diseases.`
    : 'No treatment connections were returned for these drugs.';
}

function selectCandidate(candidateId, navigate = false) {
  if (!state.currentResult) return;
  state.selectedCandidateId = candidateId;
  const candidates = state.currentResult?.candidateSets ?? [];
  const candidate = candidates.find((item) => item.candidateSetId === candidateId) ?? candidates[0];
  renderWorkflow(computeWorkflowStages(state.currentResult, state.selectedCandidateId));
  renderResults(state.currentResult);
  renderSelectedCandidate(candidate, state.currentResult);
  if (navigate) setSimulationStep(4, true);
}

function startElapsedTimer() {
  const elapsed = document.getElementById('elapsed-time');
  clearInterval(state.elapsedTimer);
  state.analysisStartedAt = Date.now();
  elapsed.textContent = 'Elapsed: 0s';
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
  const generation = ++state.requestGeneration;
  const controller = new AbortController();
  state.candidateController = controller;
  const analyzeBtn = document.getElementById('analyze-btn');
  const results = document.getElementById('results');
  const catalogTag = document.getElementById('catalog-tag');
  const running = document.getElementById('analysis-running');
  analyzeBtn.disabled = true;
  catalogTag.textContent = 'Search in progress';
  running.hidden = false;
  if (state.catalogStatus === 'ready') document.getElementById('catalog-message').hidden = true;
  state.currentResult = null;
  state.selectedCandidateId = null;
  state.showAllCandidates = false;
  state.candidateOffset = 0;
  document.getElementById('result-display').hidden = true;
  document.getElementById('analysis-summary').hidden = true;
  startElapsedTimer();
  setSimulationStep(2, true);
  renderWorkflow(computeWorkflowStages(null, null, true));
  setMessage(results, 'Analysis running. The local research graph pipeline may take about a minute.');
  document.getElementById('summary-cards').replaceChildren();
  renderSelectedCandidate(null, null);
  try {
    const data = await fetchJson('/api/candidate-sets/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseaseIds: Array.from(state.selectedDiseases) }),
      signal: controller.signal,
    }, DEFAULT_CANDIDATE_TIMEOUT_MS);
    if (generation !== state.requestGeneration) return;
    state.currentResult = data;
    state.selectedCandidateId = data.candidateSets?.[0]?.candidateSetId ?? null;
    catalogTag.textContent = data.metadata?.dataStatus === 'graph_unavailable' ? 'Graph unavailable' : 'Search complete';
    renderResults(data);
    renderWorkflow(computeWorkflowStages(data, state.selectedCandidateId));
    renderSelectedCandidate(data.candidateSets?.[0], data);
    setSimulationStep(3, true);
  } catch (error) {
    if (generation !== state.requestGeneration) return;
    catalogTag.textContent = error.message.includes('timed out') ? 'Candidate search timeout' : 'System error';
    setMessage(results, `Candidate search unavailable: ${error.message}`, 'error');
    renderWorkflow(computeWorkflowStages(null, null, false, error.message));
    setSimulationStep(1, true);
    setMessage(document.getElementById('catalog-message'), `Analysis unavailable: ${error.message}`, 'error');
    document.getElementById('catalog-message').hidden = false;
  } finally {
    if (generation === state.requestGeneration) {
      state.candidateController = null;
      stopElapsedTimer();
      running.hidden = true;
      renderSelectionSummary();
      setSimulationStep(state.simulationStep);
    }
  }
}

function resetSimulation() {
  // Invalidate callbacks even when the server or a transport ignores the abort.
  state.requestGeneration += 1;
  state.candidateController?.abort();
  state.candidateController = null;
  stopElapsedTimer();
  state.selectedDiseases.clear();
  state.currentResult = null;
  state.selectedCandidateId = null;
  state.showAllCandidates = false;
  state.candidateOffset = 0;
  document.getElementById('disease-search').value = '';
  document.getElementById('elapsed-time').textContent = 'Elapsed: 0s';
  document.getElementById('analysis-running').hidden = true;
  document.getElementById('analysis-summary').hidden = true;
  document.getElementById('result-display').hidden = true;
  document.getElementById('show-all-candidates').checked = false;
  for (const id of ['summary-cards', 'your-analysis', 'result-count', 'result-limit-note', 'selected-result-link']) {
    document.getElementById(id).replaceChildren();
  }
  setMessage(document.getElementById('results'), 'Choose one or more target diseases, then search to see ranked candidate sets.', 'empty');
  renderWorkflow(computeWorkflowStages(null));
  renderSelectedCandidate(null, null);
  document.getElementById('catalog-tag').textContent = state.catalogStatus === 'ready'
    ? 'Catalog ready' : state.catalogStatus === 'loading' ? 'Loading catalog' : 'Catalog unavailable';
  if (state.catalogStatus === 'ready') {
    document.getElementById('catalog-message').hidden = true;
    renderDiseases();
  } else {
    renderSelectionSummary();
  }
  window.location.hash = 'simulation';
  document.body.dataset.view = 'simulation';
  setSimulationStep(1);
  document.getElementById('disease-search').focus();
}

function renderModelAnalysisShell(data = null) {
  const rows = data?.rows ?? [
    { Model: 'LogisticRegression', 'Mean Macro F1': '0.290759' },
    { Model: 'RandomForestClassifier', 'Mean Macro F1': '0.506086' },
    { Model: 'HistGradientBoostingClassifier', 'Mean Macro F1': '0.407769' },
  ];
  const values = rows.map((row) => ({ name: row.Model, value: Number(row['Mean Macro F1']) }));
  const max = Math.max(...values.map((row) => row.value));
  const table = rows.map((row) => `<tr>${Object.entries(row).map(([key, value]) => `<td>${escapeHtml(key === 'Model' && value === 'RandomForestClassifier' ? 'Random Forest' : value)}</td>`).join('')}</tr>`).join('');
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
      <p>Random Forest had the highest validation Macro F1 among the three tested classical models.</p>
      <p class="inline-warning">Major and Minor recall remains limited. These results are not clinical validation.</p>
      <div class="final-metrics">
        <span>DDInter classes: Major, Moderate, Minor</span>
        <span>Primary metric: validation Macro F1</span>
        <span>Selected model: Random Forest</span>
      </div>
    </section>`,
    comparison: `<section class="analysis-section" role="tabpanel">
      <h3>Model Comparison</h3>
      <p>Preserved validation Macro F1. Random Forest was selected by highest mean validation Macro F1.</p>
      <div class="bar-chart" aria-label="Validation Macro F1 chart">
        ${values.map((row) => `<div class="bar-row ${row.name === 'RandomForestClassifier' ? 'selected-model' : ''}"><span>${escapeHtml(row.name === 'RandomForestClassifier' ? 'Random Forest' : row.name.replace('Classifier', ''))}</span><div><i style="width:${Math.max(8, (row.value / max) * 100)}%"></i></div><strong>${row.value.toFixed(6)}</strong></div>`).join('')}
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
  if (view === 'explainability-panel' && state.currentResult) setSimulationStep(4);
  if (view === 'simulation' && state.simulationStep === 4) setSimulationStep(state.currentResult ? 3 : 1);
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
  setSimulationStep(1);
  setDisplayMode('simple');
  renderWorkflow(computeWorkflowStages(null));
  document.getElementById('analyze-btn').addEventListener('click', analyzeCombination);
  document.getElementById('reset-simulation').addEventListener('click', resetSimulation);
  document.getElementById('cancel-analysis').addEventListener('click', resetSimulation);
  document.getElementById('simple-view').addEventListener('click', () => setDisplayMode('simple'));
  document.getElementById('researcher-view').addEventListener('click', () => setDisplayMode('researcher'));
  document.getElementById('next-candidates').addEventListener('click', () => changeCandidatePage(1));
  document.getElementById('previous-candidates').addEventListener('click', () => changeCandidatePage(-1));
  for (let step = 1; step <= 4; step += 1) document.getElementById(`step-${step}`).addEventListener('click', () => setSimulationStep(step, true));
  document.getElementById('show-all-candidates').addEventListener('change', (event) => {
    state.showAllCandidates = event.target.checked;
    if (state.currentResult) renderResults(state.currentResult);
  });
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
  renderResults,
  resetSimulation,
  analyzeCombination,
  finalCandidateSummary,
  understandingGuide,
  shortCandidateSummary,
  setSimulationStep,
  setDisplayMode,
  changeCandidatePage,
};

if (typeof document !== 'undefined') {
  init();
}
