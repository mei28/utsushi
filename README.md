# utsushi

Slide deck transcoder for Keynote / PowerPoint / Google Slides.

> *utsushi* (写し) — to transcribe, to copy by hand. A slide *utsuslide*.

macOS-only. Uses Keynote.app and Google Drive API as conversion engines; adds routing, theme normalization, and round-trip diffing on top.

> Not related to the EPSON `utsushi` scanner driver.

## Status

Design phase. See `docs/design.md`.

## Planned commands

```bash
utsushi convert deck.key --to pptx
utsushi convert deck.pptx --to slides --folder "Work/Decks"
utsushi convert https://docs.google.com/presentation/d/XXX --to keynote
utsushi normalize deck.pptx --theme corp-template.pptx
utsushi diff before.pptx after.pptx
utsushi sync ./decks --to drive --folder "Decks"
```
