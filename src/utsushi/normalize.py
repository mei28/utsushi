"""Theme/master enforcement — overwrite a deck's theme with a template's."""

from __future__ import annotations

import shutil
from pathlib import Path

from utsushi.adapters import pptx as pptx_adapter


def _resolve_output(target: Path, out: Path | None, in_place: bool) -> Path:
    if in_place and out is not None:
        raise ValueError("--in-place and --out are mutually exclusive")
    if in_place:
        return target
    if out is not None:
        return out
    return target.with_name(f"{target.stem}.normalized{target.suffix}")


def apply_theme(
    target: Path,
    template: Path,
    out: Path | None = None,
    in_place: bool = False,
) -> Path:
    """Copy the template deck's theme1.xml into target.

    Slide masters reference the theme but their own XML (layout list,
    placeholder geometry) is left untouched, so the target's slide
    structure is preserved while colors/fonts/format scheme follow the
    template.
    """
    if not target.exists():
        raise FileNotFoundError(target)
    if not template.exists():
        raise FileNotFoundError(template)

    dst = _resolve_output(target, out, in_place)

    if not in_place:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, dst)

    template_theme = pptx_adapter.get_theme_xml(pptx_adapter.open_deck(template))
    deck = pptx_adapter.open_deck(dst)
    pptx_adapter.set_theme_xml(deck, template_theme)
    pptx_adapter.save_deck(deck, dst)
    return dst
