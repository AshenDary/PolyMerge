const diseaseList = document.getElementById('disease-list');
const analyzeBtn = document.getElementById('analyze-btn');
const resultsContainer = document.getElementById('results');
const summaryCards = document.getElementById('summary-cards');
const explainability = document.getElementById('explainability');
const statusTag = document.getElementById('status-tag');

const selectedDiseases = new Set();

function renderDiseases(diseases) {
  diseaseList.innerHTML = diseases
    .map(
      (disease) => `
        <button class="disease-chip" data-id="${disease.id}">
          ${disease.name}
          <span>${selectedDiseases.has(disease.id) ? '×' : ''}</span>
        </button>
      `
    )
    .join('');

  diseaseList.querySelectorAll('.disease-chip').forEach((button) => {
    const diseaseId = button.dataset.id;
    if (selectedDiseases.has(diseaseId)) {
      button.classList.add('selected');
    }

    button.addEventListener('click', () => {
      if (selectedDiseases.has(diseaseId)) {
        selectedDiseases.delete(diseaseId);
      } else {
        selectedDiseases.add(diseaseId);
      }
      renderDiseases(diseases);
    });
  });
}

function renderSummaryCards(candidates) {
  const candidate = candidates[0] ?? {};

  const cards = [
    { label: 'Treatment Coverage', value: `${(candidate.coverage ?? 0) * 100}% KG Coverage` },
    { label: 'Interaction Risk', value: candidate.interactionRisk != null ? candidate.interactionRisk.toFixed(2) : 'Not applied' },
    { label: 'Synergy Model', value: candidate.synergyScore != null ? candidate.synergyScore.toFixed(2) : 'Not applied' },
    { label: 'Drug Count', value: candidate.drugCount ?? 'N/A' },
    { label: 'Evidence Level', value: candidate.evidenceLevel ?? 'N/A' },
  ];

  summaryCards.innerHTML = cards
    .map(
      (card) => `
        <div class="card">
          <div class="label">${card.label}</div>
          <div class="value">${card.value}</div>
        </div>
      `
    )
    .join('');
}

function renderResults(data) {
  const results = data.candidates ?? [];

  renderSummaryCards(results);

  resultsContainer.innerHTML = results.length
    ? results
        .map(
          (candidate) => `
            <article class="result-card">
              <div class="result-header">
                <h3>Candidate #${candidate.rank}</h3>
                <button class="secondary" data-candidate="${candidate.rank}">View Explanation</button>
              </div>
              <div class="result-drugs">
                ${(candidate.drugs ?? []).map((drug) => `<span class="drug-tag">${drug}</span>`).join('')}
              </div>
              <div class="result-meta">
                <span>Coverage: ${(candidate.coverage ?? 0) * 100}% KG Coverage</span>
                <span>Interaction Risk: ${candidate.interactionRisk ?? 'Not applied'}</span>
                <span>Synergy Model: ${candidate.synergyScore ?? 'Not applied'}</span>
                <span>Evidence: ${candidate.evidenceLevel ?? 'N/A'}</span>
                <span>Status: ${candidate.status ?? 'accepted'}</span>
              </div>
              <div class="result-meta">
                ${candidate.reason ? `<span>Reason: ${candidate.reason.message}</span>` : ''}
                ${candidate.reasons ? candidate.reasons.map((reason) => `<span>${reason}</span>`).join('') : ''}
              </div>
            </article>
          `
        )
        .join('')
    : '<p class="muted">No candidates returned.</p>';

  resultsContainer.querySelectorAll('[data-candidate]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = Number(button.dataset.candidate) - 1;
      const candidate = results[target];
      if (!candidate) return;

      // Render a simple explanation panel.
      explainability.innerHTML = `
        <div class="explainability-list">
          <div class="explainability-item">
            <h3>Why was this candidate ranked?</h3>
            <ul>
              ${(candidate.reasons ?? []).map((reason) => `<li>${reason}</li>`).join('')}
            </ul>
          </div>
          <div class="explainability-item">
            <h3>Why not Candidate #${target + 2}?</h3>
            <p class="muted">Lower-ranked or rejected candidates can be reviewed in the future with explicit rejection reasons, evidence provenance, and penalty explanations.</p>
          </div>
        </div>
      `;
    });
  });
}

async function loadDiseases() {
  try {
    const response = await fetch('/api/diseases');
    const data = await response.json();

    if (!response.ok) {
      diseaseList.innerHTML = `<p class="muted">${data.error || 'Unable to load disease catalog.'}</p>`;
      statusTag.textContent = 'Catalog error';
      return;
    }

    renderDiseases(data.diseases || []);
  } catch (error) {
    diseaseList.innerHTML = `<p class="muted">Unable to load disease catalog: ${error.message}</p>`;
    statusTag.textContent = 'Catalog error';
  }
}

async function analyzeCombination() {
  if (!selectedDiseases.size) {
    statusTag.textContent = 'Select diseases';
    return;
  }

  statusTag.textContent = 'Running';

  try {
    const response = await fetch('/api/combinations/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diseases: Array.from(selectedDiseases) }),
    });

    const data = await response.json();
    statusTag.textContent = response.ok ? 'Complete' : 'Error';

    if (!response.ok) {
      resultsContainer.innerHTML = `<p class="muted">${data.error || 'Request failed.'}</p>`;
      return;
    }

    renderResults(data);
    explainability.innerHTML = `
      <div class="explainability-list">
        <div class="explainability-item">
          <h3>Evidence panel</h3>
          <p class="muted">${data.metadata?.dataStatus === 'real_graph' ? 'Candidates are based on represented knowledge-graph relationships. ML DDI and synergy prediction are not applied.' : 'Demo fallback output is clearly labeled and should not be interpreted as graph evidence or clinical evidence.'}</p>
        </div>
      </div>
    `;
  } catch (error) {
    statusTag.textContent = 'Error';
    resultsContainer.innerHTML = `<p class="muted">Unable to reach the backend: ${error.message}</p>`;
  }
}

analyzeBtn.addEventListener('click', analyzeCombination);
loadDiseases();
