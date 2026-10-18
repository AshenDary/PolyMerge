"""Retrieve an approved private artifact without exposing its bearer URL."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Artifact redirects are not permitted")


def verified(path: Path, checksum: str, size: int) -> bool:
    if not path.is_file() or path.stat().st_size != size:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == checksum


def provision() -> None:
    url = os.getenv("POLYMERGE_MODEL_DOWNLOAD_URL")
    required = os.getenv("POLYMERGE_REQUIRE_MODEL") == "true"
    if not url and not required:
        return
    metadata = json.loads((ROOT / "data/interim/sprint5/final_model_evaluation.json").read_text())
    target = Path(os.environ["POLYMERGE_DDI_MODEL_PATH"])
    checksum, size = metadata["artifact_sha256"], metadata["artifact_size_bytes"]
    if verified(target, checksum, size):
        return
    if not url:
        raise ValueError("Verified artifact required")
    parsed = urlsplit(url)
    approved = os.environ["POLYMERGE_MODEL_DOWNLOAD_HOST"]
    if parsed.scheme != "https" or parsed.hostname != approved or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Artifact destination must match the approved HTTPS host")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            with build_opener(NoRedirect()).open(Request(url), timeout=60) as response:
                received = 0
                deadline = time.monotonic() + 300
                while chunk := response.read(1024 * 1024):
                    if time.monotonic() > deadline:
                        raise ValueError("Artifact retrieval timed out")
                    received += len(chunk)
                    if received > size:
                        raise ValueError("Artifact exceeds reviewed size")
                    output.write(chunk)
        if not verified(temporary, checksum, size):
            raise ValueError("Artifact checksum mismatch")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        provision()
    except Exception:
        # Never include the signed download URL or credential-bearing exceptions.
        raise SystemExit("Verified private model provisioning failed") from None
