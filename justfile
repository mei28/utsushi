# utsushi task runner

# Show available recipes
default:
    @just --list

# Install dependencies (creates .venv)
install:
    uv sync

# Run the CLI (passes args through: just run convert deck.key --to pptx)
run *args:
    uv run utsushi {{args}}

# Run tests
test *args:
    uv run pytest {{args}}

# Lint
lint:
    uv run ruff check .

# Format
fmt:
    uv run ruff format .

# Type check
typecheck:
    uv run mypy

# All checks (lint + typecheck + test)
check: lint typecheck test
