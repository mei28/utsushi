"""Typer CLI entry point."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import typer

from utsushi import __version__, pipeline

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
    src: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    to: TargetFormat = typer.Option(..., "--to", help="Target format."),
    out: Path | None = typer.Option(None, "--out", help="Output path (default: replace ext)."),
) -> None:
    """Convert a deck to the target format."""
    try:
        result = pipeline.convert(src, target=to.value, dst=out)
    except NotImplementedError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(str(result))


if __name__ == "__main__":
    app()
