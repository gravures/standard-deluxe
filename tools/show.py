#!/usr/bin/env python3
# ruff: noqa: CPY001, T201, D100, D103
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from deluxe._version import __version__


def main() -> int:
    try:
        toml = Path(__file__).parent.parent / "pyproject.toml"
    except OSError:
        return 1

    buffer = toml.read_text()
    conf = tomllib.loads(buffer)
    print("Name:", conf["project"]["name"])
    print("Summary:", conf["project"]["description"])
    print("Authors:", conf["project"]["authors"])
    print("Version:", __version__)
    print("License:", conf["project"]["license"]["text"])
    print("Urls:", conf["project"]["urls"])
    print("Requires Python:", conf["project"]["requires-python"])
    print("Platforms:", "All")
    print("Keywords:", conf["project"]["keywords"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
