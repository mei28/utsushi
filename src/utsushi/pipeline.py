"""Conversion pipeline — routes a source deck to a target format."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

from utsushi.adapters import drive, keynote
from utsushi.detect import Format, detect_format, is_drive_url

Target = Literal["key", "pptx", "slides"]

_EXT_FOR_TARGET: dict[str, str] = {"key": ".key", "pptx": ".pptx"}


def _convert_from_slides(url_or_id: str, target: Target, dst: Path | None) -> Path:
    """Slides → .pptx or .key. Returns the output local path."""
    if target == "slides":
        raise ValueError("source is already a Slides deck")
    if dst is None:
        raise ValueError("--out is required when source is a Drive URL")
    file_id = drive.parse_file_id(url_or_id)

    if target == "pptx":
        drive.export_as_pptx(file_id, dst)
        return dst

    # target == "key": export as .pptx into a temp, then convert with Keynote.
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp_pptx = Path(tmp.name)
    try:
        drive.export_as_pptx(file_id, tmp_pptx)
        keynote.import_from_pptx(tmp_pptx, dst)
    finally:
        tmp_pptx.unlink(missing_ok=True)
    return dst


def convert(
    src: str | Path,
    target: Target,
    dst: Path | None = None,
    folder_id: str | None = None,
) -> Path:
    """Convert a deck (local file or Drive URL) to the target format.

    For local-format targets ("key", "pptx") the return value is the output
    path. For "slides" the return value is the new Drive file id wrapped in
    Path() so the caller's contract (string-y identifier) stays uniform.
    """
    # Drive URL source: dispatch to the slides-export branch.
    if isinstance(src, str) and is_drive_url(src):
        return _convert_from_slides(src, target, dst)

    src_path = Path(src) if isinstance(src, str) else src
    if not src_path.exists():
        raise FileNotFoundError(src_path)

    source_fmt: Format = detect_format(src_path)

    if target == "slides":
        if source_fmt == "pptx":
            file_id = drive.upload_as_slides(src_path, folder_id=folder_id)
        else:  # source_fmt == "key"
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                tmp_pptx = Path(tmp.name)
            try:
                keynote.export_to_pptx(src_path, tmp_pptx)
                file_id = drive.upload_as_slides(tmp_pptx, folder_id=folder_id)
            finally:
                tmp_pptx.unlink(missing_ok=True)
        return Path(file_id)

    if source_fmt == target:
        raise ValueError(f"{src_path} is already in target format {target!r}")

    if dst is None:
        dst = src_path.with_suffix(_EXT_FOR_TARGET[target])

    if source_fmt == "key" and target == "pptx":
        keynote.export_to_pptx(src_path, dst)
    elif source_fmt == "pptx" and target == "key":
        keynote.import_from_pptx(src_path, dst)
    else:  # pragma: no cover — guarded by detect_format / target literal above.
        raise ValueError(f"no route from {source_fmt!r} to {target!r}")

    return dst
