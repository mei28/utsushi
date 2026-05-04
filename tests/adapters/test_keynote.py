"""Unit tests for the Keynote adapter (osascript script generation)."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

from utsushi.adapters import keynote


def test_build_export_script_includes_paths() -> None:
    src = Path("/tmp/in.key")
    dst = Path("/tmp/out.pptx")
    script = keynote.build_export_script(src, dst)
    assert str(src) in script
    assert str(dst) in script
    assert "Microsoft PowerPoint" in script


def test_build_import_script_includes_paths() -> None:
    src = Path("/tmp/in.pptx")
    dst = Path("/tmp/out.key")
    script = keynote.build_import_script(src, dst)
    assert str(src) in script
    assert str(dst) in script
    # Keynote opens .pptx and saves as native .key — no explicit format token needed.
    assert "save" in script


@pytest.mark.parametrize("bad", ['/tmp/foo"bar.key', "/tmp/foo\\bar.key", "/tmp/foo\nbar.key"])
def test_build_export_script_rejects_unsafe_path(bad: str) -> None:
    # Fail fast on paths that would break the AppleScript string literal.
    with pytest.raises(ValueError, match="unsafe character"):
        keynote.build_export_script(Path(bad), Path("/tmp/out.pptx"))


@pytest.mark.parametrize("bad", ['/tmp/foo"bar.pptx', "/tmp/foo\\bar.pptx"])
def test_build_import_script_rejects_unsafe_path(bad: str) -> None:
    with pytest.raises(ValueError, match="unsafe character"):
        keynote.build_import_script(Path(bad), Path("/tmp/out.key"))


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = stderr


def test_run_script_invokes_osascript_with_script_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def fake(script: str) -> _FakeCompleted:
        captured["script"] = script
        return _FakeCompleted()

    monkeypatch.setattr(keynote, "_run_osascript", fake)
    monkeypatch.setattr(keynote, "_acquire_lock", nullcontext)

    keynote.run_script('tell application "Keynote" to activate')
    assert "Keynote" in captured["script"]


def test_run_script_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        keynote, "_run_osascript", lambda script: _FakeCompleted(returncode=1, stderr="boom")
    )
    monkeypatch.setattr(keynote, "_acquire_lock", nullcontext)

    with pytest.raises(keynote.KeynoteError, match="boom"):
        keynote.run_script("noop")


def test_export_to_pptx_creates_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    src = tmp_path / "in.key"
    dst = tmp_path / "out.pptx"
    src.write_text("fake key body")

    def fake_run_script(script: str) -> None:
        # Simulate Keynote producing the output file.
        dst.write_bytes(b"PK\x03\x04fake-pptx")

    monkeypatch.setattr(keynote, "run_script", fake_run_script)
    keynote.export_to_pptx(src, dst)
    assert dst.exists()


def test_export_to_pptx_fails_if_output_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "in.key"
    dst = tmp_path / "out.pptx"
    src.write_text("fake")
    monkeypatch.setattr(keynote, "run_script", lambda script: None)
    with pytest.raises(keynote.KeynoteError, match="output not produced"):
        keynote.export_to_pptx(src, dst)


def test_export_to_pptx_fails_if_source_missing(tmp_path: Path) -> None:
    src = tmp_path / "missing.key"
    dst = tmp_path / "out.pptx"
    with pytest.raises(FileNotFoundError):
        keynote.export_to_pptx(src, dst)


def test_import_from_pptx_creates_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    src = tmp_path / "in.pptx"
    dst = tmp_path / "out.key"
    src.write_bytes(b"PK\x03\x04fake")

    def fake_run_script(script: str) -> None:
        dst.write_bytes(b"fake-key")

    monkeypatch.setattr(keynote, "run_script", fake_run_script)
    keynote.import_from_pptx(src, dst)
    assert dst.exists()
