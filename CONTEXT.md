# Project Context: PolyMerge

PolyMerge is a decision-support system designed to accelerate the discovery of safe, effective "polypills" (Fixed-Dose Combinations).

Currently, patients with comorbidities take multiple separate pills, leading to low adherence and high risks of adverse Drug-Drug Interactions (DDIs). This system aggregates pharmacological data into a Knowledge Graph (Neo4j) and utilizes Graph Neural Networks (GNNs) to predict interaction safety. A combinatorial search algorithm then identifies the minimal optimal drug set for a given cluster of diseases.

This is a formulation-screening tool for researchers, not an autonomous prescribing system.
