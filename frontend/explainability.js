/**
 * Structured explainability API client used by the dashboard.
 * Rendering stays in app.js so candidate cards and evidence channels share
 * the same layout, status handling, and escaping rules.
 */
(() => {
  async function fetchStructured(queryId) {
    if (!queryId) throw new Error('A candidate search ID is required.');

    const response = await fetch(
      `/api/candidate-sets/${encodeURIComponent(queryId)}/explain?format=structured`,
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error ?? `Explainability request failed (${response.status}).`);
    }
    return data;
  }

  window.PolyMergeExplainability = Object.freeze({ fetchStructured });
})();
