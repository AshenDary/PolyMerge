"""Conservative PubChem identity resolution and deterministic RDKit descriptors."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

from app.data.ddinter_dataset import INTERIM_DIR, normalize_drug_name


PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_DOCS_URL = "https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest"
CACHE_PATH = INTERIM_DIR / "pubchem_query_cache.jsonl"
MAPPING_PATH = INTERIM_DIR / "ddinter_pubchem_mapping.csv"
REQUEST_INTERVAL_SECONDS = 0.22
PROPERTY_LIST = "Title,ConnectivitySMILES,SMILES,InChI,InChIKey"
MAPPING_COLUMNS = [
    "ddinter_id", "ddinter_name", "pubchem_cid", "pubchem_title",
    "connectivity_smiles", "smiles", "inchi", "inchikey", "mapping_method",
    "mapping_status", "structure_status", "retrieval_source", "retrieved_at",
]
DESCRIPTOR_NAMES = ["molecular_weight", "logp", "tpsa", "hbd", "hba", "rotatable_bonds"]


def pubchem_property_url(name: str) -> str:
    encoded = quote(name, safe="")
    return f"{PUBCHEM_BASE_URL}/compound/name/{encoded}/property/{PROPERTY_LIST}/JSON"


def fetch_pubchem_name(name: str, timeout: int = 45, retries: int = 4) -> dict[str, object]:
    """Query one exact name while respecting PubChem's shared-service limits."""
    request = Request(
        pubchem_property_url(name),
        headers={"User-Agent": "PolyMerge/0.1 academic research"},
    )
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                return {
                    "http_status": response.status,
                    "properties": json.load(response)["PropertyTable"]["Properties"],
                }
        except HTTPError as error:
            if error.code == 404:
                return {"http_status": 404, "properties": []}
            if error.code not in {429, 500, 502, 503, 504} or attempt == retries - 1:
                return {"http_status": error.code, "properties": [], "error": str(error)}
        except (TimeoutError, URLError) as error:
            if attempt == retries - 1:
                return {"http_status": 0, "properties": [], "error": str(error)}
        time.sleep(2 ** attempt)
    return {"http_status": 0, "properties": [], "error": "retry limit reached"}


def classify_pubchem_result(
    ddinter_id: str,
    ddinter_name: str,
    result: dict[str, object],
    retrieved_at: str,
) -> dict[str, object]:
    """Accept only a unique exact-title structure; never pick a plausible first hit."""
    properties = result.get("properties", [])
    row: dict[str, object] = {
        "ddinter_id": ddinter_id,
        "ddinter_name": ddinter_name,
        "pubchem_cid": pd.NA,
        "pubchem_title": pd.NA,
        "connectivity_smiles": pd.NA,
        "smiles": pd.NA,
        "inchi": pd.NA,
        "inchikey": pd.NA,
        "mapping_method": "exact DDInter name query",
        "mapping_status": "unmapped",
        "structure_status": "unavailable",
        "retrieval_source": pubchem_property_url(ddinter_name),
        "retrieved_at": retrieved_at,
    }
    if len(properties) > 1:
        row["mapping_status"] = "ambiguous"
        row["structure_status"] = "excluded_multiple_candidates"
        return row
    if not properties:
        if result.get("http_status") not in {404, None}:
            row["mapping_status"] = "rejected"
            row["structure_status"] = "query_error"
        return row

    candidate = properties[0]
    row.update({
        "pubchem_cid": candidate.get("CID", pd.NA),
        "pubchem_title": candidate.get("Title", pd.NA),
        "connectivity_smiles": candidate.get("ConnectivitySMILES", pd.NA),
        "smiles": candidate.get("SMILES", pd.NA),
        "inchi": candidate.get("InChI", pd.NA),
        "inchikey": candidate.get("InChIKey", pd.NA),
    })
    if normalize_drug_name(str(candidate.get("Title", ""))) != normalize_drug_name(ddinter_name):
        row["mapping_status"] = "ambiguous"
        row["structure_status"] = "excluded_title_mismatch"
        return row
    if not all(candidate.get(field) for field in ("CID", "SMILES", "InChI", "InChIKey")):
        row["mapping_status"] = "rejected"
        row["structure_status"] = "missing_structure_identifier"
        return row
    molecule = Chem.MolFromSmiles(str(candidate["SMILES"]))
    if molecule is None:
        row["mapping_status"] = "rejected"
        row["structure_status"] = "rdkit_parse_failed"
        return row
    row["mapping_status"] = "exact_unique"
    row["structure_status"] = "valid"
    return row


def load_query_cache(path: Path = CACHE_PATH) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    records: dict[str, dict[str, object]] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                record = json.loads(line)
                records[record["ddinter_id"]] = record
    return records


def enrich_pubchem_mapping(
    drugs: pd.DataFrame,
    retrieved_at: str,
    cache_path: Path = CACHE_PATH,
    mapping_path: Path = MAPPING_PATH,
    fetcher: Callable[[str], dict[str, object]] = fetch_pubchem_name,
    request_interval: float = REQUEST_INTERVAL_SECONDS,
    workers: int = 1,
) -> pd.DataFrame:
    """Resolve all drugs, appending each query result to a restartable cache."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached = load_query_cache(cache_path)
    transient_statuses = {0, 429, 500, 502, 503, 504}
    retry_ids = {
        ddinter_id for ddinter_id, record in cached.items()
        if record["result"].get("http_status") in transient_statuses
    }
    pending = drugs.loc[
        ~drugs["ddinter_id"].isin(cached) | drugs["ddinter_id"].isin(retry_ids)
    ].sort_values("ddinter_id")
    rate_lock = Lock()
    last_request_started = [0.0]

    def rate_limited_fetch(name: str) -> dict[str, object]:
        with rate_lock:
            wait = request_interval - (time.monotonic() - last_request_started[0])
            if wait > 0:
                time.sleep(wait)
            last_request_started[0] = time.monotonic()
        return fetcher(name)

    rows_by_future = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for row in pending.itertuples(index=False):
            rows_by_future[executor.submit(rate_limited_fetch, row.ddinter_name)] = row
        for number, future in enumerate(as_completed(rows_by_future), start=1):
            row = rows_by_future[future]
            record = {
                "ddinter_id": row.ddinter_id,
                "ddinter_name": row.ddinter_name,
                "retrieved_at": retrieved_at,
                "result": future.result(),
            }
            with cache_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            cached[row.ddinter_id] = record
            if number % 100 == 0 or number == len(pending):
                print(f"Cached {number}/{len(pending)} pending PubChem queries", flush=True)

    with cache_path.open("w", encoding="utf-8") as stream:
        for ddinter_id in sorted(cached):
            stream.write(json.dumps(cached[ddinter_id], sort_keys=True) + "\n")

    rows = [
        classify_pubchem_result(
            record["ddinter_id"], record["ddinter_name"], record["result"],
            record["retrieved_at"],
        )
        for record in cached.values()
        if record["ddinter_id"] in set(drugs["ddinter_id"])
    ]
    mapping = pd.DataFrame(rows, columns=MAPPING_COLUMNS).sort_values("ddinter_id").reset_index(drop=True)
    mapping.to_csv(mapping_path, index=False)
    return mapping


def validate_pubchem_mapping(frame: pd.DataFrame) -> None:
    missing = set(MAPPING_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"PubChem mapping is missing columns: {', '.join(sorted(missing))}")
    accepted = frame.loc[frame["mapping_status"] == "exact_unique"]
    invalid = accepted.loc[accepted["smiles"].map(lambda value: Chem.MolFromSmiles(str(value)) is None)]
    if not invalid.empty:
        raise ValueError(f"Accepted PubChem mappings contain {len(invalid)} invalid structures")


def rdkit_descriptors(smiles: object) -> dict[str, float | int | object]:
    if pd.isna(smiles):
        return {name: pd.NA for name in DESCRIPTOR_NAMES}
    return _rdkit_descriptors_for_smiles(str(smiles))


@lru_cache(maxsize=None)
def _rdkit_descriptors_for_smiles(smiles: str) -> dict[str, float | int | object]:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return {name: pd.NA for name in DESCRIPTOR_NAMES}
    return {
        "molecular_weight": Descriptors.MolWt(molecule),
        "logp": Crippen.MolLogP(molecule),
        "tpsa": rdMolDescriptors.CalcTPSA(molecule),
        "hbd": Lipinski.NumHDonors(molecule),
        "hba": Lipinski.NumHAcceptors(molecule),
        "rotatable_bonds": Lipinski.NumRotatableBonds(molecule),
    }
