from app.services.set_cover_optimizer import greedy_set_cover, optimize_set_cover


def test_optimizer_selects_one_drug_covering_multiple_diseases():
    result = optimize_set_cover(
        ["drug-a", "drug-b"],
        ["disease-1", "disease-2"],
        {
            "drug-a": ["disease-1", "disease-2"],
            "drug-b": ["disease-1"],
        },
    )

    assert result["selectedDrugs"] == ["drug-a"]
    assert result["selectedDrugCount"] == 1
    assert result["coveredDiseaseIds"] == ["disease-1", "disease-2"]
    assert result["coverage"] == 1.0
    assert result["coverageMatrix"] == {
        "drug-a": ["disease-1", "disease-2"],
        "drug-b": ["disease-1"],
    }


def test_optimizer_respects_configured_drug_limit_and_preserves_uncovered_diseases():
    result = optimize_set_cover(
        ["drug-a", "drug-b"],
        ["disease-1", "disease-2"],
        {"drug-a": ["disease-1"], "drug-b": ["disease-2"]},
        config={"maxDrugCount": 1, "minimumCoverage": 1.0},
    )

    assert result["selectedDrugs"] == ["drug-a"]
    assert result["selectedDrugCount"] == 1
    assert result["uncoveredDiseaseIds"] == ["disease-2"]
    assert result["coverage"] == 0.5


def test_greedy_set_cover_ignores_coverage_outside_target_diseases():
    assert greedy_set_cover(
        ["drug-a", "drug-b"],
        ["disease-1"],
        coverage_by_drug={"drug-a": ["unrequested"], "drug-b": ["disease-1"]},
    ) == ["drug-b"]