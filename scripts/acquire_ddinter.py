"""Download and verify the official DDInter 2.0 category CSV files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
DESTINATION = REPO_ROOT / "data" / "original" / "ddinter"
MANIFEST_PATH = DESTINATION / "source_manifest.json"
BASE_URL = "https://ddinter2.scbdd.com/static/media/download"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename, expected_hash in manifest["files"].items():
        destination = DESTINATION / filename
        if not destination.exists() or sha256(destination) != expected_hash:
            with urlopen(f"{BASE_URL}/{filename}", timeout=120) as response:
                destination.write_bytes(response.read())
        actual_hash = sha256(destination)
        if actual_hash != expected_hash:
            raise ValueError(f"Checksum mismatch for {filename}: {actual_hash}")
        print(f"Verified {filename}: {actual_hash}")


if __name__ == "__main__":
    main()
