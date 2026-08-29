# Project Context: PolyMerge

## 1. Problem Statement

Patients managing multiple chronic, comorbid conditions — commonly hypertension, type 2 diabetes, and hyperlipidemia together — are typically prescribed several separate medications. This "polypharmacy" pattern creates compounding problems:

- **Low adherence:** pill burden (5+ tablets a day, at different times) causes patients to skip doses.
- **Cost and complexity:** more prescriptions mean more refills, more copays, and more room for error, particularly for elderly patients or in low-resource healthcare settings.
- **Undetected Drug-Drug Interactions (DDIs):** with many drugs prescribed independently (sometimes by different providers), no single person may be tracking the full interaction risk across the whole regimen.
- **Redundant mechanisms:** some prescribed drugs may have overlapping or complementary mechanisms that could, in principle, be consolidated.

A **polypill** — a single Fixed-Dose Combination (FDC) tablet containing multiple active pharmaceutical ingredients — addresses this directly by combining the needed drugs into one dose. This isn't a hypothetical: the **Polycap trial** (aspirin, a statin, and multiple antihypertensives in one pill) and the **PolyIran trial** both demonstrated that polypills can improve adherence and reduce cardiovascular events at population scale.

## 2. Why AI, Why Now

Manually screening every candidate drug combination for a disease cluster against known interaction data doesn't scale: for a cluster of *N* target diseases and a candidate pool of *M* drugs, the number of pairwise and higher-order interactions to check grows combinatorially. At the same time, large structured public datasets already exist — DrugBank, Hetionet, TWOSIDES/OFFSIDES, DrugCombDB — but none of them natively answer the question "what's the minimal safe drug set for this specific disease cluster?"

PolyMerge exists to close that gap: turn scattered pharmacological data into a queryable Knowledge Graph, learn interaction and synergy patterns with Graph Neural Networks, and use classical combinatorial optimization to surface candidate FDCs for expert review — faster than manual literature review, without replacing the human judgment that has to sign off on any real formulation.

## 3. Who This Is For

- **Primary users:** pharmaceutical researchers and pharmacists evaluating candidate FDC formulations during early-stage research.
- **Explicitly not for:** patients, or point-of-care clinical decision-making. Nothing PolyMerge outputs is validated for direct clinical use (see Section 8).

## 4. System Design Principles

- **Decision-support, not decision-making.** Every output is a candidate for expert review, never a final answer a patient or clinician should act on directly.
- **Deep learning scores, classical search decides.** GNNs handle interaction/synergy *scoring*; a set-cover / integer-programming layer handles *selection*. The GNN never directly outputs a "final" combination — its scores always pass through the combinatorial search and rule layer (see Overview doc, Section 5: Model & Algorithm Choices).
- **Hard-coded safety rules always win.** Absolute contraindications (e.g., MAOI + SSRI) are enforced as a backend-level check independent of any model score (`backend/src/rules/contraindications.js`) — a high model confidence score can never override a known-dangerous pairing.
- **Explainability is non-negotiable.** Any medical-adjacent prediction ships with a reasoning trace (GNNExplainer / attention visualization). An unexplained "trust the model" output is out of scope for this project.

## 5. Scope Boundaries (recap)

**In scope:** knowledge graph construction, DDI/synergy prediction, combination optimization, explainability.
**Out of scope:** autonomous prescribing, clinical validation/regulatory approval, physical/chemical manufacturing modeling of the pill itself.

See the full Overview & Scope document for the complete scope table.

## 6. Core Terminology

- **Polypill / Fixed-Dose Combination (FDC):** a single pill combining multiple active pharmaceutical ingredients.
- **Enteric / Multiparticulate Release:** a pill design where different drug layers or pellets dissolve at different points in the GI tract, based on pH.
- **DDI (Drug-Drug Interaction):** an adverse or beneficial effect that occurs when two or more drugs are taken together.
- **Knowledge Graph (KG):** a structured graph of entities (drugs, diseases, targets, side effects) and the relationships between them.
- **Link Prediction:** the ML task of predicting whether an edge (relationship) should exist between two nodes in a graph — used here for drug-disease and drug-drug relationships.
- **Set-Cover Problem:** a classical combinatorial optimization problem — here, finding the smallest drug set that "covers" (treats) every target disease.
- **GNNExplainer:** a technique for identifying which nodes/edges in a graph most influenced a GNN's prediction, used for explainability.

## 7. Data & Validation Strategy

**Primary data sources:** DrugBank (drug identities, targets, known DDIs), TWOSIDES/OFFSIDES (polypharmacy side effects), DrugCombDB (synergy scores), Hetionet (integrated biomedical KG), RxNorm/RxNav (standardized drug naming).

**Validation approach:** rather than validating in a vacuum, generated combinations are checked against real, published, clinically-tested polypill trials — Polycap and PolyIran — as a sanity check that the system's suggestions are directionally consistent with formulations that have already been through real trials.

## 8. Regulatory & Ethical Positioning

PolyMerge is pre-clinical research tooling. Its outputs are theoretical and bounded by the completeness and quality of the open-source datasets it's built on. Any path from a PolyMerge suggestion to a real polypill requires full clinical trials and FDA (or equivalent regional) regulatory approval — this system does not shortcut, replace, or substitute for that process.

## 9. Success Criteria for the MVP (end of Sprint 4)

- A complete pipeline works end to end: disease cluster input → KG-grounded GNN scoring → combinatorial search → ranked candidate FDC → explainability trace → UI display.
- At least one validated concordance between a PolyMerge-generated combination and a real published trial formulation (Polycap or PolyIran) for the chosen disease cluster.
- All hard-coded safety rules are enforced and demonstrably block at least one known contraindicated pair in a test case, regardless of model confidence.
