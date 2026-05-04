"""Round-trip QA — compare two PPTX decks at the XML level."""

from __future__ import annotations

import difflib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

# Only XML-typed parts are compared; binary media (images, embedded fonts)
# generate noise that is rarely meaningful for fidelity verification.
_XML_SUFFIXES = (".xml", ".rels")


@dataclass
class PartDiff:
    partname: str
    unified: str


@dataclass
class DiffReport:
    changed_parts: list[PartDiff] = field(default_factory=list)
    only_in_left: list[str] = field(default_factory=list)
    only_in_right: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.changed_parts or self.only_in_left or self.only_in_right)


def _xml_parts(path: Path) -> dict[str, bytes]:
    """Return {partname: blob} for every XML/rels entry in the .pptx zip."""
    parts: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.filename.endswith(_XML_SUFFIXES):
                parts[info.filename] = zf.read(info.filename)
    return parts


def _canonicalize(blob: bytes) -> str:
    """Return a canonical XML form so attribute order does not show up as diff."""
    tree = etree.fromstring(blob)
    return etree.tostring(tree, method="c14n").decode("utf-8")


def _unified(left: str, right: str, partname: str) -> str:
    return "".join(
        difflib.unified_diff(
            left.splitlines(keepends=True),
            right.splitlines(keepends=True),
            fromfile=f"a/{partname}",
            tofile=f"b/{partname}",
        )
    )


def diff_decks(left: Path, right: Path) -> DiffReport:
    """Compare two .pptx decks at the XML-part level."""
    if not left.exists():
        raise FileNotFoundError(left)
    if not right.exists():
        raise FileNotFoundError(right)

    left_parts = _xml_parts(left)
    right_parts = _xml_parts(right)

    report = DiffReport()
    report.only_in_left = sorted(left_parts.keys() - right_parts.keys())
    report.only_in_right = sorted(right_parts.keys() - left_parts.keys())

    for name in sorted(left_parts.keys() & right_parts.keys()):
        a = _canonicalize(left_parts[name])
        b = _canonicalize(right_parts[name])
        if a != b:
            report.changed_parts.append(PartDiff(partname=name, unified=_unified(a, b, name)))
    return report
