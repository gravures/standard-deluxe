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
# ruff: noqa: D301
"""ANSI escape code support module.

This module generates ANSI character codes for printing colors to terminals or
modifying its buffer and moving the cursor. The set of generated escape sequences
is deliberately kept tight for high portability and can be translated for Windows
terminal by the `colorama <https://github.com/tartley/colorama>`_ module.

.. note::
    On Windows platform, the presence of colorama is checked at import time and
    automatically activated if found.

Usages
______

Style text with colors and modes::

    >>> from deluxe.console.ansi import Fg, Bg, Mode, style
    >>> print(f"{style(Fg.RED)}Error:{style(Mode.RESET_ALL)} something went wrong")
    >>> print(f"{style(Fg.GREEN, Bg.WHITE, Mode.BRIGHT)}Success!{style(Mode.RESET_ALL)}")

Combine multiple modes::

    >>> from deluxe.console.ansi import Fg, Mode, style
    >>> print(f"{style(Fg.BLUE, Mode.UNDERLINE, Mode.ITALIC)}link text{style(Mode.RESET_ALL)}")

Use light (bright) color variants::

    >>> from deluxe.console.ansi import Fg, Bg, Mode, style
    >>> print(f"{style(Fg.LIGHT_CYAN, Bg.BLACK)}bright cyan on black{style(Mode.RESET_ALL)}")

Clear screen and set title::

    >>> from deluxe.console.ansi import clear_fullscreen, set_title
    >>> print(clear_fullscreen())
    >>> print(set_title("My Application"))

Work with escape sequences directly::

    >>> from deluxe.console.ansi import strip_esc, length, bell
    >>> strip_esc("\\x1b[31mHello\\x1b[0m")
    'Hello'
    >>> length("\\x1b[31mHello\\x1b[0m")
    5
    >>> print(bell())  # audible alert

Clear lines::

    >>> from deluxe.console.ansi import clear_line, clear_line_after
    >>> print(f"some text{clear_line_after()}")
    >>> print(f"{clear_line()}cleared line")

.. seealso::
    * `colorama <https://github.com/tartley/colorama>`_
    * `termstandard/colors <https://github.com/termstandard/colors>`_
    * `ANSI escape code (Wikipedia) <https://en.wikipedia.org/wiki/ANSI_escape_code>`_
"""

from __future__ import annotations

import enum
import importlib.util
import re
import sys
from abc import abstractmethod
from typing import (
    ClassVar,
    Literal,
    Protocol,
    TypeVar,
    final,
)


__all__ = [
    "BELL",
    "C0",
    "C1",
    "CSI",
    "CSI_CMD",
    "CSI_PARAM",
    "ED",
    "EL",
    "OSC",
    "OSC_CMD",
    "OSC_PARAM",
    "SGR",
    "SGR_PARAMS",
    "TITLE",
    "Background",
    "Bg",
    "Fg",
    "Foreground",
    "Mode",
    "bell",
    "clear_fullscreen",
    "clear_line",
    "clear_line_after",
    "clear_line_before",
    "clear_screen",
    "clear_screen_before",
    "clear_scrollback",
    "length",
    "set_title",
    "strip_esc",
    "style",
]


# NOTE: see https://en.wikipedia.org/wiki/C1_control_codes
# TODO: cursor positioning


if sys.platform in {"win32", "cygwin"} and importlib.util.find_spec("colorama"):
    colorama = importlib.import_module("colorama")  # pragma: no cover
    colorama.just_fix_windows_console()  # pragma: no cover


class C0(Protocol):
    """C0 Control codes Protocol.

    C0 control codes are ASCII control characters (0x00-0x1F) that
    perform basic terminal control functions like bell, backspace,
    and line feed.

    When called, returns the associated control character sequence.
    """

    def __call__(self) -> str: ...  # noqa: D102


class BELL(C0):
    """Make an audible noise.

    This class implements the C0 control code for the terminal bell
    character (ASCII 0x07). When called, returns the bell character
    (``\\a``).
    """

    def __call__(self) -> str:  # noqa: D102
        return "\a"


bell = BELL()
"""Audible terminal bell. When called, returns the bell character (``\\a``)."""


class C1(C0, Protocol):
    """C1 ANSI Escape Sequence Protocol.

    C1 control codes are ESC-prefixed sequences (0x80-0x9F) used for
    extended terminal control functions. This protocol defines the
    base for ANSI escape sequences.

    When called, returns the complete escape sequence.
    """

    prefix: ClassVar[str] = "\033"

    @abstractmethod
    def __call__(self) -> str: ...  # noqa: D102


CSI_CMD = TypeVar("CSI_CMD", bound=Literal["", "m", "J", "K"])
"""Type variable for CSI command characters."""
CSI_PARAM = TypeVar(name="CSI_PARAM", bound=int)
"""Type variable for CSI integer parameters."""


class CSI(C1, Protocol[CSI_CMD, CSI_PARAM]):
    """Control Sequence Introducer Protocol.

    CSI sequences are used to control cursor movement, display editing,
    and character attributes. The format is: ``ESC [ <params> <command>``

    When initialized with ``*params``, stores them as integer parameters.
    When called, returns the compiled CSI sequence: ``ESC [ <param1> ; <param2> ... <command>``.
    When converted to string, returns the command character.

    Args:
        *params: Integer parameters for the CSI sequence. Multiple parameters
            are separated by semicolons in the compiled sequence.

    Attributes:
        prefix: The CSI prefix string ``ESC [``.
        params: Tuple of integer parameters for the sequence.
        cmd: The command character (e.g., ``'m'`` for SGR, ``'J'`` for ED).
    """

    prefix: ClassVar[str] = f"{C1.prefix}["
    params: tuple[CSI_PARAM, ...]
    cmd: CSI_CMD

    def __init__(self, *params: CSI_PARAM) -> None:
        self.params = params

    def __call__(self) -> str:  # noqa: D102
        return f"{CSI.prefix}{';'.join(map(str, self.params))}{self}"

    def __str__(self) -> str:
        return self.cmd


OSC_CMD = TypeVar("OSC_CMD", bound=str)
"""Type variable for OSC command strings."""
OSC_PARAM = TypeVar("OSC_PARAM", bound=int | str)
"""Type variable for OSC parameters."""


class OSC(C1, Protocol[OSC_CMD, OSC_PARAM]):
    """Operating System Command Protocol.

    OSC sequences are used to configure system settings like window
    titles, colors, and other terminal features. The format is:
    ``ESC ] <params> <command>``

    When initialized with ``*params``, stores them as parameters.
    When called, returns the compiled OSC sequence: ``ESC ] <param1> ; <param2> ... <command>``.
    When converted to string, returns the command string.

    Args:
        *params: Parameters for the OSC sequence (integers or strings).
            Multiple parameters are separated by semicolons in the compiled sequence.

    Attributes:
        prefix: The OSC prefix string ``ESC ]``.
        params: Tuple of parameters for the sequence.
        cmd: The command string (often terminated by BEL or ST).
    """

    prefix: ClassVar[str] = f"{C1.prefix}]"
    params: tuple[OSC_PARAM, ...]
    cmd: OSC_CMD

    def __init__(self, *params: OSC_PARAM) -> None:
        self.params = params

    def __call__(self) -> str:  # noqa: D102
        return f"{OSC.prefix}{';'.join(map(str, self.params))}{self}"

    def __str__(self) -> str:
        return str(self.cmd)


class TITLE(OSC[str, Literal[0, 2] | str]):
    """Title OSC command.

    This class implements the OSC sequence for setting the terminal
    window title. The command is terminated by the bell character.
    """

    cmd: str = BELL()()


class ED(CSI[Literal["J"], Literal[0, 1, 2, 3]]):
    """Erase in display.

    This class implements the CSI sequence for erasing parts of the
    terminal display. The command character is ``'J'``.

    Parameters:
        0: Clear from cursor to end of screen.
        1: Clear from cursor to beginning of screen.
        2: Clear entire screen.
        3: Clear screen and scrollback buffer.
    """

    cmd: Literal["J"] = "J"


clear_screen = ED(0)
"""Clear from cursor to end of screen."""
clear_screen_before = ED(1)
"""Clear from cursor to beginning of screen."""
clear_fullscreen = ED(2)
"""Clear entire screen."""
clear_scrollback = ED(3)
"""Clear screen and scrollback buffer."""


class EL(CSI[Literal["K"], Literal[0, 1, 2]]):
    """Erase in line.

    This class implements the CSI sequence for erasing parts of the
    current line. The command character is ``'K'``.

    Parameters:
        0: Clear from cursor to end of line.
        1: Clear from cursor to beginning of line.
        2: Clear entire line.
    """

    cmd: Literal["K"] = "K"


clear_line = EL(2)
"""Clear entire line."""
clear_line_before = EL(1)
"""Clear from cursor to beginning of line."""
clear_line_after = EL(0)
"""Clear from cursor to end of line."""


@enum.unique
class Mode(enum.IntEnum):
    """ANSI SGR mode parameters.

    These parameters control text styling attributes like brightness,
    italic, underline, etc. They are used with the :class:`SGR` class
    to create styled text.
    """

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
    """ANSI SGR foreground color parameters.

    Standard colors (30-37) and bright/light variants (90-97).
    The light variants are not part of the original ANSI standard
    but are widely supported in modern terminals.

    These parameters are used with the :class:`SGR` class to set
    foreground text colors.
    """

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


Fg = Foreground
"""Shorthand alias for :class:`Foreground`."""


@enum.unique
class Background(enum.IntEnum):
    """ANSI SGR background color parameters.

    Standard colors (40-47) and bright/light variants (100-107).
    The light variants are not part of the original ANSI standard
    but are widely supported in modern terminals.

    These parameters are used with the :class:`SGR` class to set
    background text colors.
    """

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


Bg = Background
"""Shorthand alias for :class:`Background`."""


SGR_PARAMS = Literal[
    Mode.BRIGHT,
    Mode.DIM,
    Mode.NORMAL,
    Mode.ITALIC,
    Mode.RESET_ALL,
    Mode.UNDERLINE,
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
"""Union type for valid SGR parameters.

Combines :class:`Mode`, :class:`Foreground`, and :class:`Background` values
that can be passed to :class:`SGR` or :func:`style`.
"""


@final
class SGR(CSI[Literal["m"], SGR_PARAMS]):
    """Select Graphic Rendition (SGR) parameters.

    SGR sequences control text styling attributes like colors, bold,
    italic, etc. The format is: ``ESC [ <params> m``

    When initialized with ``*params``, the parameters are processed to ensure
    proper ordering and deduplication:
    - Mode parameters: Last occurrence of each mode wins
    - Background parameters: Only the last background color is kept
    - Foreground parameters: Only the last foreground color is kept
    - All parameters are ordered as: modes, background, foreground

    Examples::

        >>> sgr = SGR(Mode.BRIGHT, Foreground.RED, Background.BLUE)
        >>> sgr()
        '\\x1b[1;44;31m'

    Args:
        *params: One or more :class:`Mode`, :class:`Foreground`, or
            :class:`Background` values to apply. Parameters are automatically
            ordered and deduplicated.
    """

    def __init__(self, *params: SGR_PARAMS) -> None:
        modes: dict[SGR_PARAMS, SGR_PARAMS] = {}
        fg: tuple[SGR_PARAMS, ...] = ()
        bg: tuple[SGR_PARAMS, ...] = ()
        for param in params:
            match param:
                case Mode():
                    modes.pop(param, None)
                    modes[param] = param
                case Foreground():
                    fg = (param,)
                case Background():
                    bg = (param,)
        super().__init__(*modes.values(), *bg, *fg)

    cmd = "m"


def style(*args: SGR_PARAMS) -> str:
    """Return an ANSI styling characters sequence.

    This is a convenience function that creates an :class:`SGR` sequence
    and immediately compiles it to a string.

    Args:
        *args: :class:`Mode`, :class:`Foreground`, or :class:`Background` values.

    Returns:
        :obj:`str`: The compiled ANSI escape sequence for styling.

    Examples::

        >>> style(Fg.RED, Bg.WHITE, Mode.BRIGHT)
        '\\x1b[1;47;31m'
        >>> print(f"{style(Fg.GREEN)}Hello{style(Mode.RESET_ALL)} World")
    """
    sgr_ = SGR(*args)
    return sgr_()


def set_title(title: str) -> str:
    """Return an ANSI characters sequence to set the terminal window title.

    Uses the OSC (Operating System Command) sequence to set the terminal
    title bar text.

    Args:
        title (:obj:`str`): The title text to set.

    Returns:
        :obj:`str`: The compiled ANSI escape sequence for setting the title.

    Examples::

        >>> set_title('My Application')
        '\\x1b]2;My Application\\x07'
    """
    osc_ = TITLE(2, title)
    return osc_()


_STRIP_ESC = re.compile(
    r"""
    \x1b\[(?:\d+;)*\d*[JKm]  # CSI: ESC [ <params> <command>
    |
    \x1b\].*?\a               # OSC: ESC ] <content> BEL
    """,
    flags=re.VERBOSE,
)


def strip_esc(string: str) -> str:
    """Strip ANSI escape sequences from a string.

    Removes both CSI (Control Sequence Introducer) and OSC (Operating System
    Command) escape sequences from the input string.

    Args:
        string (:obj:`str`): The string potentially containing ANSI escape sequences.

    Returns:
        :obj:`str`: The input string with all ANSI escape sequences removed.

    Examples::

        >>> strip_esc('\\x1b[31mHello\\x1b[0m')
        'Hello'
        >>> strip_esc('\\x1b]2;Title\\x07')
        ''
    """
    return re.sub(_STRIP_ESC, "", string)


def length(string: str) -> int:
    """Length of an ANSI escaped string.

    Returns the visible length of a string by first stripping all ANSI
    escape sequences.

    Args:
        string (:obj:`str`): The string potentially containing ANSI escape sequences.

    Returns:
        :obj:`int`: The length of the string after removing escape sequences.

    Examples::

        >>> length('\\x1b[31mHello\\x1b[0m')
        5
        >>> length('\\x1b]2;Title\\x07')
        0
    """
    return len(strip_esc(string))
