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


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.google.com/presentation/d/1abcXYZ/edit",
        "https://docs.google.com/presentation/d/1abcXYZ",
    ],
)
def test_is_drive_url_recognizes_drive_presentation(url: str) -> None:
    assert detect.is_drive_url(url)


def test_is_drive_url_rejects_non_drive() -> None:
    assert not detect.is_drive_url("https://example.com/foo")
    assert not detect.is_drive_url("/local/path/deck.pptx")
