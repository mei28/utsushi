"""Format detection for slide deck inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

Format = Literal["key", "pptx"]

_EXT_TO_FORMAT: dict[str, Format] = {".key": "key", ".pptx": "pptx"}


def detect_format(path: Path) -> Format:
    """Identify the deck format from a file extension (case-insensitive)."""
    ext = path.suffix.lower()
    fmt = _EXT_TO_FORMAT.get(ext)
    if fmt is None:
        raise ValueError(f"unsupported extension {ext!r} (path: {path})")
    return fmt
