from app.services.candidate_generator import generate_candidate_sets


def _path(path_id, drug_id, target_id):
    return {
        "pathId": path_id,
        "semanticType": "treatment",
        "sourceEntity": {"id": drug_id, "name": drug_id, "kind": "Compound"},
        "relationship": {"type": "CtD", "metaedge": "CtD"},
        "targetEntity": {"id": target_id, "name": target_id, "kind": "Disease"},
        "provenance": {
            "source": "Hetionet",
            "graphVersion": "Hetionet v1.0 filtered PolyMerge fragment",
            "evidenceType": "known",
        },
    }


def test_generate_candidate_sets_builds_multi_drug_coverage_and_comparison():
    candidates = generate_candidate_sets(
        [
            {
                "drugId": "drug-a",
                "drugName": "Drug A",
                "treatedDiseaseIds": ["disease-1"],
                "treats": ["Disease 1"],
                "evidence": [{"source": "Hetionet", "targetId": "disease-1"}],
            },
            {
                "drugId": "drug-b",
                "drugName": "Drug B",
                "treatedDiseaseIds": ["disease-2"],
                "treats": ["Disease 2"],
                "evidence": [{"source": "Hetionet", "targetId": "disease-2"}],
            },
        ],
        target_disease_ids=["disease-1", "disease-2"],
        max_drug_count=2,
    )

    multi_drug = next(
        candidate
        for candidate in candidates
        if candidate["candidateSetId"] == "candidate-set:drug-a+drug-b"
    )
    assert multi_drug["status"] == "accepted"
    assert multi_drug["drugs"] == ["drug-a", "drug-b"]
    assert multi_drug["treatedDiseaseIds"] == ["disease-1", "disease-2"]
    assert multi_drug["coverage"] == 1.0
    assert len(multi_drug["evidence"]) == 2
    assert multi_drug["comparison"]["drugCount"] == 2


def test_generate_candidate_sets_marks_hard_safety_rejections_before_optimization():
    candidates = generate_candidate_sets(
        [
            {
                "drugId": "maoi",
                "drugName": "MAOI",
                "treatedDiseaseIds": ["disease-1"],
                "treats": ["Disease 1"],
                "evidence": [],
            },
            {
                "drugId": "ssri",
                "drugName": "SSRI",
                "treatedDiseaseIds": ["disease-2"],
                "treats": ["Disease 2"],
                "evidence": [],
            },
        ],
        target_disease_ids=["disease-1", "disease-2"],
        max_drug_count=2,
    )

    rejected = next(
        candidate
        for candidate in candidates
        if candidate["candidateSetId"] == "candidate-set:maoi+ssri"
    )
    assert rejected["status"] == "rejected"
    assert rejected["reason"]["type"] == "hard_contraindication"
    assert rejected["rejectionReasons"][0]["stage"] == "pre_optimization"


def test_generate_candidate_sets_respects_configured_max_drug_count():
    candidates = generate_candidate_sets(
        [
            {"drugId": "drug-a", "drugName": "Drug A", "treatedDiseaseIds": ["disease-1"]},
            {"drugId": "drug-b", "drugName": "Drug B", "treatedDiseaseIds": ["disease-2"]},
            {"drugId": "drug-c", "drugName": "Drug C", "treatedDiseaseIds": ["disease-3"]},
        ],
        target_disease_ids=["disease-1", "disease-2", "disease-3"],
        max_drug_count=2,
    )

    assert candidates
    assert max(candidate["drugCount"] for candidate in candidates) == 2
    assert all(len(candidate["drugs"]) <= 2 for candidate in candidates)


def test_candidate_sets_deduplicate_and_order_member_graph_paths():
    path_a = _path("graph-path:a", "drug-a", "disease-1")
    path_b = _path("graph-path:b", "drug-b", "disease-2")
    candidates = generate_candidate_sets(
        [
            {
                "drugId": "drug-a",
                "drugName": "Drug A",
                "treatedDiseaseIds": ["disease-1"],
                "graphEvidence": {"paths": [path_b, path_a, path_a]},
            },
            {
                "drugId": "drug-b",
                "drugName": "Drug B",
                "treatedDiseaseIds": ["disease-2"],
                "graphEvidence": {"paths": [path_b]},
            },
        ],
        target_disease_ids=["disease-1", "disease-2"],
        max_drug_count=2,
    )
    combined = next(candidate for candidate in candidates if candidate["drugCount"] == 2)

    assert [path["pathId"] for path in combined["graphEvidence"]["paths"]] == [
        "graph-path:a",
        "graph-path:b",
    ]
    comparison = {drug["drugId"]: drug for drug in combined["comparison"]["drugs"]}
    assert comparison["drug-a"]["evidencePathIds"] == ["graph-path:a"]
    assert comparison["drug-b"]["evidencePathIds"] == ["graph-path:b"]
    assert combined["interactionRisk"] is None
    assert combined["synergyScore"] is None


def test_missing_optional_graph_context_produces_empty_paths_and_keeps_schema():
    [candidate] = generate_candidate_sets(
        [{"drugId": "drug-a", "drugName": "Drug A", "treatedDiseaseIds": []}],
        target_disease_ids=["disease-1"],
        max_drug_count=1,
    )

    assert candidate["graphEvidence"]["paths"] == []
    assert candidate["evidence"] == []
    assert candidate["targets"] == []
    assert candidate["sideEffects"] == []


def test_graph_paths_do_not_change_deterministic_rejection_reasons():
    candidates = generate_candidate_sets(
        [
            {
                "drugId": "maoi",
                "drugName": "MAOI",
                "treatedDiseaseIds": ["disease-1"],
                "graphEvidence": {"paths": [_path("graph-path:a", "maoi", "disease-1")]},
            },
            {
                "drugId": "ssri",
                "drugName": "SSRI",
                "treatedDiseaseIds": ["disease-2"],
                "graphEvidence": {"paths": [_path("graph-path:b", "ssri", "disease-2")]},
            },
        ],
        target_disease_ids=["disease-1", "disease-2"],
        max_drug_count=2,
    )
    rejected = next(candidate for candidate in candidates if candidate["drugCount"] == 2)

    assert rejected["status"] == "rejected"
    assert rejected["rejectionReasons"][0]["type"] == "hard_contraindication"
    assert rejected["rejectionReasons"][0]["stage"] == "pre_optimization"
