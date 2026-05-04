"""Typer CLI entry point."""

from __future__ import annotations

import typer

from utsushi import __version__

app = typer.Typer(
    name="utsushi",
    help="Slide deck transcoder for Keynote / PowerPoint / Google Slides.",
    no_args_is_help=True,
)


# Force subcommand mode even when only one command is registered.
# Without this, Typer treats a single-command app as having that command at the root.
@app.callback()
def _root() -> None:
    """utsushi root command."""


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
