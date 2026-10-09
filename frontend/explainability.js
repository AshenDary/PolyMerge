const escapeExplanation = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

function renderGraphContent(content) {
  if (!content) return '<p class="muted">Graph evidence unavailable for this candidate.</p>';
  const paths = (content.treatmentPaths ?? []).map((path) => `
    <li><strong>${escapeExplanation(path.drugName ?? path.drugId)}</strong>
      <span class="relationship-arrow">— ${escapeExplanation(path.relationship)} →</span>
      <strong>${escapeExplanation(path.diseaseName ?? path.diseaseId)}</strong>
      <small>Path ${escapeExplanation(path.pathId)} · ${escapeExplanation(path.source)} · ${escapeExplanation(path.graphVersion)}</small>
    </li>`).join('');
  const genePaths = (content.context?.genes ?? []).map((path) => `
    <li>${escapeExplanation(path.drugName ?? path.drugId)} — ${escapeExplanation(path.relationship)} → ${escapeExplanation(path.geneName ?? path.geneId)}
      <small>Path ${escapeExplanation(path.pathId)} · ${escapeExplanation(path.source)} · ${escapeExplanation(path.graphVersion)}</small></li>`).join('');
  const sideEffectPaths = (content.context?.sideEffects ?? []).map((path) => `
    <li>${escapeExplanation(path.drugName ?? path.drugId)} — ${escapeExplanation(path.relationship)} → ${escapeExplanation(path.sideEffectName ?? path.sideEffectId)}
      <small>Path ${escapeExplanation(path.pathId)} · ${escapeExplanation(path.source)} · ${escapeExplanation(path.graphVersion)}</small></li>`).join('');
  const hasPaths = paths || genePaths || sideEffectPaths;
  return `<div class="graph-summary"><span>Coverage in graph: ${escapeExplanation(content.summary?.coverage ?? 'Not provided')}</span>
    <span>Treatment paths: ${(content.treatmentPaths ?? []).length}</span></div>
    ${paths ? `<h5>Compound → CtD → Disease</h5><ul class="path-list">${paths}</ul>` : ''}
    ${genePaths ? `<h5>Compound → CbG / CuG / CdG → Gene</h5><ul class="path-list">${genePaths}</ul>` : ''}
    ${sideEffectPaths ? `<h5>Compound → CcSE → Side effect</h5><ul class="path-list">${sideEffectPaths}</ul>` : ''}
    ${!hasPaths ? '<p class="muted">No graph paths were returned for this candidate.</p>' : ''}
    <p class="provenance">Graph source: ${escapeExplanation(content.provenance?.source ?? 'Not provided')} · Version: ${escapeExplanation(content.provenance?.version ?? 'Not provided')}</p>
    <button type="button" class="secondary" data-visualization>View graph path visualization</button>
    <div class="graph-visualization" hidden></div>`;
}

function renderRulesContent(rules) {
  if (!rules?.length) return '<p class="muted">No deterministic rule details were returned.</p>';
  return `<ul class="rule-list">${rules.map((rule) => `<li class="rule-item rule-${escapeExplanation(rule.status)}">
    <strong>${rule.status === 'rejected' ? 'Rejected' : 'Accepted'} · ${escapeExplanation(rule.type)}</strong>
    <p>${escapeExplanation(rule.message)}</p>
    ${rule.affectedDrugs?.length ? `<small>Affected pair: ${rule.affectedDrugs.map(escapeExplanation).join(' + ')}</small>` : ''}
    <small>Stage: ${escapeExplanation(rule.stage ?? 'Not provided')} · Source: ${escapeExplanation(rule.source ?? 'Not provided')}</small>
  </li>`).join('')}</ul>`;
}

function renderPredictionsContent(content) {
  if (!content || content.status !== 'available' || !content.pairs?.length) {
    return `<div class="predictions-unavailable"><strong>Interaction prediction unavailable</strong>
      <p>${escapeExplanation(content?.message ?? 'No research prediction was returned for this candidate.')}</p>
      <small>This is not a clinical recommendation. No severity has been inferred.</small></div>`;
  }
  return `<ul class="prediction-list">${content.pairs.map((prediction) => `<li class="prediction-item">
    <div><strong>${prediction.drugs?.map(escapeExplanation).join(' + ') ?? 'Drug pair not provided'}</strong>
      <span class="severity-badge severity-${escapeExplanation(prediction.severity).toLowerCase()}">${escapeExplanation(prediction.severity ?? 'Class not provided')}</span></div>
    <small>Research prediction · ${escapeExplanation(prediction.model?.name ?? 'Model not provided')} · ${escapeExplanation(prediction.model?.version ?? 'Version not provided')} · ${escapeExplanation(prediction.inferenceStatus ?? 'Status not provided')}</small>
  </li>`).join('')}</ul>`;
}

function renderCandidateExplanation(explanation, container) {
  const sections = explanation.sections ?? [];
  const renderers = { graph: renderGraphContent, rules: renderRulesContent, predictions: renderPredictionsContent };
  const sectionMarkup = sections.map((section) => `<section class="evidence-section section-${escapeExplanation(section.type)}">
      <h4>${section.type === 'rules' ? 'Deterministic Rules' : section.type === 'predictions' ? 'Interaction Prediction' : escapeExplanation(section.title)}</h4>
    <div>${(renderers[section.type] ?? (() => '<p>Section unavailable.</p>'))(section.content)}</div>
    ${section.disclaimer ? `<small class="section-disclaimer">${escapeExplanation(section.disclaimer)}</small>` : ''}
  </section>`).join('');
  container.innerHTML = `<article class="candidate-explanation">
    <header class="candidate-header"><div><span class="rank-badge">#${escapeExplanation(explanation.rank ?? '—')}</span>
    <strong>Candidate explanation</strong><span class="status-badge status-${explanation.status === 'rejected' ? 'rejected' : 'accepted'}">${escapeExplanation(explanation.status)}</span></div>
    <div class="drug-list">${(explanation.drugs ?? []).map((drug) => `<code>${escapeExplanation(drug)}</code>`).join('')}</div></header>
    <div class="evidence-sections">${sectionMarkup}</div>
    <p class="overall-disclaimer">${escapeExplanation(explanation.overallDisclaimer ?? 'PolyMerge is a research decision-support prototype and does not provide clinical recommendations.')}</p>
  </article>`;
  const button = container.querySelector('[data-visualization]');
  button.addEventListener('click', async () => {
    const visualization = container.querySelector('.graph-visualization');
    visualization.hidden = false;
    setText(visualization, 'Loading graph visualization…');
    try {
      const data = await fetchExplainability(explanation._queryId, 'visualization');
      const graph = data.visualizations?.find((item) => item.candidateId === explanation.candidateId)?.evidencePath;
      const allowedRelationships = new Set(['CtD', 'CbG', 'CuG', 'CdG', 'CcSE']);
      const edges = (graph?.edges ?? []).filter((edge) => allowedRelationships.has(edge.label));
      if (!graph?.nodes?.length || !edges.length) {
        setText(visualization, 'Graph paths are unavailable for visualization.');
        return;
      }
      visualization.innerHTML = `<h5>Returned graph relationships</h5><div class="graph-path-list">${edges.map((edge) => {
        const source = graph.nodes.find((node) => node.id === edge.source);
        const target = graph.nodes.find((node) => node.id === edge.target);
        return `<div class="graph-path-row">
          <span class="graph-node graph-node-${escapeExplanation(source?.type ?? 'entity')}" title="${escapeExplanation(edge.source)}">${escapeExplanation(source?.label ?? edge.source)}</span>
          <span class="graph-edge"><span class="graph-edge-label">${escapeExplanation(edge.label)}</span><span class="graph-edge-arrow" aria-hidden="true">→</span></span>
          <span class="graph-node graph-node-${escapeExplanation(target?.type ?? 'entity')}" title="${escapeExplanation(edge.target)}">${escapeExplanation(target?.label ?? edge.target)}</span>
        </div>`;
      }).join('')}</div><small>${escapeExplanation(graph.disclaimer ?? '')}</small>`;
    } catch (error) { setText(visualization, `Graph visualization unavailable: ${error.message}`); }
  });
}

function setText(element, message) {
  element.textContent = message;
}

async function fetchExplainability(queryId, format) {
  const response = await fetch(`/api/candidate-sets/${encodeURIComponent(queryId)}/explain?format=${encodeURIComponent(format)}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error ?? `Request failed (${response.status})`);
  return data;
}

async function loadExplainability(queryId, format = 'detailed', candidateSetId = null) {
  const container = document.getElementById('explainability');
  setText(container, 'Loading candidate explanation…');
  try {
    const data = await fetchExplainability(queryId, format);
    container.replaceChildren();
    const explanations = (data.detailedExplanations ?? []).filter((item) => !candidateSetId || item.candidateId === candidateSetId);
    if (!explanations.length) {
      setText(container, 'No explanation was returned for this candidate.');
      return;
    }
    for (const explanation of explanations) {
      renderCandidateExplanation({ ...explanation, _queryId: queryId }, container);
    }
    if (data.disclaimer) {
      const disclaimer = document.createElement('p');
      disclaimer.className = 'global-disclaimer';
      disclaimer.textContent = data.disclaimer;
      container.appendChild(disclaimer);
    }
  } catch (error) {
    container.innerHTML = `<p class="state-message state-error" role="alert">Explainability unavailable: ${escapeExplanation(error.message)}</p>`;
  }
}

window.PolyMergeExplainability = { loadExplainability, renderCandidateExplanation };
if (typeof module !== 'undefined' && module.exports) module.exports = { loadExplainability, renderCandidateExplanation };
