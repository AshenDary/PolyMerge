from app.services.candidate_generator import generate_candidate_sets


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
