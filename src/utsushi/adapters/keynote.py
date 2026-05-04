"""Keynote.app adapter via osascript."""

from __future__ import annotations

import fcntl
import os
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

# AppleScript string literals do not allow these characters; escaping them
# would invite quoting bugs. Reject up front (fail fast) instead.
_FORBIDDEN_PATH_CHARS = ('"', "\\", "\n", "\r")

_LOCK_PATH = Path.home() / ".cache" / "utsushi" / "keynote.lock"


class KeynoteError(RuntimeError):
    """Raised when osascript exits non-zero."""


@contextmanager
def _acquire_lock() -> Generator[None]:
    """Serialize Keynote.app access across processes via flock.

    Concurrent osascript invocations against Keynote can corrupt document state,
    so callers of run_script() take an exclusive file lock for the duration of
    the invocation.
    """
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(_LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _run_osascript(script: str) -> subprocess.CompletedProcess[str]:
    """Invoke osascript with the given script body. Indirected for test patching."""
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )


def run_script(script: str) -> None:
    """Run an AppleScript via osascript under the Keynote concurrency lock."""
    with _acquire_lock():
        result = _run_osascript(script)
    if result.returncode != 0:
        raise KeynoteError(result.stderr.strip() or f"osascript exit {result.returncode}")


def export_to_pptx(src: Path, dst: Path) -> None:
    """Convert a .key file to .pptx via Keynote.app."""
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    run_script(build_export_script(src, dst))
    if not dst.exists():
        raise KeynoteError(f"output not produced: {dst}")


def import_from_pptx(src: Path, dst: Path) -> None:
    """Convert a .pptx file to .key via Keynote.app."""
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    run_script(build_import_script(src, dst))
    if not dst.exists():
        raise KeynoteError(f"output not produced: {dst}")


def _validate_path(path: Path) -> str:
    text = str(path)
    for ch in _FORBIDDEN_PATH_CHARS:
        if ch in text:
            raise ValueError(f"unsafe character {ch!r} in path: {text!r}")
    return text


def build_export_script(src: Path, dst: Path) -> str:
    """Build an AppleScript that exports a .key file to .pptx via Keynote.app."""
    src_s = _validate_path(src)
    dst_s = _validate_path(dst)
    return (
        f'tell application "Keynote"\n'
        f'  set theDoc to open POSIX file "{src_s}"\n'
        f'  export theDoc to POSIX file "{dst_s}" as Microsoft PowerPoint\n'
        f"  close theDoc saving no\n"
        f"end tell\n"
    )


def build_import_script(src: Path, dst: Path) -> str:
    """Build an AppleScript that imports a .pptx into Keynote and saves as .key."""
    src_s = _validate_path(src)
    dst_s = _validate_path(dst)
    return (
        f'tell application "Keynote"\n'
        f'  set theDoc to open POSIX file "{src_s}"\n'
        f'  save theDoc in POSIX file "{dst_s}"\n'
        f"  close theDoc saving no\n"
        f"end tell\n"
    )
