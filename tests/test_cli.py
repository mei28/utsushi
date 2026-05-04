"""Smoke tests for the Typer CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from utsushi import __version__
from utsushi.cli import app

runner = CliRunner()


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    # no_args_is_help shows the help text; exit code can be 0 or 2 depending on Typer version
    assert "Usage" in result.stdout
