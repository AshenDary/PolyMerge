"""Opt-in sequential benchmark of real canonical requests, never evaluation data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 4))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for scenario, ids in [("catalog", []), ("one", ["Disease::DOID:10763"]),
                          ("two", ["Disease::DOID:10763", "Disease::DOID:9352"])]:
        for repeat in range(args.repeats):
            path = "/api/candidate-sets/search" if ids else "/api/diseases"
            request = Request(args.url.rstrip("/") + path,
                              data=json.dumps({"diseaseIds": ids}).encode() if ids else None,
                              headers={"Content-Type": "application/json"})
            start = time.perf_counter()
            with urlopen(request, timeout=180) as response:
                raw = response.read()
            elapsed = (time.perf_counter() - start) * 1000
            result = json.loads(raw)
            (args.output / f"{scenario}-{repeat}.json").write_bytes(raw)
            pairs = [p for c in result.get("candidateSets", []) for p in c.get("mlPrediction", {}).get("pairs", [])]
            metric = {"scenario": scenario, "repeat": repeat, "ms": elapsed,
                      "query_id": result.get("queryId"), "bytes": len(raw),
                      "returned": len(result.get("candidateSets", [])), "applied_pairs": len(pairs)}
            with (args.output / "measurements.jsonl").open("a") as output:
                output.write(json.dumps(metric) + "\n")
            print(json.dumps(metric), flush=True)


if __name__ == "__main__":
    main()
