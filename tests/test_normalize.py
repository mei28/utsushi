"""Tests for utsushi.normalize — theme/master enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation as build_presentation

from utsushi import normalize
from utsushi.adapters import pptx as pptx_adapter

_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _make_deck_with_theme_name(path: Path, name: str) -> None:
    """Build a one-slide deck and stamp <a:clrScheme name='...'> on it."""
    prs = build_presentation()
    prs.slides.add_slide(prs.slide_layouts[0])
    prs.save(str(path))
    deck = pptx_adapter.open_deck(path)
    theme = pptx_adapter.get_theme_xml(deck)
    clr = theme.find(f".//{_NS}clrScheme")
    assert clr is not None
    clr.set("name", name)
    pptx_adapter.set_theme_xml(deck, theme)
    pptx_adapter.save_deck(deck, path)


def test_apply_theme_copies_clrscheme_from_template(tmp_path: Path) -> None:
    target = tmp_path / "deck.pptx"
    template = tmp_path / "tpl.pptx"
    _make_deck_with_theme_name(target, "deck-original")
    _make_deck_with_theme_name(template, "corp-template")

    out = normalize.apply_theme(target, template)
    deck = pptx_adapter.open_deck(out)
    clr = pptx_adapter.get_theme_xml(deck).find(f".//{_NS}clrScheme")
    assert clr is not None
    assert clr.get("name") == "corp-template"


def test_apply_theme_default_output_is_normalized_suffix(tmp_path: Path) -> None:
    target = tmp_path / "deck.pptx"
    template = tmp_path / "tpl.pptx"
    _make_deck_with_theme_name(target, "deck-original")
    _make_deck_with_theme_name(template, "tpl")

    out = normalize.apply_theme(target, template)
    assert out == target.with_name("deck.normalized.pptx")
    # Source should be untouched.
    src_clr = pptx_adapter.get_theme_xml(pptx_adapter.open_deck(target)).find(f".//{_NS}clrScheme")
    assert src_clr is not None
    assert src_clr.get("name") == "deck-original"


def test_apply_theme_in_place_overwrites_source(tmp_path: Path) -> None:
    target = tmp_path / "deck.pptx"
    template = tmp_path / "tpl.pptx"
    _make_deck_with_theme_name(target, "deck-original")
    _make_deck_with_theme_name(template, "corp")

    out = normalize.apply_theme(target, template, in_place=True)
    assert out == target
    clr = pptx_adapter.get_theme_xml(pptx_adapter.open_deck(target)).find(f".//{_NS}clrScheme")
    assert clr is not None
    assert clr.get("name") == "corp"


def test_apply_theme_explicit_out(tmp_path: Path) -> None:
    target = tmp_path / "deck.pptx"
    template = tmp_path / "tpl.pptx"
    custom = tmp_path / "elsewhere" / "themed.pptx"
    _make_deck_with_theme_name(target, "deck-original")
    _make_deck_with_theme_name(template, "corp")

    out = normalize.apply_theme(target, template, out=custom)
    assert out == custom
    assert custom.exists()


def test_apply_theme_rejects_in_place_with_out(tmp_path: Path) -> None:
    target = tmp_path / "deck.pptx"
    template = tmp_path / "tpl.pptx"
    _make_deck_with_theme_name(target, "x")
    _make_deck_with_theme_name(template, "y")
    with pytest.raises(ValueError, match="--in-place"):
        normalize.apply_theme(target, template, out=tmp_path / "z.pptx", in_place=True)
