/**
 * Sprint 5 Explainability Frontend Integration
 * 
 * Example implementation showing how to display candidate comparisons
 * with clear visual separation of evidence channels.
 * 
 * IMPORTANT: This is a reference implementation. Actual UI may vary.
 */

/**
 * Render a single candidate with separated evidence channels
 */
function renderCandidateExplanation(explanation, container) {
  const { candidateId, rank, drugs, status, sections, presentation } = explanation;
  
  const card = document.createElement('article');
  card.className = `candidate-explanation candidate-${status}`;
  card.dataset.candidateId = candidateId;
  
  // Header
  const header = document.createElement('div');
  header.className = 'candidate-header';
  header.innerHTML = `
    <h3>
      <span class="rank-badge">#${rank}</span>
      Candidate ${rank}
      <span class="status-badge status-${status}">
        ${status === 'accepted' ? '✓ Accepted' : '✗ Rejected'}
      </span>
    </h3>
    <div class="drug-list">
      ${drugs.map((drug) => `<span class="drug-chip">${drug}</span>`).join('')}
    </div>
  `;
  card.appendChild(header);
  
  // Evidence Channels (visually separated)
  const sectionsContainer = document.createElement('div');
  sectionsContainer.className = 'evidence-sections';
  
  for (const section of sections) {
    const sectionDiv = document.createElement('div');
    sectionDiv.className = `evidence-section section-${section.type}`;
    sectionDiv.style.borderLeft = `4px solid ${getSectionColor(section.color)}`;
    
    sectionDiv.innerHTML = `
      <div class="section-header" style="color: ${getSectionColor(section.color)}">
        <span class="section-icon">${getSectionIcon(section.icon)}</span>
        <h4>${section.title}</h4>
      </div>
      <div class="section-content">
        ${renderSectionContent(section)}
      </div>
      <div class="section-disclaimer">
        <small>⚠️ ${section.disclaimer}</small>
      </div>
    `;
    
    sectionsContainer.appendChild(sectionDiv);
  }
  
  card.appendChild(sectionsContainer);
  
  // Overall disclaimer
  const disclaimer = document.createElement('div');
  disclaimer.className = 'overall-disclaimer';
  disclaimer.innerHTML = `
    <strong>Research Use Only:</strong> ${explanation.overallDisclaimer}
  `;
  card.appendChild(disclaimer);
  
  container.appendChild(card);
}

/**
 * Render section content based on type
 */
function renderSectionContent(section) {
  switch (section.type) {
    case 'graph':
      return renderGraphEvidenceContent(section.content);
    case 'rules':
      return renderRulesContent(section.content);
    case 'predictions':
      return renderPredictionsContent(section.content);
    default:
      return '<p>Unknown section type</p>';
  }
}

/**
 * Render graph evidence section
 */
function renderGraphEvidenceContent(content) {
  if (!content) return '<p>No graph evidence available</p>';
  
  return `
    <div class="graph-summary">
      <div class="metric">
        <span class="metric-label">Coverage:</span>
        <span class="metric-value">${content.summary?.coverage ?? 'N/A'}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Treated Diseases:</span>
        <span class="metric-value">${content.summary?.treatedCount ?? 0}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Uncovered:</span>
        <span class="metric-value">${content.summary?.uncoveredCount ?? 0}</span>
      </div>
    </div>
    
    ${content.treatmentPaths && content.treatmentPaths.length > 0 ? `
      <div class="treatment-paths">
        <h5>Treatment Paths:</h5>
        <ul>
          ${content.treatmentPaths.map((path) => `
            <li>
              <span class="evidence-type evidence-${path.evidenceType}">
                ${path.evidenceType === 'known' ? '●' : '○'}
              </span>
              ${path.description}
              <small>(${path.source})</small>
            </li>
          `).join('')}
        </ul>
      </div>
    ` : ''}
    
    <div class="graph-provenance">
      <small>Source: ${content.provenance?.source} ${content.provenance?.version}</small>
    </div>
  `;
}

/**
 * Render deterministic rules section
 */
function renderRulesContent(rules) {
  if (!rules || rules.length === 0) {
    return '<p>No rule evaluations available</p>';
  }
  
  return `
    <div class="rules-list">
      ${rules.map((rule) => `
        <div class="rule-item rule-${rule.status}">
          <div class="rule-header">
            <span class="rule-icon">${rule.status === 'accepted' ? '✓' : '✗'}</span>
            <strong>${rule.type}</strong>
          </div>
          <p>${rule.message}</p>
          ${rule.affectedDrugs && rule.affectedDrugs.length > 0 ? `
            <div class="affected-drugs">
              Affected: ${rule.affectedDrugs.join(', ')}
            </div>
          ` : ''}
          <div class="rule-source">
            <small>Source: ${rule.source}</small>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

/**
 * Render ML predictions section
 */
function renderPredictionsContent(content) {
  if (!content || content.status === 'not_available') {
    return `
      <div class="predictions-unavailable">
        <p>${content?.message ?? 'ML predictions not available'}</p>
        <small>Graph evidence and safety rules remain available.</small>
      </div>
    `;
  }
  
  return `
    <div class="predictions-list">
      ${content.pairs.map((pred) => `
        <div class="prediction-item prediction-${pred.visualStyle}">
          <div class="prediction-header">
            <strong>${pred.drugs[0]} ↔ ${pred.drugs[1]}</strong>
            <span class="severity-badge severity-${pred.severity?.toLowerCase()}">
              ${pred.severity ?? 'N/A'}
            </span>
          </div>
          
          ${pred.probabilities ? `
            <div class="probability-bars">
              <div class="prob-bar">
                <span class="prob-label">Major:</span>
                <div class="prob-bar-fill" style="width: ${(pred.probabilities.Major ?? 0) * 100}%"></div>
                <span class="prob-value">${((pred.probabilities.Major ?? 0) * 100).toFixed(0)}%</span>
              </div>
              <div class="prob-bar">
                <span class="prob-label">Moderate:</span>
                <div class="prob-bar-fill" style="width: ${(pred.probabilities.Moderate ?? 0) * 100}%"></div>
                <span class="prob-value">${((pred.probabilities.Moderate ?? 0) * 100).toFixed(0)}%</span>
              </div>
              <div class="prob-bar">
                <span class="prob-label">Minor:</span>
                <div class="prob-bar-fill" style="width: ${(pred.probabilities.Minor ?? 0) * 100}%"></div>
                <span class="prob-value">${((pred.probabilities.Minor ?? 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
          ` : ''}
          
          <div class="prediction-meta">
            <small>
              Model: ${pred.model?.name ?? 'N/A'} ${pred.model?.version ?? ''}
              ${pred.confidence ? ` | Confidence: ${(pred.confidence * 100).toFixed(0)}%` : ''}
            </small>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

/**
 * Render comparison table for multiple candidates
 */
function renderComparisonTable(comparisonView, container) {
  const { headers, rows } = comparisonView.comparisonTable;
  
  const table = document.createElement('table');
  table.className = 'comparison-table';
  
  // Headers
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      ${headers.map((header) => `<th>${header}</th>`).join('')}
    </tr>
  `;
  table.appendChild(thead);
  
  // Rows
  const tbody = document.createElement('tbody');
  for (const row of rows) {
    const tr = document.createElement('tr');
    tr.className = `row-${row.visualStyle}`;
    tr.innerHTML = `
      <td class="rank-cell">#${row.rank}</td>
      <td class="drugs-cell">${row.drugs}</td>
      <td class="coverage-cell">
        <span class="coverage-badge">${row.coverage}</span>
      </td>
      <td class="status-cell">
        <span class="status-badge status-${row.status}">${row.status}</span>
      </td>
      <td class="rules-cell">${row.rulesStatus}</td>
      <td class="ml-cell">${row.mlStatus}</td>
    `;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  
  container.appendChild(table);
}

/**
 * Helper: Get section color
 */
function getSectionColor(color) {
  const colors = {
    blue: '#2196F3',
    green: '#4CAF50',
    red: '#F44336',
    purple: '#9C27B0',
  };
  return colors[color] || '#666';
}

/**
 * Helper: Get section icon
 */
function getSectionIcon(icon) {
  const icons = {
    database: '🗄️',
    shield: '🛡️',
    cpu: '🧠',
  };
  return icons[icon] || '📊';
}

/**
 * Fetch and render explainability for a query
 */
async function loadExplainability(queryId, format = 'detailed') {
  const container = document.getElementById('explainability-container');
  container.innerHTML = '<p>Loading explainability...</p>';
  
  try {
    const response = await fetch(`/api/candidate-sets/${queryId}/explain?format=${format}`);
    
    if (!response.ok) {
      throw new Error(`Failed to load explainability: ${response.status}`);
    }
    
    const data = await response.json();
    container.innerHTML = '';
    
    // Render based on format
    if (format === 'detailed' && data.detailedExplanations) {
      for (const explanation of data.detailedExplanations) {
        renderCandidateExplanation(explanation, container);
      }
    } else if (format === 'comparison' && data.comparisonView) {
      renderComparisonTable(data.comparisonView, container);
    } else {
      container.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    }
    
    // Add overall disclaimer
    if (data.disclaimer) {
      const disclaimer = document.createElement('div');
      disclaimer.className = 'global-disclaimer';
      disclaimer.innerHTML = `<strong>Important:</strong> ${data.disclaimer}`;
      container.appendChild(disclaimer);
    }
  } catch (error) {
    container.innerHTML = `<p class="error">Error loading explainability: ${error.message}</p>`;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    renderCandidateExplanation,
    renderComparisonTable,
    loadExplainability,
  };
}
