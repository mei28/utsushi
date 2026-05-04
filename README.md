# utsushi

Slide deck transcoder for Keynote / PowerPoint / Google Slides.

> *utsushi* (写し) — to transcribe, to copy by hand. A slide *utsuslide*.

macOS-only. Uses Keynote.app and Google Drive API as conversion engines; adds routing, theme normalization, and round-trip diffing on top.

> Not related to the EPSON `utsushi` scanner driver.

## Status

PPTX <-> Keynote conversion, theme normalization, and XML diff are implemented. Google Slides (Drive API) is deferred. See `docs/design.md` for the design and `.tmp/plan.md` for the current implementation plan.

## Development

Requires `uv` and `just`.

```bash
just install     # uv sync — create .venv and install deps
just test        # pytest
just lint        # ruff check
just typecheck   # mypy --strict
just check       # lint + typecheck + test
just run --help  # invoke the CLI
```

## Commands

Implemented:

```bash
utsushi convert deck.key --to pptx              # .key <-> .pptx
utsushi convert deck.pptx --to key
utsushi normalize deck.pptx --theme tpl.pptx    # copy template's theme1.xml
utsushi diff before.pptx after.pptx             # XML-part level round-trip QA
utsushi version
```

Deferred (Drive API not yet wired):

```bash
utsushi convert deck.pptx --to slides --folder "Work/Decks"
utsushi convert https://docs.google.com/presentation/d/XXX --to keynote
utsushi sync ./decks --to drive --folder "Decks"
```
