"""Measure real candidate rule coverage without changing graph or model data."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "hypertension": ["10763"],
    "hypertension_diabetes": ["10763", "9352"],
    "coronary_atherosclerosis": ["3393", "1936"],
    "four_diseases": ["14221", "3393", "784", "10763"],
    "no_treatments": ["8398", "7148"],
}


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    candidates = result["candidateSets"]
    return {
        "candidates": len(candidates),
        "ruleStatuses": dict(Counter(c.get("ruleEvaluation", {}).get("status", "unreported") for c in candidates)),
        "ruleOutcomes": dict(Counter(r["status"] for c in candidates for r in c.get("ruleEvaluation", {}).get("rules", []))),
        "rejected": sum(c["status"] == "rejected" for c in candidates),
        "mlStatuses": dict(Counter(c["mlStatus"] for c in candidates)),
        "candidatesWithPredictions": sum(bool(c.get("mlPrediction", {}).get("pairs")) for c in candidates),
        "optimizerDrugs": result.get("metadata", {}).get("optimization", {}).get("selectedDrugs", []),
        "frequentDrugs": Counter(d for c in candidates for d in c["drugs"]).most_common(15),
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old = {c["candidateSetId"]: c for c in before["candidateSets"]}
    new = {c["candidateSetId"]: c for c in after["candidateSets"]}
    common = old.keys() & new.keys()
    return {
        "sharedCandidates": len(common),
        "changedSharedRanks": sum(old[key]["rank"] != new[key]["rank"] for key in common),
        "removedCandidates": [{"id": key, "drugs": old[key]["drugs"]} for key in sorted(old.keys() - new.keys())],
        "addedCandidates": [{"id": key, "drugs": new[key]["drugs"]} for key in sorted(new.keys() - old.keys())],
        "sharedEvidenceAndPredictionsUnchanged": all(
            all(old[key].get(field) == new[key].get(field) for field in
                ["graphEvidence", "treatedDiseaseIds", "uncoveredDiseaseIds", "mlStatus", "mlPrediction"])
            for key in common),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3002")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    mapping = json.loads((ROOT / "data/rules/research_rule_mapping.json").read_text())
    with (ROOT / "data/processed/fragment_nodes.csv").open() as stream:
        compounds = {r["id"]: r["name"] for r in csv.DictReader(stream) if r["kind"] == "Compound"}
    report: dict[str, Any] = {"mappingVersion": mapping["version"], "compounds": compounds,
        "mappedCompounds": len(set(compounds) & mapping["mappings"].keys()), "scenarios": {}}
    for name, ids in SCENARIOS.items():
        request = Request(args.url + "/api/candidate-sets/search",
            data=json.dumps({"diseaseIds": ["Disease::DOID:" + i for i in ids]}).encode(),
            headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=180) as response:
            result = json.load(response)
        (args.output / (name + ".json")).write_text(json.dumps(result))
        row = summarize(result)
        if args.baseline:
            before = json.loads((args.baseline / (name + ".json")).read_text())
            row.update(compare(before, result))
        report["scenarios"][name] = row
        json.dump({"scenario": name, **row}, sys.stdout)
        sys.stdout.write("\n")
    (args.output / "report.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
