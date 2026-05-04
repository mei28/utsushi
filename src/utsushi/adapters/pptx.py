"""PPTX adapter — wraps python-pptx for theme/master operations."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx import Presentation as _open_presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as _RT
from pptx.opc.package import Part
from pptx.presentation import Presentation


def open_deck(path: Path) -> Presentation:
    """Open a .pptx file as a python-pptx Presentation."""
    if not path.exists():
        raise FileNotFoundError(path)
    return _open_presentation(str(path))


def _theme_part(deck: Presentation) -> Part:
    """Return the theme part of the first slide master."""
    if len(deck.slide_masters) == 0:
        raise ValueError("deck has no slide masters")
    sm_part = deck.slide_masters[0].part
    return sm_part.part_related_by(_RT.THEME)


def get_theme_xml(deck: Presentation) -> etree._Element:
    """Return the parsed theme1.xml element of the deck's first slide master."""
    return etree.fromstring(_theme_part(deck).blob)


def set_theme_xml(deck: Presentation, theme: etree._Element) -> None:
    """Replace the theme1.xml blob of the deck's first slide master."""
    _theme_part(deck).blob = etree.tostring(
        theme, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def save_deck(deck: Presentation, path: Path) -> None:
    """Write the deck to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    deck.save(str(path))
