# Final Demo Guide

## Before Presentation

1. Use [Local Setup](LOCAL_SETUP.md); start the existing reviewed Neo4j database.
2. Run Start-PolyMerge. Wait for **PolyMerge is ready.** and note its actual URLs.
3. Run `python3.11 scripts/check_demo_readiness.py` (Windows: `py -3.11`).
   This verifies dependencies, model SHA-256, complete graph identity and services.
4. Open Streamlit and confirm the iframe actually renders. Check the disease
   catalog. Open the printed direct Fastify URL as a backup tab.
5. Run the scenario below once. Record a real rehearsal with visible data and
   date; prepare it as a clearly labeled recording, never as fake live output.
6. Keep power connected and prevent sleep. Keep launcher and log locations handy.
   Do not update packages, graph data or model immediately before the defense.

## Live Walkthrough

1. On Home, state the objective: explore existing-drug combinations worth
   researching for selected diseases while making the evidence gaps visible.
2. Select **hypertension** (`Disease::DOID:10763`) and
   **type 2 diabetes mellitus** (`Disease::DOID:9352`).
3. Choose Analyze Candidates. Explain elapsed time; do not describe it as a
   percentage-complete scientific pipeline.
4. Remain on Analyze after completion. Review the full-response summary,
   prediction availability and expandable configured-rule counts.
5. Explicitly choose Review Candidates. Explain pagination and backend rank order.
6. Find **Valsartan + Esmolol**
   (`Compound::DB00177 + Compound::DB00187`), verified as an ML-applied
   multi-drug candidate in the preserved two-disease fixture. Locate by names/IDs,
   not a promised rank or severity; confirm availability in the actual run.
7. Open Understand Result. Show represented treatment connections and their
   provenance, then separate configured-rule applicability from graph coverage.
8. Show the real pair prediction and model metadata. Major/Moderate/Minor
   describe the model's DDInter severity classification, not a clinical verdict.
9. Switch Researcher View. Show IDs, paths, mapping coverage and the ranking
   explanation. Changing view does not rerun the model.
10. Read Research Takeaway: what the candidate contributes to the research goal,
    which evidence is available and what still needs investigation.
11. Visit Model Analysis. Explain the three-model comparison and preserved
    evaluation; the page does not train or reevaluate on the test set.
12. Finish with limitations. Reset with New Simulation and show the previous
    selection/result disappears. Never present an accepted candidate as safe.

## Short Defense Answers

- **Why Random Forest?** It had the best mean Macro F1 under the fixed training-only
  comparison, not because tree models guarantee biomedical validity.
- **Why three algorithms?** Logistic Regression, Random Forest and Histogram
  Gradient Boosting provide traditional baselines under the same folds and
  preprocessing contract.
- **What are the 55 features?** The frozen pair representation includes molecular
  descriptors and symmetric graph summaries/coverage information. Missing mappings
  are represented explicitly; features are not the severity labels.
- **What is graph coverage?** The fraction of selected diseases connected by
  represented treatment edges, not the probability of treatment success.
- **What do the severity classes mean?** Learned categories from curated DDInter
  interaction labels. They are not a complete patient-specific safety judgment.
- **Why are some predictions unavailable?** A pair may not map to the frozen
  feature bridge. A single drug has no drug pair. No severity is invented.
- **Why incomplete rule mappings?** Only reviewed positive memberships were
  accepted. Unmapped drugs are unknown, not confirmed nonmembers.
- **Why not synergy?** There is no therapeutic-synergy target or validated
  formulation model. Severity classification answers a different question.
- **Why local?** Public deployment was not required; reviewed free-tier resource
  constraints reduced reliability. Local operation preserves the original model
  and graph without paid infrastructure. It does not waive security findings.

## Recovery and Recording

If only Streamlit fails, use the printed direct Fastify frontend URL. If a required
service fails, stop the supervisor, inspect `.polymerge/logs/`, fix the cause and
restart the whole managed application stack. Neo4j is intentionally not stopped.
Check ML/backend `/ready` and rerun readiness before continuing.

For occupied ports, choose new ports through the shared supervisor; never kill an
unknown listener. For graph/model failures use the trusted assets, not a fallback
backend. Save private logs before restarting and redact them before sharing.
Repeat the same disease IDs and candidate names for a consistent demonstration.

Recording checklist: Home/objective, disease selection, completed Analyze,
explicit Review, supported pair, all three evidence channels, Research Takeaway,
Model Analysis, limitations and reset. Label the recording as a prior real run.
No recording has been fabricated or automatically produced by this guide.

Final desktop/mobile, keyboard, console, favicon and iframe acceptance follows
[the UI checklist](sprint6-guided-demo.md). Read
[the finalization audit](audits/local-demo-finalization.md) before claiming that
native Windows or browser acceptance is complete.
