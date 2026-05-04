"""Integration tests against a real .pptx (typically generated from a real .key).

Requires UTSUSHI_TEST_PPTX env var pointing to an existing .pptx file.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from utsushi.adapters import pptx

_TEST_PPTX = os.environ.get("UTSUSHI_TEST_PPTX")

skip_no_pptx = pytest.mark.skipif(
    not _TEST_PPTX or not Path(_TEST_PPTX).exists(),
    reason="UTSUSHI_TEST_PPTX env var not set or file missing",
)


@skip_no_pptx
def test_open_and_get_theme_from_real_pptx() -> None:
    assert _TEST_PPTX is not None
    deck = pptx.open_deck(Path(_TEST_PPTX))
    theme = pptx.get_theme_xml(deck)
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    assert theme.tag == f"{ns}theme"


@skip_no_pptx
def test_set_theme_xml_round_trip_on_real_pptx(tmp_path: Path) -> None:
    assert _TEST_PPTX is not None
    deck = pptx.open_deck(Path(_TEST_PPTX))
    theme = pptx.get_theme_xml(deck)
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    clrscheme = theme.find(f".//{ns}clrScheme")
    assert clrscheme is not None
    clrscheme.set("name", "utsushi-real-test")

    pptx.set_theme_xml(deck, theme)
    out = tmp_path / "themed.pptx"
    pptx.save_deck(deck, out)

    reopened = pptx.open_deck(out)
    reopened_clr = pptx.get_theme_xml(reopened).find(f".//{ns}clrScheme")
    assert reopened_clr is not None
    assert reopened_clr.get("name") == "utsushi-real-test"
