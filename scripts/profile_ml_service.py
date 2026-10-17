"""Optional local-only instrumentation launcher; never trains or evaluates models.

Run with PROFILE_OUTPUT=/tmp/profile.jsonl python scripts/profile_ml_service.py.
Stage times are inclusive and must not be summed across nested stages.
"""
from __future__ import annotations

import contextvars
import functools
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_engine"))
import main as api
from app.services import candidate_generator as generation
from app.services import graph_service as graph
from app.services import ddi_feature_builder as features
from app.services.model_serving import DDIModelService
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
import uvicorn

CURRENT = contextvars.ContextVar("profile", default=None)


def instrument(owner: object, name: str, stage: str) -> None:
    original = getattr(owner, name)

    @functools.wraps(original)
    def measured(*args, **kwargs):
        record = CURRENT.get()
        start = time.perf_counter()
        try:
            result = original(*args, **kwargs)
            if record is not None and stage == "graph_total":
                record["compound_count"] = len(result["candidates"])
            return result
        finally:
            if record is not None:
                slot = record["stages"].setdefault(stage, {"ms": 0, "calls": 0})
                slot["ms"] += (time.perf_counter() - start) * 1000
                slot["calls"] += 1

    setattr(owner, name, measured)


for owner, name, stage in [
    (graph.GraphService, "resolve_diseases", "disease_validation"),
    (graph.GraphService, "get_disease_drug_relationships", "neo4j_treatments"),
    (graph.GraphService, "get_drug_targets", "neo4j_genes"),
    (graph.GraphService, "get_drug_side_effects", "neo4j_side_effects"),
    (graph.GraphService, "build_candidate_drugs", "graph_total"),
    (graph, "_graph_evidence", "graph_paths"),
    (generation, "generate_candidate_sets", "candidate_generation"),
    (generation, "_candidate_set_from_combo", "candidate_materialization"),
    (generation, "check_hard_contraindications", "rules"),
    (generation, "_aggregate_graph_paths", "candidate_paths"),
    (api, "rank_candidates", "ranking"),
    (api, "optimize_candidate_sets", "optimization"),
    (features.PairFeatureBuilder, "__post_init__", "feature_initialization"),
    (features.PairFeatureBuilder, "_load_hetionet_mapping", "id_mapping_load"),
    (features.PairFeatureBuilder, "_load_pubchem_mapping", "structure_lookup_load"),
    (features, "build_graph_feature_lookup", "graph_feature_lookup_build"),
    (features.PairFeatureBuilder, "build_features", "feature_construction"),
    (features, "_pair_graph_features", "graph_pair_features"),
    (features, "_pair_molecular_features", "molecular_pair_features"),
    (DDIModelService, "predict", "validated_inference"),
    (Pipeline, "predict", "pipeline_predict"),
    (ColumnTransformer, "transform", "preprocessing"),
    (RandomForestClassifier, "predict", "random_forest"),
    (api, "_candidate_set_response", "response_and_predictions"),
]:
    instrument(owner, name, stage)


@api.app.middleware("http")
async def profile_request(request, call_next):
    record = {"request_id": uuid.uuid4().hex, "path": request.url.path, "stages": {}}
    token = CURRENT.set(record)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        record["status"] = response.status_code
        response.headers["X-Profile-Request-Id"] = record["request_id"]
        return response
    finally:
        record["total_ms"] = (time.perf_counter() - start) * 1000
        CURRENT.reset(token)
        with Path(os.environ["PROFILE_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    uvicorn.run(api.app, host="127.0.0.1", port=int(os.getenv("PROFILE_PORT", "8014")))
