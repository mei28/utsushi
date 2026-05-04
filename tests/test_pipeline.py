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


def test_convert_to_slides_is_not_implemented(tmp_path: Path) -> None:
    src = tmp_path / "deck.pptx"
    src.write_bytes(b"PK\x03\x04")
    with pytest.raises(NotImplementedError, match="slides"):
        pipeline.convert(src, target="slides")
