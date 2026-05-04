"""Format detection for slide deck inputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

Format = Literal["key", "pptx"]

_EXT_TO_FORMAT: dict[str, Format] = {".key": "key", ".pptx": "pptx"}

_DRIVE_URL = re.compile(r"^https?://docs\.google\.com/presentation/d/[A-Za-z0-9_-]+")


def detect_format(path: Path) -> Format:
    """Identify the deck format from a file extension (case-insensitive)."""
    ext = path.suffix.lower()
    fmt = _EXT_TO_FORMAT.get(ext)
    if fmt is None:
        raise ValueError(f"unsupported extension {ext!r} (path: {path})")
    return fmt


def is_drive_url(s: str) -> bool:
    """True when the string looks like a Google Slides URL."""
    return bool(_DRIVE_URL.match(s))
