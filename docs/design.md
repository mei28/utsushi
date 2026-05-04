# utsushi — Design Notes

Carried over from a dotfiles-side discussion (2026-05-04). This document is the source of truth going forward; further discussion happens in this repo.

## Goal

Convert presentation decks among three formats with maximum fidelity, keeping the result editable in the target tool:

- `.pptx` (PowerPoint)
- `.key` (Keynote)
- Google Slides (`application/vnd.google-apps.presentation`)

Out of scope for fidelity: fonts (acceptable to fix manually post-conversion), Magic Move, SmartArt, embedded video, complex animations.

In scope for fidelity: font sizes, paragraph widths, slide styles, master slides, color tables, placeholder roles.

Optional ambition: Slidev integration. Treat as a *parallel* system, not a member of the round-trip group (see "Slidev" below).

## Constraints

- macOS only — Keynote.app required for `.key` handling.
- Any language. Python chosen because `python-pptx` is the only mature library for PPTX theme/master XML manipulation.
- Editable output required (no rasterization for the three core formats).

## Architecture

```
utsushi/
├── detect.py             format detection (extension + zip magic + Drive URL)
├── adapters/
│   ├── keynote.py        Keynote.app via osascript
│   ├── drive.py          google-api-python-client wrapper
│   └── pptx.py           python-pptx (theme/master ops)
├── pipeline.py           routing, PPTX-as-hub for indirect paths
├── normalize.py          theme/colorscheme/master enforcement
├── diff.py               unzip + XML diff for round-trip QA
└── cli.py                Typer entry point
```

### Routing table

```
.key   → .pptx     : Keynote.app export
.key   → Slides    : Keynote → PPTX → Drive upload
.pptx  → .key      : Keynote.app import + save
.pptx  → Slides    : Drive upload, mimeType=presentation
Slides → .pptx     : Drive files.export
Slides → .key      : Drive → PPTX → Keynote.app import
```

PPTX is the hub. Six paths collapse to four adapters.

## Engine choices (and why we don't reimplement them)

| Conversion | Engine | Reason |
|---|---|---|
| Keynote ⇄ PPTX | `osascript` driving Keynote.app | Apple's native importer/exporter. Highest preservation of master, color scheme, geometry. No third party beats it. |
| Slides ⇄ PPTX | Drive API (`files.copy` + `files.export`) | Google owns the conversion. SaaS converters wrap LibreOffice and lose master/theme detail. |
| PPTX theme/master editing | `python-pptx` | Only mature library; alternatives are write-only (`pptxgenjs`, `officegen`). |

## What survives across formats

| Element | PPTX↔Keynote | PPTX↔Slides | Notes |
|---|---|---|---|
| Font size (pt) | Preserved | Preserved | numeric pass-through |
| Text frame geometry | Preserved (EMU) | Mostly preserved | Slides rounds to px |
| Line / character spacing | Preserved | Partial | Slides rounds to % |
| Master slides | Mapped to Keynote "theme" | Mapped to Slides "theme"; multi-master collapsed | Slides has weak master hierarchy |
| Color table (theme colors) | Mapped to Keynote palette | Mapped to Slides theme (accent1-6, dk1/lt1, dk2/lt2) | PPTX `theme1.xml` `<a:clrScheme>` is the hub |
| Placeholder kind | Preserved | Preserved | title/body/idx |
| Custom shapes (`a:custGeom`) | Preserved | Path preserved, edit limited | |
| Animations / transitions | Partial | Mostly static | acceptable loss |

## Differentiating value (beyond what existing tools do)

The conversion itself is delegated. The reasons to write `utsushi`:

1. **One CLI, format-agnostic.** Detect input, route to the right engine, produce target. No mental switch among `osascript`, Drive console, Python scripts.
2. **Theme normalization.** After conversion, overwrite `theme1.xml` (`<a:clrScheme>`, `<a:fontScheme>`, `<a:fmtScheme>`) and `slideMaster*.xml` with a corporate template. Existing tools don't do this.
3. **Round-trip QA.** Unzip PPTX, normalize XML, diff before/after. Detects silent loss in conversion chains.
4. **Drive auth handled.** OAuth desktop flow, token in macOS Keychain via `keyring`. User doesn't think about credentials.
5. **PPTX as canonical, git-versionable.** PPTX unzipped to XML diffs cleanly. Keynote/Slides/Slidev cannot.

## Slidev

Treated as a separate, parallel system. Not part of the round-trip group.

| Direction | Feasibility | Notes |
|---|---|---|
| Slidev → PPTX | `slidev export --format pptx` works | Each slide is a Playwright-rendered raster image embedded in PPTX. Not editable. Distribution-only. |
| PPTX → Slidev | Effectively impossible to automate well | `pptx2md` extracts text but loses geometry/colors. Reconstruction, not conversion. |
| Keynote → Slidev | No direct path | Same as above via PPTX. |
| Slides → Slidev | No direct path | Same. |

Recommendation: if using Slidev, keep its Markdown as source of truth and emit PPTX raster for distribution only. Don't try to round-trip.

## Tech stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.12+ | `python-pptx` decisive |
| CLI framework | Typer | argparse-based, type hints |
| Output formatting | Rich | progress, errors |
| PPTX manipulation | python-pptx | only mature option |
| Drive client | google-api-python-client + google-auth-oauthlib | official |
| Credential storage | keyring | uses macOS Keychain |
| Keynote control | subprocess + osascript | trivial, reliable |
| Packaging | uv (`uv tool install` / `pipx`) | macOS-friendly distribution |

## Known risks / gotchas

1. **Keynote.app concurrency.** Opening multiple decks programmatically can corrupt state. Implement a serial queue / lock around `osascript` calls.
2. **Drive OAuth.** Service accounts cannot access user Drive. Must use OAuth desktop flow. Token refresh handling required.
3. **PPTX validity from Keynote export.** Occasionally produces `.pptx` that `python-pptx` cannot open. Run `zip -T` validation after Keynote export; surface clear error.
4. **Theme overwrite scope.** `slideMaster*.xml` references layouts; replacing only `theme1.xml` may leave inconsistencies. Normalize must touch master + layouts together.
5. **Drive rate limits.** Batch operations need exponential backoff.

## CLI surface

```bash
# Single conversion (target extension implied)
utsushi convert deck.key --to pptx
utsushi convert deck.pptx --to slides --folder "Work/Decks"
utsushi convert https://docs.google.com/presentation/d/XXX --to keynote

# Theme/master enforcement
utsushi normalize deck.pptx --theme corp-template.pptx

# Round-trip QA
utsushi diff before.pptx after.pptx

# Watch / sync
utsushi sync ./decks --to drive --folder "Decks"
```

## Optional future: GUI

If demand arises, a SwiftUI menu-bar app shelling out to the CLI:

- Drop zone for files
- Target format selector
- `Process` invocation of `utsushi convert`
- Notification Center on completion

Estimated 1–2 days after CLI is stable. Not part of MVP.

## Roadmap

| Phase | Estimate | Deliverable |
|---|---|---|
| 1 | ½ day | `keynote.py` osascript wrapper + one-way conversion smoke test |
| 2 | ½ day | `drive.py` OAuth flow + upload/export |
| 3 | ½ day | `pipeline.py` routing + Typer CLI MVP |
| 4 | 1 day | `normalize.py` theme/master overwrite |
| 5 | ½ day | `diff.py` XML diff |
| 6 | optional | SwiftUI menu-bar wrapper or Automator Quick Action |

MVP (phases 1–3): ~1.5 days. Differentiating layer (phase 4): the actual reason to write this.

## Naming

- Project / command: `utsushi` (写し — to transcribe)
- PyPI distribution: `utsushi-cli` (avoids confusion with archived EPSON `utsushi` scanner driver in PyPI search results, should it ever appear)
- Tagline: "slide utsuslide for keynote / pptx / slides"

## Open questions

- Drive API client_id distribution: ship a default OAuth client, or require user-provided credentials? Default is friendlier; user-provided avoids quota sharing.
- Keynote export format options: `Microsoft PowerPoint` only, or also offer `as PDF`?
- Should `normalize` operate in place or always emit a copy? Lean toward copy by default with `--in-place` flag.
- Slidev: include a `utsushi to-slidev` that does best-effort text extraction (acknowledging the result is not faithful), or refuse and document why?
