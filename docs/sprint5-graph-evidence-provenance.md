# Sprint 5 Graph Evidence and Provenance

## Objective

Provide traceable graph evidence for candidate results while keeping represented
knowledge-graph relationships separate from deterministic safety rules and ML
predictions.

## Existing Graph Sources

PolyMerge uses the Hetionet v1.0 filtered PolyMerge fragment loaded into Neo4j.
Stable compound, disease, gene, and side-effect IDs are retained from that
fragment. This handoff does not add literature citations or clinical sources
that the fragment does not contain.

## Evidence Path Contract

Candidate and candidate-set payloads expose `graphEvidence.source`,
`graphEvidence.graphVersion`, and `graphEvidence.paths`. Every path contains a
stable `pathId`, semantic type, source compound, relationship type and metaedge,
target entity, and path-level provenance.

The ID is `graph-path:` plus the first 24 hexadecimal characters of SHA-256 over
the compact JSON array `[source, compound ID, relationship type, target entity
ID, graph version]`. Therefore the same represented relationship in the same
graph version has the same ID. Paths are deduplicated by ID and sorted by ID.

The existing `evidence`, `targets`, `sideEffects`, `treatedDiseaseIds`,
`coverage`, and `comparison` fields remain available for compatibility.

## Treatment Paths

Each represented `Compound -> CtD -> Disease` relationship becomes one
`treatment` path. Every disease in a graph-derived drug's `treatedDiseaseIds`
has a matching `CtD` path. Coverage is based only on represented `CtD` edges and
does not state clinical efficacy.

## Gene Context Paths

Represented `CbG`, `CuG`, and `CdG` relationships become `gene_context` paths
from a compound to a gene. They provide graph context; they do not prove
treatment efficacy or a drug-drug interaction.

## Side-Effect Context Paths

Represented `CcSE` relationships become `side_effect_context` paths from a
compound to a side effect. They are not converted into interaction severity,
contraindications, or clinical safety conclusions.

## Candidate-Set Aggregation

A candidate set contains the union of all member-drug paths. Identical path IDs
are retained once, ordering is deterministic, and every path keeps its
originating compound ID. No paths are joined into synthetic multi-hop claims.

`comparison.drugs[].evidencePathIds` identifies the candidate-level paths owned
by each drug without duplicating full path payloads.

## Provenance

Candidate-level graph context identifies Hetionet and the graph version. Each
path repeats source, graph version, relationship/metaedge, and evidence type so
it remains interpretable when selected independently.

## CrC Boundary

`CrC` means Compound resembles Compound. It is resemblance context only and is
never emitted as treatment, DDI truth, severity, safety evidence,
contraindication, or clinical interaction evidence. This work does not alter its
existing use in the frozen Sprint 3 feature contract.

## Missing-Evidence Semantics

Missing gene or side-effect context is represented by an empty path subset; no
evidence is fabricated. A drug remains a valid graph-derived treatment
candidate when its represented `CtD` relationship exists. Path absence means
the relationship is not represented in this fragment, not that it is
biologically false.

## Pamela #43 Handoff

Issue #43 can render `graphEvidence.paths` by semantic type, follow per-drug
`evidencePathIds`, and display source and graph version. It must keep graph
evidence visually and semantically separate from `rejectionReasons` and future
`mlPrediction` output. It must not infer new biomedical claims from path presence
or absence.

## Limitations

These paths trace represented graph relationships. They are not clinical
validation, causal proof, treatment efficacy, DDI severity, or a safety
recommendation. The payload includes no fabricated publication provenance, no
model prediction, and no change to deterministic hard-safety behavior.
