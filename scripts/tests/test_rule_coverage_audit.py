"""Coverage reports must distinguish pool replacement from changed predictions."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_rule_coverage import compare, summarize


class RuleCoverageAuditTests(unittest.TestCase):
    def test_counts_candidates_not_pairs(self) -> None:
        candidate = {"candidateSetId": "a", "rank": 1, "drugs": ["x", "y", "z"],
                     "status": "accepted", "mlStatus": "partial", "mlPrediction": {"pairs": [{}, {}]},
                     "ruleEvaluation": {"status": "partially_evaluated", "rules": [{"status": "partially_evaluated"}]}}
        result = summarize({"candidateSets": [candidate]})
        self.assertEqual(result["candidatesWithPredictions"], 1)
        self.assertEqual(result["ruleStatuses"], {"partially_evaluated": 1})

    def test_pool_change_does_not_claim_shared_prediction_change(self) -> None:
        a = {"candidateSetId": "a", "rank": 1, "drugs": ["x"], "mlStatus": "not_applied"}
        b = {"candidateSetId": "b", "rank": 2, "drugs": ["y"]}
        c = {"candidateSetId": "c", "rank": 2, "drugs": ["z"]}
        result = compare({"candidateSets": [a, b]}, {"candidateSets": [a, c]})
        self.assertEqual(result["sharedCandidates"], 1)
        self.assertTrue(result["sharedEvidenceAndPredictionsUnchanged"])
        self.assertEqual(result["removedCandidates"], [{"id": "b", "drugs": ["y"]}])
        changed = compare({"candidateSets": [a]}, {"candidateSets": [{**a, "mlStatus": "applied"}]})
        self.assertFalse(changed["sharedEvidenceAndPredictionsUnchanged"])
