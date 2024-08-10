# Copyright (c) 2024 - Gilles Coissac
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
"""Console package."""

from __future__ import annotations

from deluxe.console.ansi import (
    BG,
    FG,
    ST,
    bell,
    clear_fullscreen,
    clear_line,
    clear_line_after,
    clear_line_before,
    clear_screen,
    clear_screen_before,
    clear_scrollback,
    set_title,
    style,
)
from deluxe.console.argparser import PrettyHelpFormatter, PrettyParser


__all__ = [
    "BG",
    "FG",
    "ST",
    "PrettyHelpFormatter",
    "PrettyParser",
    "bell",
    "clear_fullscreen",
    "clear_line",
    "clear_line_after",
    "clear_line_before",
    "clear_screen",
    "clear_screen_before",
    "clear_scrollback",
    "set_title",
    "style",
]
