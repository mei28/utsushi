"""Tests for utsushi.diff — round-trip XML comparison."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pptx import Presentation as build_presentation

from utsushi import diff
from utsushi.adapters import pptx as pptx_adapter

_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _make_tiny_deck(path: Path) -> None:
    prs = build_presentation()
    prs.slides.add_slide(prs.slide_layouts[0])
    prs.save(str(path))


def test_diff_decks_identical_files_returns_empty(tmp_path: Path) -> None:
    a = tmp_path / "a.pptx"
    b = tmp_path / "b.pptx"
    _make_tiny_deck(a)
    shutil.copyfile(a, b)
    report = diff.diff_decks(a, b)
    assert report.is_empty()


def test_diff_decks_detects_theme_change(tmp_path: Path) -> None:
    a = tmp_path / "a.pptx"
    b = tmp_path / "b.pptx"
    _make_tiny_deck(a)
    shutil.copyfile(a, b)

    deck = pptx_adapter.open_deck(b)
    theme = pptx_adapter.get_theme_xml(deck)
    clr = theme.find(f".//{_NS}clrScheme")
    assert clr is not None
    clr.set("name", "mutated")
    pptx_adapter.set_theme_xml(deck, theme)
    pptx_adapter.save_deck(deck, b)

    report = diff.diff_decks(a, b)
    assert not report.is_empty()
    assert any("theme1.xml" in p.partname for p in report.changed_parts)


def test_diff_decks_raises_on_missing_input(tmp_path: Path) -> None:
    real = tmp_path / "real.pptx"
    _make_tiny_deck(real)
    with pytest.raises(FileNotFoundError):
        diff.diff_decks(real, tmp_path / "missing.pptx")
