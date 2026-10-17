"""Read-only canonical availability probe; writes local evidence, not graph data."""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_engine"))
from app.services.ddi_feature_builder import PairFeatureBuilder, PairFeatureUnavailableError
from app.utils.neo4j_client import Neo4jClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3002")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    builder = PairFeatureBuilder()
    client = Neo4jClient()
    try:
        graph = {
            "relationships": client.query("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count"),
            "classes": client.query("MATCH (p)-[:PCiC]->(c:Compound) RETURN p.id AS classId, p.name AS className, c.id AS compoundId, c.name AS compoundName ORDER BY classId, compoundId"),
        }
    finally:
        client.close()
    (args.output / "graph.json").write_text(json.dumps(graph, indent=2))
    report = []
    for scenario, ids in [
        ("one", ["Disease::DOID:10763"]),
        ("two", ["Disease::DOID:10763", "Disease::DOID:9352"]),
        ("alternative", ["Disease::DOID:3393", "Disease::DOID:1936"]),
        ("no_treatments", ["Disease::DOID:8398", "Disease::DOID:7148"]),
    ]:
        start = time.perf_counter()
        request = Request(args.url + "/api/candidate-sets/search", data=json.dumps({"diseaseIds": ids}).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=180) as response:
            result = json.load(response)
            http = response.status
        elapsed = (time.perf_counter() - start) * 1000
        (args.output / f"{scenario}.json").write_text(json.dumps(result))
        if args.baseline:
            before = json.loads((args.baseline / f"{scenario}.json").read_text())
            assert scientific_payload(before) == scientific_payload(result), f"Scientific output changed: {scenario}"
        with urlopen(args.url + "/api/candidate-sets/" + result["queryId"] + "/explain?format=detailed") as response:
            explanation = json.load(response)
            explain_http = response.status
        (args.output / f"{scenario}-explain.json").write_text(json.dumps(explanation))
        pair_failures = []
        for candidate in result["candidateSets"]:
            for pair in combinations(sorted(candidate["drugs"]), 2):
                try:
                    builder.build_features(*pair)
                except PairFeatureUnavailableError as error:
                    pair_failures.append({"candidateSetId": candidate["candidateSetId"], "pair": pair, "reason": str(error)})
        candidates = result["candidateSets"]
        row = {"scenario": scenario, "diseaseIds": ids, "http": http, "explain_http": explain_http,
               "ms": elapsed, "candidateCount": len(candidates),
               "mlStatuses": dict(Counter(c["mlStatus"] for c in candidates)),
               "ruleApplicability": dict(Counter(c.get("ruleEvaluation", {}).get("status", "unreported") for c in candidates)),
               "rules": dict(Counter(c["status"] for c in candidates)),
               "drugCounts": dict(Counter(c["drugCount"] for c in candidates)),
               "coverage": dict(Counter(str(c["coverage"]) for c in candidates)),
               "appliedPairs": sum(len(c.get("mlPrediction", {}).get("pairs", [])) for c in candidates),
               "pairFailures": pair_failures,
               "metadata": result["metadata"]}
        report.append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in ("metadata", "pairFailures")}))
        print("unsupported pair occurrences:", len(pair_failures))
    (args.output / "report.json").write_text(json.dumps(report, indent=2))


def scientific_payload(value: object) -> object:
    # Only request bookkeeping and newly added availability metadata are excluded.
    excluded = {"queryId", "timestamp", "ruleEvaluation", "reasonCode", "unavailablePairs", "missingDrugIds"}
    if isinstance(value, dict):
        return {key: scientific_payload(item) for key, item in value.items() if key not in excluded}
    if isinstance(value, list):
        return [scientific_payload(item) for item in value]
    return value


if __name__ == "__main__":
    main()
