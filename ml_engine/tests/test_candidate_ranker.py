from app.services.candidate_ranker import rank_candidates


def test_rank_candidates_prioritizes_accepted_coverage_and_fewer_drugs():
    ranked = rank_candidates(
        [
            {
                "candidateSetId": "wide-rejected",
                "status": "rejected",
                "coverage": 1.0,
                "confidence": 1.0,
                "drugCount": 1,
            },
            {
                "candidateSetId": "lower-coverage",
                "status": "accepted",
                "coverage": 0.5,
                "confidence": 1.0,
                "drugCount": 1,
            },
            {
                "candidateSetId": "wide-compact",
                "status": "accepted",
                "coverage": 1.0,
                "confidence": 0.7,
                "drugCount": 1,
            },
            {
                "candidateSetId": "wide-larger",
                "status": "accepted",
                "coverage": 1.0,
                "confidence": 0.9,
                "drugCount": 2,
            },
        ]
    )

    assert [candidate["candidateSetId"] for candidate in ranked] == [
        "wide-compact",
        "wide-larger",
        "lower-coverage",
        "wide-rejected",
    ]
    assert [candidate["rank"] for candidate in ranked] == [1, 2, 3, 4]
