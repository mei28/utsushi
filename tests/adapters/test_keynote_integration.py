"""Integration tests that drive Keynote.app for real.

Skipped unless UTSUSHI_TEST_KEY is set to the path of an existing .key file.
This avoids committing binary fixtures and lets CI skip cleanly.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from utsushi.adapters import keynote

_TEST_KEY = os.environ.get("UTSUSHI_TEST_KEY")

skip_no_key = pytest.mark.skipif(
    not _TEST_KEY or not Path(_TEST_KEY).exists(),
    reason="UTSUSHI_TEST_KEY env var not set or file missing",
)


@skip_no_key
def test_export_real_key_to_pptx(tmp_path: Path) -> None:
    assert _TEST_KEY is not None
    src = Path(_TEST_KEY)
    dst = tmp_path / "out.pptx"
    keynote.export_to_pptx(src, dst)
    assert dst.exists()
    assert dst.stat().st_size > 0
    # PPTX is a zip; check the magic bytes.
    assert dst.read_bytes()[:2] == b"PK"


@skip_no_key
def test_round_trip_key_to_pptx_to_key(tmp_path: Path) -> None:
    assert _TEST_KEY is not None
    src = Path(_TEST_KEY)
    intermediate = tmp_path / "round.pptx"
    final = tmp_path / "round.key"
    keynote.export_to_pptx(src, intermediate)
    keynote.import_from_pptx(intermediate, final)
    assert final.exists()
