#!/usr/bin/env python  # noqa: CPY001
"""Install python traceback formatter in the current virtualenv."""

from __future__ import annotations

import site
import sys
from pathlib import Path


site = Path(site.getsitepackages()[0])
hook = site / "_traceback.pth"
activate = """import pretty_errors

pretty_errors.configure(
    separator_character="*",
    filename_display=pretty_errors.FILENAME_COMPACT,
    line_number_first=True,
    display_link=False,
    lines_before=5,
    lines_after=2,
    line_color=pretty_errors.RED + "> " + pretty_errors.default_config.line_color,
    code_color="  " + pretty_errors.default_config.line_color,
    truncate_code=True,
    display_locals=True,
    trace_lines_before=True,
    display_trace_locals=True,
)
"""


def main() -> int:
    if sys.prefix == sys.base_prefix:
        sys.stderr.write("Should be run inside a virtual environment!")
        return 1

    try:
        if not hook.exists():
            with hook.open("w") as stream:
                stream.write(activate)
                sys.stdout.write(f"traceback hook installed at {hook}")
        else:
            hook.unlink()
            sys.stdout.write("traceback hook uninstalled")
    except OSError as e:
        sys.stderr.write(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
