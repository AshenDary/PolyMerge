# Explainability Integration

Sprint 5 explainability framework for candidate comparison without mixing evidence channels.

## Quick Start

### Backend API

```javascript
// Get explainability for a candidate set query
GET /api/candidate-sets/:queryId/explain?format=detailed

// Formats:
// - detailed: Full explanations with all sections
// - comparison: Table view for comparing candidates
// - visualization: Graph visualization data  
// - structured: Raw payload
```

### Frontend Integration

```html
<!-- Add explainability styles -->
<link rel="stylesheet" href="/frontend/explainability.css">

<!-- Add explainability script -->
<script src="/frontend/explainability.js"></script>

<!-- Container for rendering -->
<div id="explainability"></div>

<script>
  // Load and render explainability
  loadExplainability('query-12345', 'detailed');
</script>
```

## Architecture

### Three Evidence Channels

**CRITICAL**: These channels must remain separate. Never combine into a single score.

#### 1. Graph Evidence (Blue)
```javascript
{
  treatedDiseaseIds: string[],
  uncoveredDiseaseIds: string[],
  coverage: number,  // 0-1
  treatmentPaths: TreatmentPath[],
  geneContext: GeneAssociation[],
  sideEffectContext: SideEffectAssociation[],
  provenance: { source, version, dataStatus, timestamp }
}
```

**Interpretation**: Knowledge graph representation, **not** clinical efficacy

#### 2. Deterministic Rules (Green/Red)
```javascript
{
  ruleId: string,
  type: string,  // e.g., "hard_contraindication"
  status: "accepted" | "rejected",
  message: string,
  affectedDrugs: string[],
  source: string,
  stage: string
}
```

**Interpretation**: Hard safety checks, **not** comprehensive interaction database

#### 3. ML Predictions (Purple)
```javascript
{
  drugPair: [string, string],
  predictedSeverity: "Major" | "Moderate" | "Minor",
  modelName: string,
  modelVersion: string,
  inferenceStatus: "applied"
}
```

**Interpretation**: Statistical estimates, **not** clinical validation

## Usage Examples

### Example 1: Build Candidate Comparison

```javascript
import { buildCandidateComparison } from './types.js';

const candidateSet = {
  candidateSetId: 'candidate-001',
  rank: 1,
  drugs: ['lisinopril', 'metformin'],
  treatedDiseaseIds: ['hypertension', 'type-2-diabetes'],
  coverage: 1.0,
  graphEvidence: { source, graphVersion, paths },
  rejectionReasons: [],
  status: 'accepted',
  dataStatus: 'real_graph',
  mlStatus: 'applied',
};

const comparison = buildCandidateComparison(candidateSet);

// comparison now has separate channels:
// - comparison.graphEvidence
// - comparison.deterministicRules
// - comparison.mlPrediction
```

### Example 2: Create Explainability Response

```javascript
import { buildExplainabilityResponse } from './presentation.js';

const response = buildExplainabilityResponse(
  'query-123',
  ['hypertension', 'type-2-diabetes'],
  candidateSets,
  'detailed'  // or 'comparison', 'visualization', 'structured'
);

// Returns structured payload with:
// - Separated evidence channels
// - Formatted explanations
// - Disclaimers and limitations
```

### Example 3: Render in Frontend

```javascript
import { renderCandidateExplanation } from './explainability.js';

const container = document.getElementById('explainability-container');

for (const explanation of response.detailedExplanations) {
  renderCandidateExplanation(explanation, container);
}
```

## Visual Separation

### Color Coding

- **Graph Evidence**: Blue (#2196F3)
- **Safety Rules**: Green (#4CAF50) or Red (#F44336)
- **ML Predictions**: Purple (#9C27B0)

### Layout

Each candidate card should have three visually distinct sections:

```
┌─────────────────────────────────────────┐
│ Candidate #1: [Drugs]                   │
│ Status: Accepted                        │
├─────────────────────────────────────────┤
│ Graph Evidence (Blue Border)            │
│ • Coverage: 100%                         │
│ • Treatment paths: [...]                 │
│ Disclaimer: KG representation only       │
├─────────────────────────────────────────┤
│ Safety Rules (Green Border)              │
│ • No configured deterministic hard-rule  │
│   violation detected                     │
│ Disclaimer: Hard-coded checks only       │
├─────────────────────────────────────────┤
│ ML Predictions (Purple Border)           │
│ • Drug A to Drug B: Moderate             │
│ • Model: RandomForestClassifier          │
│ Disclaimer: Statistical estimates only   │
└─────────────────────────────────────────┘
```

## Dependencies

### Completed
- ✅ Type definitions and builders
- ✅ Presentation layer
- ✅ API endpoint
- ✅ Frontend reference implementation
- ✅ Visual styles
- ✅ Tests

### Future
- Evidence path explorer
- Additional comparative analysis tools

## Testing

### Run Tests

```bash
npm test backend/tests/explainability.test.js
```

### Manual Testing

1. Start backend: `npm run dev`
2. Submit candidate set search: `POST /api/candidate-sets/search`
3. Get explainability: `GET /api/candidate-sets/:id/explain?format=detailed`
4. Verify three separate channels in response
5. Check frontend rendering with visual separation

## Common Issues

### Issue: ML predictions are empty

**Cause**: `mlStatus` is "not_applied" or "unavailable"

**Solution**: This is expected when the candidate pair cannot be represented by
the reviewed feature bridge or when model serving is unavailable. Graph evidence
and rules still work.

### Issue: Graph evidence is minimal

**Cause**: Insufficient graph data or coverage

**Solution**: Check `dataStatus` field. If "demo" or "graph_unavailable", graph data source is not fully available.

### Issue: All candidates rejected

**Cause**: Deterministic rules are triggering

**Solution**: Check `rules` array for rejection reasons. Common: hard_contraindication for MAOI+SSRI.

## Best Practices

### DO

- Keep three channels visually separate in UI
- Include channel-specific disclaimers
- Show "Research use only" prominently
- Handle missing ML predictions gracefully
- Test with various `mlStatus` values

### DON'T

- Combine channels into single "safety score"
- Mix graph evidence with ML predictions
- Present ML output as clinical advice
- Hide rejection reasons
- Omit disclaimers

## Documentation

- **Full Spec**: `docs/sprint5-explainability-integration.md`
- **API Docs**: `docs/api.md`
- **Issue**: #43 / Sprint 5 integration branch

## Contact

For questions or issues with explainability integration, refer to Issue #43 and
the Sprint 5 integration branch notes.
