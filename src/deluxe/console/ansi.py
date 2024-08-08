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
"""ANSI escape code support module.

This module generates ANSI character codes for printing
colors to terminals or modify its buffer and move the cursor.
The set of generated escape sequences is deliberately kept tight.
This way those sequences are hightly portable and could be
translated for Windows terminal by the colorama module.

On Windows platform the presence of coloroma is checked
at import time and automatically activated by this module
if found.

Usage:
    from deluxe.console.ansi import FG, BG, ST, style

    print(f"{style(FG.RED, BG.YELLOW, ST.BRIGHT)} give me colors... ")

see: https://github.com/tartley/colorama
     https://github.com//termstandard/colors
     https://en.wikipedia.org/wiki/ANSI_escape_code
"""

from __future__ import annotations

import enum
import importlib.util
import sys
from abc import abstractmethod
from typing import (
    ClassVar,
    Literal,
    Protocol,
    TypeVar,
    Union,
    final,
)


# NOTE: see https://en.wikipedia.org/wiki/C1_control_codes
# TODO: cursor positioning


if sys.platform in {"win32", "cygwin"} and importlib.util.find_spec("colorama"):
    colorama = importlib.import_module("colorama")
    colorama.just_fix_windows_console()


class C0(Protocol):
    """C0 Control codes Protocol."""

    @abstractmethod
    def __call__(self) -> str:
        """Should return the associate characters sequence."""
        ...


class BELL(C0):
    """Make an audible noise."""

    def __call__(self) -> str:
        """Returns the bell characters sequence."""
        return "\a"  # noqa: DOC201


class C1(C0, Protocol):
    """C1 ANSI Escape Sequence Protocol."""

    prefix: ClassVar[str] = "\033"  # ASCII escape character

    @abstractmethod
    def __call__(self) -> str:
        """Should return the associate characters sequence."""
        ...


CSI_CMD = TypeVar("CSI_CMD", bound=Literal["", "m", "J", "K"])
CSI_PARAM = TypeVar(name="CSI_PARAM", bound=int)


class CSI(C1, Protocol[CSI_CMD, CSI_PARAM]):
    """Control Sequence Introducer Protocol."""

    prefix: ClassVar[str] = f"{C1.prefix}["
    params: tuple[CSI_PARAM, ...]
    cmd: CSI_CMD

    def __init__(self, *params: CSI_PARAM) -> None:
        self.params = params

    def __call__(self) -> str:
        """Returns a compiled CSI characters sequence: ESC [ <param> ; <param> ... <command>."""
        return f"{CSI.prefix}{';'.join(map(str, self.params))}{self}"  # noqa: DOC201

    def __str__(self) -> str:
        return self.cmd


OSC_CMD = TypeVar("OSC_CMD", bound=str)
OSC_PARAM = TypeVar("OSC_PARAM", bound=int | str)


class OSC(C1, Protocol[OSC_CMD, OSC_PARAM]):
    """Operating System Command Protocol."""

    prefix: ClassVar[str] = f"{C1.prefix}]"
    params: tuple[OSC_PARAM, ...]
    cmd: OSC_CMD

    def __init__(self, *params: OSC_PARAM) -> None:
        self.params = params

    def __call__(self) -> str:
        """Returns a compiled OSC characters sequence: ESC ] <param> ; <param> ... <command>."""
        return f"{OSC.prefix}{';'.join(map(str, self.params))}{self}"  # noqa: DOC201

    def __str__(self) -> str:
        return str(self.cmd)


class TITLE(OSC[str, Union[Literal[0, 2], str]]):
    """Title OSC command."""

    cmd = BELL()()


class ED(CSI[Literal["J"], Literal[0, 1, 2, 3]]):
    """Erase in display."""

    cmd = "J"


class EL(CSI[Literal["K"], Literal[0, 1, 2]]):
    """Erase in line."""

    cmd = "K"


@enum.unique
class Style(enum.IntEnum):
    """Enum for SGR style parameters."""

    RESET_ALL = 0
    BRIGHT = 1
    DIM = 2
    NORMAL = 22
    ITALIC = 3
    UNDERLINE = 4
    SLOW_BLINK = 5
    BLINK = 6
    INVERT = 7
    # HIDE = 8
    # BOLD = 21


@enum.unique
class Foreground(enum.IntEnum):
    """Enum for SGR foreground color parameters."""

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 39
    # Not part of the standard.
    LIGHT_BLACK = 90
    LIGHT_RED = 91
    LIGHT_GREEN = 92
    LIGHT_YELLOW = 93
    LIGHT_BLUE = 94
    LIGHT_MAGENTA = 95
    LIGHT_CYAN = 96
    LIGHT_WHITE = 97


@enum.unique
class Background(enum.IntEnum):
    """Enum for SGR background color parameters."""

    BLACK = 40
    RED = 41
    GREEN = 42
    YELLOW = 43
    BLUE = 44
    MAGENTA = 45
    CYAN = 46
    WHITE = 47
    RESET = 49
    # Not part of the standard.
    LIGHT_BLACK = 100
    LIGHT_RED = 101
    LIGHT_GREEN = 102
    LIGHT_YELLOW = 103
    LIGHT_BLUE = 104
    LIGHT_MAGENTA = 105
    LIGHT_CYAN = 106
    LIGHT_WHITE = 107


SGR_Params = Literal[
    Style.BRIGHT,
    Style.DIM,
    Style.NORMAL,
    Style.RESET_ALL,
    Foreground.BLACK,
    Foreground.BLUE,
    Foreground.CYAN,
    Foreground.GREEN,
    Foreground.MAGENTA,
    Foreground.RED,
    Foreground.YELLOW,
    Foreground.WHITE,
    Foreground.RESET,
    Foreground.LIGHT_BLACK,
    Foreground.LIGHT_RED,
    Foreground.LIGHT_BLUE,
    Foreground.LIGHT_CYAN,
    Foreground.LIGHT_GREEN,
    Foreground.LIGHT_MAGENTA,
    Foreground.LIGHT_WHITE,
    Foreground.LIGHT_YELLOW,
    Background.BLACK,
    Background.BLUE,
    Background.CYAN,
    Background.GREEN,
    Background.MAGENTA,
    Background.RED,
    Background.YELLOW,
    Background.WHITE,
    Background.RESET,
    Background.LIGHT_BLACK,
    Background.LIGHT_RED,
    Background.LIGHT_BLUE,
    Background.LIGHT_CYAN,
    Background.LIGHT_GREEN,
    Background.LIGHT_MAGENTA,
    Background.LIGHT_WHITE,
    Background.LIGHT_YELLOW,
]


@final
class SGR(CSI[Literal["m"], SGR_Params]):
    """Select Graphic Rendition parameters."""

    cmd = "m"


FG = Foreground
BG = Background
ST = Style

bell = BELL()
clear_screen = ED(0)
clear_screen_before = ED(1)
clear_fullscreen = ED(2)
clear_scrollback = ED(3)
clear_line = EL(2)
clear_line_before = EL(1)
clear_line_after = EL(0)


def style(*args: SGR_Params) -> str:
    """Return an ANSI styling characters sequence."""
    _sgr = SGR(*args)
    return _sgr()  # noqa: DOC201


def set_title(title: str) -> str:
    """Return an ANSI characters sequence."""
    _osc = TITLE(2, title)
    return _osc()  # noqa: DOC201


__ALL__ = [
    "bell",
    "clear_screen",
    "clear_screen_before",
    "clear_fullscreen",
    "clear_scrollback",
    "clear_line",
    "clear_line_before",
    "clear_line_after",
    "set_style",
    "set_title",
    "FG",
    "BG",
    "ST",
]
