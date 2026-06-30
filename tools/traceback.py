#!/usr/bin/env python
# Copyright (c) 2025 - Gilles Coissac
# This file is part of standard-deluxe library.
#
# standard-deluxe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# standard-deluxe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with standard-deluxe. If not, see <https://www.gnu.org/licenses/>
#
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


def main() -> int:  # noqa: D103
    if sys.prefix == sys.base_prefix:
        sys.stderr.write("Should be run inside a virtual environment!")
        return 1

    install = "--remove" not in sys.argv
    try:  # noqa: PLW0717
        if install and not hook.exists():
            with hook.open("w") as stream:
                stream.write(activate)
                sys.stdout.write(f"traceback hook installed at {hook}")
        elif not install and hook.exists():
            hook.unlink()
            sys.stdout.write("traceback hook uninstalled")
    except OSError as e:
        sys.stderr.write(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
