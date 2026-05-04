"""Conversion pipeline — routes a source deck to a target format."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from utsushi.adapters import keynote
from utsushi.detect import Format, detect_format

# Targets accepted by the CLI today. "slides" is reserved for the future
# Drive adapter and explicitly fails fast until drive.py lands.
Target = Literal["key", "pptx", "slides"]

_EXT_FOR_TARGET: dict[str, str] = {"key": ".key", "pptx": ".pptx"}


def convert(src: Path, target: Target, dst: Path | None = None) -> Path:
    """Convert a deck file to the target format and return the output path."""
    if target == "slides":
        raise NotImplementedError("conversion to slides is not implemented yet")
    if not src.exists():
        raise FileNotFoundError(src)

    source_fmt: Format = detect_format(src)
    if source_fmt == target:
        raise ValueError(f"{src} is already in target format {target!r}")

    if dst is None:
        dst = src.with_suffix(_EXT_FOR_TARGET[target])

    if source_fmt == "key" and target == "pptx":
        keynote.export_to_pptx(src, dst)
    elif source_fmt == "pptx" and target == "key":
        keynote.import_from_pptx(src, dst)
    else:  # pragma: no cover — guarded by detect_format / target literal above.
        raise ValueError(f"no route from {source_fmt!r} to {target!r}")

    return dst
