from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from app import artifact_bootstrap as bootstrap


def setup_artifact(tmp_path: Path, monkeypatch, content: bytes = b"reviewed artifact") -> Path:
    metadata = tmp_path / "data/interim/sprint5/final_model_evaluation.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({"artifact_size_bytes": len(content), "artifact_sha256": hashlib.sha256(content).hexdigest()}))
    target = tmp_path / "model/frozen.joblib"
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setenv("POLYMERGE_DDI_MODEL_PATH", str(target))
    monkeypatch.setenv("POLYMERGE_REQUIRE_MODEL", "true")
    monkeypatch.setenv("POLYMERGE_MODEL_DOWNLOAD_URL", "https://approved.example/model?signature=secret")
    monkeypatch.setenv("POLYMERGE_MODEL_DOWNLOAD_HOST", "approved.example")
    return target


def test_download_verifies_and_reuses_cache_without_network(tmp_path, monkeypatch) -> None:
    content = b"reviewed artifact"
    target = setup_artifact(tmp_path, monkeypatch, content)
    class Opener:
        def open(self, request, timeout):
            return io.BytesIO(content)
    monkeypatch.setattr(bootstrap, "build_opener", lambda *_: Opener())
    bootstrap.provision()
    assert target.read_bytes() == content
    monkeypatch.setattr(bootstrap, "build_opener", lambda *_: pytest.fail("Cache must not download"))
    bootstrap.provision()


@pytest.mark.parametrize("content", [b"wrong", b"x" * 100])
def test_wrong_artifact_never_replaces_target(tmp_path, monkeypatch, content) -> None:
    target = setup_artifact(tmp_path, monkeypatch)
    class Opener:
        def open(self, request, timeout):
            return io.BytesIO(content)
    monkeypatch.setattr(bootstrap, "build_opener", lambda *_: Opener())
    with pytest.raises(ValueError):
        bootstrap.provision()
    assert not target.exists()
    assert not list(target.parent.iterdir())


def test_unapproved_host_or_missing_artifact_fails_closed(tmp_path, monkeypatch) -> None:
    setup_artifact(tmp_path, monkeypatch)
    monkeypatch.setenv("POLYMERGE_MODEL_DOWNLOAD_HOST", "different.example")
    with pytest.raises(ValueError):
        bootstrap.provision()
    monkeypatch.delenv("POLYMERGE_MODEL_DOWNLOAD_URL")
    with pytest.raises(ValueError):
        bootstrap.provision()


def test_redirect_is_not_followed() -> None:
    with pytest.raises(ValueError):
        bootstrap.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "http://private-host")
