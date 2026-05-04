"""Tests for utsushi.detect — format identification."""

from __future__ import annotations

from pathlib import Path

import pytest

from utsushi import detect


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("deck.key", "key"),
        ("deck.pptx", "pptx"),
        ("/tmp/MY DECK.KEY", "key"),
        ("/tmp/My-Deck.PPTX", "pptx"),
    ],
)
def test_detect_format_from_extension(path: str, expected: str) -> None:
    assert detect.detect_format(Path(path)) == expected


def test_detect_format_rejects_unknown_extension() -> None:
    with pytest.raises(ValueError, match="unsupported extension"):
        detect.detect_format(Path("deck.odp"))
