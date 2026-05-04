"""Tests for the conversion pipeline routing."""

from __future__ import annotations

from pathlib import Path

import pytest

from utsushi import pipeline
from utsushi.adapters import keynote


def test_convert_routes_key_to_pptx_via_keynote_export(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "deck.key"
    src.write_text("fake")
    captured: dict[str, Path] = {}

    def fake_export(s: Path, d: Path) -> None:
        captured["src"] = s
        captured["dst"] = d
        d.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(keynote, "export_to_pptx", fake_export)
    out = pipeline.convert(src, target="pptx")

    assert captured["src"] == src
    assert out == src.with_suffix(".pptx")
    assert out.exists()


def test_convert_routes_pptx_to_key_via_keynote_import(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"PK\x03\x04")

    def fake_import(s: Path, d: Path) -> None:
        d.write_bytes(b"fake-key")

    monkeypatch.setattr(keynote, "import_from_pptx", fake_import)
    out = pipeline.convert(src, target="key")

    assert out == src.with_suffix(".key")
    assert out.exists()


def test_convert_honors_explicit_dst(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    src = tmp_path / "deck.key"
    src.write_text("fake")
    dst = tmp_path / "elsewhere" / "renamed.pptx"

    def fake_export(s: Path, d: Path) -> None:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(keynote, "export_to_pptx", fake_export)
    out = pipeline.convert(src, target="pptx", dst=dst)
    assert out == dst
    assert out.exists()


def test_convert_noop_when_target_matches_source(
    tmp_path: Path,
) -> None:
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"PK\x03\x04")
    with pytest.raises(ValueError, match="already in target format"):
        pipeline.convert(src, target="pptx")


def test_convert_pptx_to_slides_uploads_via_drive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from utsushi.adapters import drive

    src = tmp_path / "deck.pptx"
    src.write_bytes(b"PK\x03\x04")
    captured: dict[str, object] = {}

    def fake_upload(p: Path, folder_id: str | None = None) -> str:
        captured["path"] = p
        captured["folder_id"] = folder_id
        return "FILE_ID"

    monkeypatch.setattr(drive, "upload_as_slides", fake_upload)
    out = pipeline.convert(src, target="slides", folder_id="F1")
    assert out == Path("FILE_ID")  # pipeline returns a Path-shaped identifier
    assert captured["folder_id"] == "F1"


def test_convert_key_to_slides_routes_through_pptx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from utsushi.adapters import drive, keynote

    src = tmp_path / "deck.key"
    src.write_text("fake")

    def fake_export(s: Path, d: Path) -> None:
        d.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(keynote, "export_to_pptx", fake_export)
    monkeypatch.setattr(drive, "upload_as_slides", lambda p, folder_id=None: "FILE_ID")
    out = pipeline.convert(src, target="slides")
    assert out == Path("FILE_ID")


def test_convert_from_slides_url_to_pptx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from utsushi.adapters import drive

    url = "https://docs.google.com/presentation/d/ABC123/edit"
    captured: dict[str, object] = {}

    def fake_export(file_id: str, dst: Path) -> None:
        captured["file_id"] = file_id
        dst.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(drive, "export_as_pptx", fake_export)
    out = pipeline.convert(url, target="pptx", dst=tmp_path / "out.pptx")
    assert captured["file_id"] == "ABC123"
    assert out == tmp_path / "out.pptx"
    assert out.exists()


def test_convert_from_slides_url_to_key_routes_through_pptx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from utsushi.adapters import drive, keynote

    url = "https://docs.google.com/presentation/d/ABC123"
    monkeypatch.setattr(
        drive, "export_as_pptx", lambda fid, dst: dst.write_bytes(b"PK\x03\x04")
    )

    def fake_import(s: Path, d: Path) -> None:
        d.write_bytes(b"fake-key")

    monkeypatch.setattr(keynote, "import_from_pptx", fake_import)
    out = pipeline.convert(url, target="key", dst=tmp_path / "out.key")
    assert out == tmp_path / "out.key"
    assert out.exists()
