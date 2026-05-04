# utsushi

Slide deck transcoder for Keynote / PowerPoint / Google Slides.

> *utsushi* (写し) — to transcribe, to copy by hand. A slide *utsuslide*.

macOS-only. Uses Keynote.app and Google Drive API as conversion engines; adds routing, theme normalization, and round-trip diffing on top.

> Not related to the EPSON `utsushi` scanner driver.

## Status

PPTX <-> Keynote, Slides <-> PPTX/Keynote, theme normalization, and XML diff are implemented. See `docs/design.md` for the design.

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

```bash
utsushi convert deck.key --to pptx                                # .key -> .pptx
utsushi convert deck.pptx --to key                                # .pptx -> .key
utsushi convert deck.pptx --to slides                             # upload to Drive
utsushi convert deck.pptx --to slides --folder FOLDER_ID          # to a specific folder
utsushi convert https://docs.google.com/presentation/d/XXX --to pptx --out deck.pptx
utsushi normalize deck.pptx --theme tpl.pptx                      # copy template's theme1.xml
utsushi diff before.pptx after.pptx                               # XML-part level QA
utsushi version
```

## Google Slides setup

Drive integration uses your own Google Cloud OAuth client. Five-minute setup:

1. Open the Google Cloud Console and create a new project (or pick an existing one).
2. Enable the Google Drive API for that project (`APIs & Services > Library`).
3. Configure the OAuth consent screen as `External` with your own Google account as a test user.
4. Under `APIs & Services > Credentials`, create an `OAuth client ID` of type `Desktop app`.
5. Download the JSON and save it to `~/.config/utsushi/credentials.json` (or set `UTSUSHI_CREDENTIALS` to its path).

The first `utsushi convert ... --to slides` opens a browser for you to authorize the desktop client. The resulting OAuth token is cached in your macOS Keychain via `keyring`; it refreshes automatically.
