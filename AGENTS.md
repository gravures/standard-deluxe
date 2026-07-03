# Standard Deluxe Agent Guidelines

This document provides instructions for agentic coding agents operating in this repository.

## Project Structure

- **Source Code**: `src/deluxe`
- **Documentation Templates**: `docs/`
- **Tests**: `tests/`
- **Dependencies**: Managed with `uv`. See `pyproject.toml` and `uv.lock`.
- **Python**: Version-3.11

## Build, Lint, and Test

`mise` is used to manage almost all the tasks on this project, run `mise tasks`
to view all available tasks.

- **Build**: `mise run build`
- **Lint**: `mise run lint [files,...]`
- **Check Format**: `mise run lint:format [files,...]`
- **Format**: `mise run code:format [files,...]`
- **Type Checking**: `mise run typecheck [files,...]`
- **Run a single test**: `mise run test:this test_name`
- **Test full suite with coverage records and report**: `mise run test:cover [test_name]`

## Code Style

- **Formatting**: We use `ruff` for formatting defined in `ruff.toml`.
- **Types**: The project is fully typed and checked with `basedpyright`.
- **Naming Conventions**: Follow `PEP 8` naming conventions.
- **Docstrings**: Google-style docstrings are required.
- **Commits**: Commit messages must follow the Conventional Commits specification.

## Test Conventions

- **Framework**: use `pytest`. Test environment is set up by `mise run setup`,
  no extra install needed.
- **Test unit**: each test is implemented as a module level function (NO test class).
- **Structure**: tests are grouped by logical unit (tests on a class, multiple_declaratorsodules functions,..)
  into one python file.
- **File naming**: descriptive about tested unit should and end with `_test.py`.
- **Test function names** should be descriptive and prefixed with `test_`.
