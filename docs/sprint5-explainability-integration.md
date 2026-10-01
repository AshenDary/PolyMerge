# Sprint 5: Candidate Comparison & Explainability Integration

## Objective

Integrate the final model output into PolyMerge candidate comparison and research-facing explainability **without mixing** predicted severity with graph evidence or deterministic rejection reasons.

## Key Principle: Separation of Evidence Channels

PolyMerge maintains **three distinct evidence channels** that must never be combined into a single "safety score":

### 1. Graph Evidence (Blue Channel)
- **Source**: Hetionet knowledge graph
- **Content**: Disease coverage, treatment paths, gene context, side effects
- **Interpretation**: Represents knowledge graph relationships, **not clinical efficacy**
- **Status Field**: `dataStatus` (`real_graph`, `demo`, `graph_unavailable`)

### 2. Deterministic Rules (Red/Green Channel)
- **Source**: Hard-coded safety rules (e.g., contraindications)
- **Content**: Acceptance/rejection decisions, violation messages
- **Interpretation**: Hard safety checks, **not comprehensive interaction database**
- **Status Field**: `status` (`accepted`, `rejected`)

### 3. ML Predictions (Purple Channel)
- **Source**: Trained ML model (Sprint 4 selected model)
- **Content**: Pair-level predicted DDI severity and model provenance
- **Interpretation**: Statistical estimates, **not clinical validation**
- **Status Field**: `mlStatus` (`applied`, `not_applied`)

## Candidate Comparison Structure

### CandidateComparison Object

```javascript
{
  candidateSetId: "candidate-001",
  rank: 1,
  drugs: ["lisinopril", "amlodipine", "metformin"],
  drugCount: 3,
  status: "accepted", // or "rejected"
  
  // GRAPH EVIDENCE SECTION
  graphEvidence: {
    treatedDiseaseIds: ["hypertension", "type-2-diabetes"],
    uncoveredDiseaseIds: [],
    coverage: 1.0,
    coverageDescription: "100% of requested diseases",
    treatmentPaths: [
      {
        pathId: "graph-path:a60e0433840b09f0eaa3b4a7",
        drugId: "Compound::DB00177",
        drugName: "Valsartan",
        diseaseId: "Disease::DOID:10763",
        diseaseName: "hypertension",
        relationship: "CtD",
        source: "Hetionet",
        graphVersion: "Hetionet v1.0 filtered PolyMerge fragment",
        evidenceType: "known"
      }
    ],
    geneContext: [ /* gene associations */ ],
    sideEffectContext: [ /* side effect associations */ ],
    provenance: {
      source: "Hetionet",
      version: "v1.0",
      dataStatus: "real_graph",
      timestamp: "2026-09-30T12:00:00Z"
    }
  },
  
  // DETERMINISTIC RULES SECTION
  rules: [
    {
      ruleId: "rule-accepted",
      type: "accepted",
      status: "accepted",
      message: "No configured deterministic hard-rule violation detected",
      affectedDrugs: [],
      source: "PolyMerge Safety Rules",
      stage: "backend_validation"
    }
  ],
  
  // ML PREDICTIONS SECTION
  mlPrediction: {
    status: "applied",
    pairs: [
      {
        drugPair: ["Compound::DB00177", "Compound::DB00331"],
        predictedSeverity: "Moderate",
        modelName: "RandomForestClassifier",
        modelVersion: "RandomForestClassifier-sprint5-v1-65e9834666ad19c5",
        inferenceStatus: "applied"
      }
    ]
  },
  
  // PRESENTATION HINTS
  presentation: {
    visualSeparation: {
      graphSection: "Graph Evidence",
      rulesSection: "Safety Rules",
      mlSection: "ML Predictions",
      note: "These sections must be visually distinct in UI"
    },
    statusIcon: "check-circle",
    statusColor: "green",
    coverageBadge: {
      text: "100% Coverage",
      color: "green"
    },
    warningLevel: "none",
    disclaimer: "Research use only. Not clinical guidance."
  },
  
  dataStatus: "real_graph",
  mlStatus: "applied"
}
```

## API Endpoints

### GET /api/candidate-sets/:id/explain

Returns explainability payload for a candidate set query.

**Query Parameters:**
- `format`: Response format
  - `detailed` (default): Full explanations with all sections
  - `comparison`: Table view for comparing multiple candidates
  - `visualization`: Graph visualization data
  - `structured`: Raw structured payload

**Response Example (format=detailed):**

```json
{
  "queryId": "query-12345",
  "diseaseIds": ["hypertension", "type-2-diabetes"],
  "candidates": [ /* array of CandidateComparison objects */ ],
  "detailedExplanations": [
    {
      "candidateId": "candidate-001",
      "rank": 1,
      "drugs": ["lisinopril", "metformin"],
      "status": "accepted",
      "sections": [
        {
          "title": "Graph Evidence",
          "type": "graph",
          "icon": "database",
          "color": "blue",
          "content": { /* formatted graph evidence */ },
          "disclaimer": "Based on knowledge graph relationships. Coverage measures representation, not clinical efficacy."
        },
        {
          "title": "Safety Rules",
          "type": "rules",
          "icon": "shield",
          "color": "green",
          "content": [ /* formatted rules */ ],
          "disclaimer": "Hard-coded safety checks. Not a comprehensive drug interaction database."
        },
        {
          "title": "ML Predictions",
          "type": "predictions",
          "icon": "cpu",
          "color": "purple",
          "content": { /* formatted predictions */ },
          "disclaimer": "Statistical estimates from research models. Not clinical validation."
        }
      ],
      "presentation": { /* UI hints */ },
      "overallDisclaimer": "Research decision-support only. All evidence channels require expert review."
    }
  ],
  "metadata": {
    "timestamp": "2026-09-30T12:00:00Z",
    "candidateCount": 5,
    "acceptedCount": 3,
    "rejectedCount": 2
  },
  "disclaimer": "Research decision-support only. Graph evidence, deterministic rules, and ML predictions are separate evidence channels that must not be combined into a single 'safety score'.",
  "limitations": [
    "Graph coverage measures representation in knowledge graph, not clinical efficacy",
    "Deterministic rules are hard-coded safety checks, not comprehensive drug interaction databases",
    "ML predictions are statistical estimates from research models, not clinical validation",
    "All evidence channels require expert review and appropriate clinical/regulatory validation"
  ]
}
```

## Frontend Integration Guidelines

### Visual Separation Requirements

1. **Use Distinct Colors**
   - Graph Evidence: Blue (#2196F3)
   - Safety Rules: Green (#4CAF50) for accepted, Red (#F44336) for rejected
   - ML Predictions: Purple (#9C27B0)

2. **Use Section Headers**
   - Clearly label each evidence channel
   - Include channel-specific disclaimers

3. **Use Separate UI Components**
   - Don't mix evidence types in the same card/panel
   - Use tabs, accordions, or columns to separate channels

4. **Never Combine Into Single Score**
   - Do not create: `safetyScore = 0.4*graph + 0.3*rules + 0.3*ml`
   - Do present: three separate evidence summaries

### Example UI Layout

```
┌─────────────────────────────────────────────────┐
│ Candidate #1: Lisinopril + Metformin           │
│ Status: Accepted                               │
├─────────────────────────────────────────────────┤
│ ┌──────────── Graph Evidence (Blue) ──────────┐│
│ │ Coverage: 100% of requested diseases         ││
│ │ Treatment paths: 2 known relationships       ││
│ │ Disclaimer: Represents KG, not efficacy      ││
│ └──────────────────────────────────────────────┘│
├─────────────────────────────────────────────────┤
│ ┌──────────── Safety Rules (Green) ───────────┐│
│ │ No configured deterministic hard-rule        ││
│ │ violation detected                           ││
│ │ Disclaimer: Hard-coded checks only           ││
│ └──────────────────────────────────────────────┘│
├─────────────────────────────────────────────────┤
│ ┌──────────── ML Predictions (Purple) ────────┐│
│ │ Pair: Valsartan to Metformin                 ││
│ │ Predicted Severity: Moderate                 ││
│ │ Model: RandomForestClassifier sprint5        ││
│ │ Disclaimer: Statistical estimate only        ││
│ └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

## Rejection Explanation

When a candidate is rejected, explain clearly:

```javascript
{
  "rejectionSummary": {
    "reason": "Deterministic rule violation",
    "ruleCount": 1
  },
  "details": [
    {
      "ruleType": "hard_contraindication",
      "message": "MAOI + SSRI: severe serotonin syndrome risk",
      "affectedDrugs": ["maoi", "ssri"],
      "source": "PolyMerge Safety Rules",
      "canOverride": false,
      "explanation": "This is a hard contraindication and cannot be overridden without clinical review."
    }
  ],
  "alternatives": {
    "message": "Consider accepted candidates or modify disease selection.",
    "showAcceptedCandidates": true
  },
  "disclaimer": "Rejection is based on deterministic rules, not ML predictions. Graph evidence is still available for research purposes."
}
```

## Graph Visualization

For evidence path visualization:

- **Nodes**: Drugs (green circles), Diseases (blue circles), Genes (purple circles)
- **Edges**: 
  - Solid lines: Known evidence
  - Dashed lines: Inferred evidence
  - Dotted lines: Context relationships
- **Disclaimer**: "Visualization shows graph relationships only. Not a clinical decision tree."

## ML Prediction Status

### mlStatus Values

- `"applied"`: ML model successfully generated predictions
- `"not_applied"`: Feature bridge or model serving unavailable; no prediction
  was emitted

### Handling Missing Predictions

When `mlStatus !== "applied"`:

```javascript
{
  "status": "not_available",
  "message": "ML predictions are unavailable for this candidate.",
  "pairs": []
}
```

Display in UI:
```
ML Predictions: Not Available
Graph evidence and safety rules remain available.
```

## Research Use Disclaimer

**Always display prominently:**

> **Research Use Only**
> 
> PolyMerge does not provide medical advice, prescriptions, or clinically validated safety guarantees. All evidence channels (graph, rules, ML) require expert review and appropriate clinical/regulatory validation.
> 
> - Graph coverage measures representation, not clinical efficacy
> - Safety rules are hard-coded checks, not comprehensive databases
> - ML predictions are statistical estimates, not clinical validation

## Dependencies

### Completed (Sprint 4)
- ✅ Model selection and comparison framework
- ✅ Feature contract and preprocessing pipeline
- ✅ Evaluation metrics and reporting

### Completed On Integration Branch (Sprint 5)
- Issue #42 (Ranee): Model serving API integration
- Issue #41 (Jared): Graph evidence/provenance handoff
- Issue #43 (Pamela): Explainability integration

### Future Work
- Evidence path explorer
- Additional comparative analysis tools

## Testing Recommendations

### Unit Tests

1. **Evidence Channel Separation**
   - Verify graph, rules, and ML sections are structurally distinct
   - Ensure no mixing of evidence types in payloads

2. **Formatting Functions**
   - Test `formatGraphEvidence()`, `formatRules()`, `formatMLPredictions()`
   - Verify correct disclaimer text for each channel

3. **Rejection Logic**
   - Test that rejected candidates include rejection details
   - Verify hard contraindications override other evidence

### Integration Tests

1. **API Endpoint**
   - Test `/api/candidate-sets/:id/explain` with all formats
   - Verify 404 for missing query IDs
   - Test format validation

2. **Full Pipeline**
   - Submit candidate set search
   - Retrieve explainability payload
   - Verify structure matches specification

### Frontend Tests

1. **Visual Separation**
   - Verify distinct colors for each channel
   - Check section headers and disclaimers present

2. **Rejection Display**
   - Test rejected candidate rendering
   - Verify rejection reasons are clear

3. **ML Status Handling**
   - Test display when `mlStatus = "not_available"`
   - Verify graceful degradation

## File Structure

```
backend/src/
├── explainability/
│   ├── types.js              # Type definitions and builders
│   └── presentation.js       # Formatting and presentation layer
├── rules/
│   └── contraindications.js  # Deterministic safety rules
└── server.js                 # API endpoints (updated)

docs/
└── sprint5-explainability-integration.md  # This document

frontend/
└── (future implementation)
```

## Definition of Done

- [x] Candidate comparison fields defined
- [x] Predicted DDI severity structure integrated with Ranee's API
- [x] Model/version metadata fields added
- [x] Deterministic rejection reasons separated
- [x] Graph treatment coverage separated
- [x] Graph evidence/provenance separated
- [x] Evidence-path presentation structure created
- [x] Graph visualization plan documented
- [x] Multi-drug candidate set comparison preserved
- [x] Rejected candidate reasons made explicit
- [x] Generic "safety score" avoided
- [x] Research-use wording added
- [x] Explainability fields documented
- [x] Frontend/static tests verify main-app wiring
- [x] Explainability payload aligns with backend contract

## Next Steps

1. Review repaired temporary Sprint 5 integration branch for #39 closeout.
2. Preserve the three-channel contract during Sprint 6 deployment work.
3. Expand UI tests if the static frontend becomes a richer application.

---

**Document Version**: 1.0
**Last Updated**: 2026-10-01
**Status**: Integrated on temporary Sprint 5 branch
**Issue**: #43
