"""Typer CLI entry point."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import rich
import typer

from utsushi import __version__, normalize, pipeline
from utsushi import diff as diff_mod

app = typer.Typer(
    name="utsushi",
    help="Slide deck transcoder for Keynote / PowerPoint / Google Slides.",
    no_args_is_help=True,
)


class TargetFormat(StrEnum):
    """CLI-facing target format choices. 'slides' is reserved (not implemented)."""

    pptx = "pptx"
    key = "key"
    slides = "slides"


@app.callback()
def _root() -> None:
    """utsushi root command."""


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@app.command()
def convert(
    src: str = typer.Argument(..., help="Source deck path or Google Slides URL."),
    to: TargetFormat = typer.Option(..., "--to", help="Target format."),
    out: Path | None = typer.Option(None, "--out", help="Output path (default: replace ext)."),
    folder: str | None = typer.Option(
        None, "--folder", help="Drive folder id (only with --to slides)."
    ),
) -> None:
    """Convert a deck to the target format."""
    try:
        result = pipeline.convert(src, target=to.value, dst=out, folder_id=folder)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(str(result))


@app.command(name="normalize")
def normalize_cmd(
    target: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    theme: Path = typer.Option(
        ..., "--theme", exists=True, dir_okay=False, readable=True, help="Template .pptx."
    ),
    out: Path | None = typer.Option(None, "--out", help="Output path."),
    in_place: bool = typer.Option(False, "--in-place", help="Overwrite the target deck."),
) -> None:
    """Overwrite a deck's theme with a corporate template's theme."""
    try:
        result = normalize.apply_theme(target, theme, out=out, in_place=in_place)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(str(result))


@app.command()
def diff(
    left: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    right: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
) -> None:
    """Compare two PPTX decks at the XML-part level."""
    report = diff_mod.diff_decks(left, right)
    if report.is_empty():
        rich.print("[green]decks are identical at the XML level[/green]")
        return

    for name in report.only_in_left:
        rich.print(f"[red]- only in left:[/red]  {name}")
    for name in report.only_in_right:
        rich.print(f"[green]+ only in right:[/green] {name}")
    for part in report.changed_parts:
        rich.print(f"[yellow]~ changed:[/yellow] {part.partname}")
        rich.print(part.unified)

    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
