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
# ruff: noqa: PYI019, PYI066, UP031
"""Argument parser module with ANSI markup support.

This module extends Python's argparse module to provide enhanced command-line
argument parsing with ANSI escape code support for colored and styled output.
It includes custom help formatters that can display colored help text.
The :class:`PrettyParser` class is the main entry to look at in this module,
it adds shell completion capabilities and improved error handling.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import warnings
from argparse import _MutuallyExclusiveGroup  # pyright: ignore[reportPrivateUsage]
from typing import IO, TYPE_CHECKING, Any, ClassVar, Final, TypeVar, cast, no_type_check

from deluxe.console import ansi
from deluxe.console.wrap import AnsiTextWrapper


try:
    from gettext import (
        gettext as _,
        ngettext,  # pyright:ignore[reportAssignmentType]
    )
except ImportError:  # pragma: no cover

    def _(message: str) -> str:
        return message

    def ngettext(singular: object, plural: object, n: int) -> object:
        return singular if n == 1 else plural


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from types import ModuleType


__all__ = (
    "SHELL_COMPLETION",
    "AnsiHelpFormatter",
    "ArgumentDefaultsAnsiHelpFormatter",
    "PrettyHelpFormatter",
    "PrettyParser",
    "RawAnsiHelpFormatter",
    "RawDescriptionAnsiHelpFormatter",
)


SHELL_COMPLETION: Final[frozenset[str]] = frozenset(("bash", "zsh", "fish", "powershell"))
"""Supported shell names for **completion** feature of :class:`PrettyParser`.

This :class:`frozenset` includes 'bash', 'zsh', 'fish' and 'powershell'. Each entry
corresponds to a shell for which `argcomplete <https://github.com/kislyuk/argcomplete>`_
can generate an integration script.
"""


_S = TypeVar("_S", bound="AnsiHelpFormatter._Section")  # pyright:ignore[reportPrivateUsage]


class AnsiHelpFormatter(argparse.HelpFormatter):
    """An argparse.HelpFormatter with ansi markup text support."""

    styles: ClassVar[dict[str, str]] = {
        "argparse.args": ansi.style(ansi.Fg.LIGHT_CYAN),
        "argparse.groups": ansi.style(ansi.Fg.LIGHT_MAGENTA),
        "argparse.help": ansi.style(ansi.Mode.RESET_ALL),
        "argparse.metavar": ansi.style(ansi.Fg.YELLOW),
        "argparse.syntax": ansi.style(ansi.Mode.BRIGHT),
        "argparse.text": ansi.style(ansi.Mode.RESET_ALL),
        "argparse.prog": ansi.style(ansi.Fg.LIGHT_WHITE),
        "argparse.default": ansi.style(ansi.Mode.ITALIC),
    }
    """A dict of ansi styles to control the formatter.

    The following styles are used:

    - ``argparse.args``: for positional-arguments and --options (e.g "--help")
    - ``argparse.groups``: for group names (e.g. "positional arguments")
    - ``argparse.metavar``: for meta variables (e.g. "FILE" in "--file FILE")
    - ``argparse.prog``: for %(prog)s in the usage (e.g. "foo" in "Usage: foo [options]")
    - ``argparse.syntax``: for highlights of back-tick quoted text (e.g. "``` `some text` ```")
    - ``argparse.text``: for the descriptions and epilog (e.g. "A foo program")
    - ``argparse.default``: for %(default)s in the help (e.g. "Value" in "(default: Value)")
    """

    # highlights: ClassVar[list[str]] = [
    #     r"`(?P<syntax>[^`]*)`",  # highlight `text in backquotes` as syntax
    # ]
    # """A list of regex patterns to highlight in the help text.

    # It is used in the description, epilog, groups descriptions, and arguments' help.
    # By default, it highlights ``` `text in backquotes` ``` with the `argparse.syntax` style.
    # To disable highlighting, clear this list (``AnsiHelpFormatter.highlights.clear()``).
    # """

    @staticmethod
    def _ansi_style(text: str, style: str) -> str:
        return f"{AnsiHelpFormatter.styles[style]}{text}{ansi.style(ansi.Mode.RESET_ALL)}"

    @staticmethod
    def _ansi_aware_pad(text: str, width: int, char: str = " ") -> str:
        return text + char * (width - ansi.length(text))

    def _ansi_metavar_parts(  # noqa: PLR0912
        self, action: argparse.Action, default_metavar: str
    ) -> Iterator[tuple[str, bool]]:
        """A ansi aware substitute for self._format_args).

        Yields:
            (str, bool): as (part, colorize) of the metavar.
        """
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            # '%s' % get_metavar(1)
            yield "{}".format(*get_metavar(1)), True
        elif action.nargs == argparse.OPTIONAL:
            # '[%s]' % get_metavar(1)
            yield from (
                ("[", False),
                ("{}".format(*get_metavar(1)), True),
                ("]", False),
            )
        elif action.nargs == argparse.ZERO_OR_MORE:
            if sys.version_info < (3, 9) or len(get_metavar(1)) == 2:  # pragma: <3.9 cover
                metavar = get_metavar(2)
                # '[%s [%s ...]]' % metavar
                yield from (
                    ("[", False),
                    ("{}".format(*metavar[0]), True),
                    (" [", False),
                    ("{}".format(*metavar[1]), True),
                    (" ", False),
                    ("...", True),
                    ("]]", False),
                )
            else:  # pragma: >=3.9 cover
                # '[%s ...]' % metavar
                yield from (
                    ("[", False),
                    ("{}".format(*get_metavar(1)), True),
                    (" ", False),
                    ("...", True),
                    ("]", False),
                )
        elif action.nargs == argparse.ONE_OR_MORE:
            # '%s [%s ...]' % get_metavar(2)
            metavar = get_metavar(2)
            yield from (
                ("{}".format(*metavar[0]), True),
                (" [", False),
                ("{}".format(*metavar[1]), True),
                (" ", False),
                ("...", True),
                ("]", False),
            )
        elif action.nargs == argparse.REMAINDER:
            # '...'
            yield "...", True
        elif action.nargs == argparse.PARSER:
            # '%s ...' % get_metavar(1)
            yield from (
                ("{}".format(*get_metavar(1)), True),
                (" ", False),
                ("...", True),
            )
        elif action.nargs == argparse.SUPPRESS:
            # ''
            yield "", False
        else:
            metavar = get_metavar(action.nargs)  # pyright: ignore[reportArgumentType]
            first = True
            for met in metavar:
                if first:
                    first = False
                else:
                    yield " ", False
                yield (f"{met}", True)

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        text = self._whitespace_matcher.sub(" ", text).strip()
        return AnsiTextWrapper(
            width=width,
            initial_indent=indent,
            subsequent_indent=indent,
        ).fill(text)

    def _split_lines(self, text: str, width: int) -> list[str]:
        text = self._whitespace_matcher.sub(" ", text).strip()
        return AnsiTextWrapper(width=width).wrap(text)

    def _format_action(self, action: argparse.Action) -> str:
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        indent_first = 0

        if not action.help:
            # no help; start on same line and add a final newline
            action_header = f"{' ' * self._current_indent}{action_header}\n"
        elif ansi.length(action_header) <= action_width:
            # short action name; start on the same line and pad two spaces
            h_ = self._ansi_aware_pad(action_header, action_width)
            action_header = f"{' ' * self._current_indent}{h_}  "
            indent_first = 0
        else:
            # long action name; start on the next line
            action_header = f"{' ' * self._current_indent}{action_header}\n"
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        if action.help and action.help.strip():
            if help_text := self._expand_help(action):
                help_lines = self._split_lines(help_text, help_width)
                parts.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                parts.extend("%*s%s\n" % (help_position, "", line) for line in help_lines[1:])
        elif not action_header.endswith("\n"):  # pragma: no cover
            # seems to be dead branch
            parts.append("\n")

        # if there are any sub-actions, add their help as well
        parts.extend(
            self._format_action(subaction) for subaction in self._iter_indented_subactions(action)
        )
        # return a single string
        return self._join_parts(parts)

    def _format_usage(  # noqa: C901, PLR0912, PLR0915, PLR0914
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],  # pyright:ignore[reportPrivateUsage]
        prefix: str | None,
    ) -> str:
        if prefix is None:
            prefix = _("usage: ")
        prefix_len = ansi.length(prefix)

        # if usage is specified, use that
        if usage is not None:
            usage %= {"prog": self._prog}
        elif usage is None and not actions:
            usage = f"{self._prog}"
        elif usage is None:
            # XXX: this branch seems to be dead code
            prog = f"{self._prog}"
            # split optionals from positionals
            optionals: list[argparse.Action] = []
            positionals: list[argparse.Action] = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            @no_type_check
            def format_(
                actions: Iterable[argparse.Action],
                groups: Iterable[_MutuallyExclusiveGroup],
            ) -> str:
                # Python 3.14 removed _format_actions_usage in favor of
                # _get_actions_usage_parts which returns (parts, pos_start).
                if hasattr(self, "_get_actions_usage_parts"):  # pragma >=3.14 cover
                    parts, _pos_start = self._get_actions_usage_parts(actions, groups)
                    return " ".join(parts)
                return self._format_actions_usage(actions, groups)  # pragma <3.14 cover

            action_usage = format_(optionals + positionals, groups)
            usage = " ".join([s for s in [prog, action_usage] if s])

            text_width = self._width - self._current_indent
            if prefix_len + ansi.length(usage) > text_width:
                # wrap the usage parts if it's too long
                # break usage into wrappable parts
                part_regexp = r"\(.*?\)+(?=\s|$)|\[.*?\]+(?=\s|$)|\S+"
                opt_usage = format_(optionals, groups)
                pos_usage = format_(positionals, groups)
                opt_parts = re.findall(part_regexp, opt_usage)
                pos_parts = re.findall(part_regexp, pos_usage)
                if " ".join(opt_parts) != opt_usage or " ".join(pos_parts) != pos_usage:
                    raise AssertionError

                def get_lines(
                    parts: list[str], indent: str, prefix: str | None = None
                ) -> list[str]:
                    """Helper for wrapping lines."""  # noqa: DOC201
                    lines: list[str] = []
                    line: list[str] = []
                    indent_length = len(indent)
                    line_len = prefix_len - 1 if prefix is not None else indent_length - 1
                    for part in parts:
                        part_len = ansi.length(part)
                        if line_len + 1 + part_len > text_width and line:
                            lines.append(indent + " ".join(line))
                            line = []
                            line_len = indent_length - 1
                        line.append(part)
                        line_len += part_len + 1
                    if line:
                        lines.append(indent + " ".join(line))
                    if prefix is not None:
                        lines[0] = lines[0][indent_length:]
                    return lines

                len_prog = ansi.length(prog)
                if prefix_len + len_prog <= 0.75 * text_width:
                    # if prog is short, follow it with optionals or positionals
                    indent = " " * (prefix_len + len_prog + 1)
                    if opt_parts:
                        lines = get_lines([prog, *opt_parts], indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog, *pos_parts], indent, prefix)
                    else:  # pragma: no cover
                        lines = [prog]
                else:
                    # if prog is long, put it on its own line
                    indent = " " * prefix_len
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines: list[str] = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog, *lines]

                # join lines into usage
                usage = "\n".join(lines)

        # prefix with 'usage:'
        return f"{prefix}{usage}\n\n"

    def add_argument(self, action: argparse.Action) -> None:
        """Updates the action maximum length.

        Updates action and invocation length based on the provided action,
        taking into account ansi escape codes.

        Args:
            action: The action to be added.
        """
        old_max = self._action_max_length
        super().add_argument(action)
        # the self._action_max_length updated above
        # won't account for color codes,
        # so we need to update it here as well
        if action.help is not argparse.SUPPRESS:
            self._action_max_length: int = old_max
            invocations = [self._format_action_invocation(action)]
            invocations.extend(
                self._format_action_invocation(subaction)
                for subaction in self._iter_indented_subactions(action)
            )
            invocation_length = max(ansi.length(invocation) for invocation in invocations)
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length, action_length)

    def _format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings:
            return self._ansi_style(
                super()._format_action_invocation(action), style="argparse.args"
            )

        parts: list[str] = []
        if action.nargs == 0:
            # if the Optional doesn't take a value, format is: -s, --long
            parts.extend(self._ansi_style(o, "argparse.args") for o in action.option_strings)
        else:
            # if the Optional takes a value, format is: -s ARGS, --long ARGS
            default = self._get_default_metavar_for_optional(action)
            args = " ".join(
                self._ansi_style(part, "argparse.metavar") if colorize else part
                for part, colorize in self._ansi_metavar_parts(action, default)
            )
            parts.extend(
                f"{self._ansi_style(o, 'argparse.args')} {args}" for o in action.option_strings
            )
        return ", ".join(parts)

    class _Section:  # pyright:ignore[reportIncompatibleVariableOverride]
        def __init__(
            self: _S,
            formatter: argparse.HelpFormatter,
            parent: _S | None,
            heading: str | None = None,
        ) -> None:
            self.formatter: argparse.HelpFormatter = formatter
            self.parent: object | None = parent
            self.heading: str | None = heading
            self.items: list[tuple[Callable[..., str], Iterable[object]]] = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ""

            # add the heading if the section was non-empty
            if self.heading is not argparse.SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = AnsiHelpFormatter._ansi_style(self.heading, "argparse.groups")
                heading = "%*s%s:\n" % (current_indent, "", heading)
            else:
                heading = ""

            # join the section-initial newline, the heading and the help
            return join(["\n", heading, item_help, "\n"])

    def _get_default_metavar_for_optional(self, action: argparse.Action) -> str:
        return self._ansi_style(action.dest.upper(), "argparse.default")

    def _get_default_metavar_for_positional(self, action: argparse.Action) -> str:
        return self._ansi_style(action.dest, "argparse.default")

    def _expand_help(self, action: argparse.Action) -> str:
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is argparse.SUPPRESS:
                del params[name]
            elif hasattr(params[name], "__name__"):
                params[name] = params[name].__name__
        if params.get("choices") is not None:
            params["choices"] = ", ".join([str(c) for c in params["choices"]])

        if not (help_string := self._get_help_string(action)):
            raise ValueError

        return help_string % params


class RawAnsiHelpFormatter(argparse.RawTextHelpFormatter, AnsiHelpFormatter):
    """An argparse.RawTextHelpFormatter with ansi markup text support."""


class RawDescriptionAnsiHelpFormatter(argparse.RawDescriptionHelpFormatter, AnsiHelpFormatter):
    """An argparse.RawDescriptionHelpFormatter with ansi markup text support."""


class ArgumentDefaultsAnsiHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, AnsiHelpFormatter):
    """An argparse.ArgumentDefaultsHelpFormatter with ansi markup text support."""


class PrettyHelpFormatter(  # pyright:ignore[reportIncompatibleVariableOverride]
    argparse.RawDescriptionHelpFormatter,
    argparse.ArgumentDefaultsHelpFormatter,
    AnsiHelpFormatter,
):
    """AnsiHelpFormatter with combined raw description and argument defaults support.

    Combines the behaviours of :class:`~argparse.RawDescriptionHelpFormatter`
    and :class:`~argparse.ArgumentDefaultsHelpFormatter` with
    :class:`AnsiHelpFormatter`. Also implements the
    :class:`~argparse.MetavarTypeHelpFormatter` on demand via the
    ``metavar_typed`` class variable.

    Args:
        prog (:obj:`str`): The name of the program.
        indent_increment (:obj:`int`): The number of characters to indent
            each nesting level. Default: ``2``.
        max_help_position (:obj:`int`): The maximum starting column for
            help messages. Default: ``24``.
        width (:obj:`int` | ``None``): The total width of the help output.
            If ``None``, the width is determined by the terminal.
            Default: ``None``.
    """

    metavar_typed: ClassVar[bool] = False

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
    ) -> None:
        super().__init__(prog, indent_increment, max_help_position, width)

    def _get_default_metavar_for_optional(self, action: argparse.Action) -> str:
        if self.metavar_typed and hasattr(action, "type") and action.type:
            return self._ansi_style(cast("str", action.type.__name__), "argparse.default")  # pyright: ignore[reportAttributeAccessIssue]
        return super()._get_default_metavar_for_optional(action)

    def _get_default_metavar_for_positional(self, action: argparse.Action) -> str:
        if self.metavar_typed and hasattr(action, "type") and action.type:
            return self._ansi_style(cast("str", action.type.__name__), "argparse.default")  # pyright: ignore[reportAttributeAccessIssue]
        return super()._get_default_metavar_for_positional(action)

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],  # pyright:ignore[reportPrivateUsage]
        prefix: str | None,
    ) -> str:
        usage_: str = super()._format_usage(usage, actions, groups, None)
        return f"{prefix}\n\n{usage_}"


class _ShellCompletion(argparse.Action):
    def __init__(  # noqa: PLR0917
        self,
        option_strings: Sequence[str],
        dest: str,
        choices: Sequence[str] | None = None,
        default: str | None = None,
        help: str | None = None,  # noqa: A002
        metavar: str | None = None,
        **_kw: Any,
    ) -> None:
        super().__init__(
            option_strings,
            dest,
            metavar=metavar,
            help=help,
            choices=choices,
            default=default,
        )

    def __call__(  # pyright:ignore[reportIncompatibleMethodOverride]
        self,
        parser: PrettyParser,
        namespace: argparse.Namespace,  # noqa: ARG002
        values: str | Sequence[Any] | None,
        option_string: str | None = None,  # noqa: ARG002
    ) -> None:
        if values not in SHELL_COMPLETION:
            parser.error("option should specify a valid shell name")
        hook: str = cast(
            "str",
            parser.argcomplete.shell_integration.shellcode(
                executables=[parser.prog],
                use_defaults=False,  # bash only
                shell=values,
            ),
        )
        parser._print_message(message=hook, file=sys.stdout)  # pyright:ignore[reportPrivateUsage]
        parser.exit()


class PrettyParser(argparse.ArgumentParser):
    """Enhanced argument parser with ANSI output and shell completion support.

    Extends :class:`~argparse.ArgumentParser` to provide a richer command-line
    experience with colored and styled help output, automatic shell completion,
    and improved error handling for better library integration.

    Color Support
    _____________

    This class lets you embed ANSI escape codes directly in help text,
    descriptions, and usage strings without breaking layout calculations.
    The default :class:`PrettyHelpFormatter` takes care of proper padding
    and wrapping of ANSI-formatted text. It also combines the behaviors
    of :class:`~argparse.RawDescriptionHelpFormatter` and
    :class:`~argparse.ArgumentDefaultsHelpFormatter`, so you get both raw
    description preservation and automatic default display out of the box.

    Two independent colouring mechanisms coexist and do not conflict:

    1. **Deluxe ANSI styles** (:attr:`AnsiHelpFormatter.styles`): the
       default :class:`PrettyHelpFormatter` embeds ANSI escape codes
       directly into help text, descriptions, and usage strings via the
       :meth:`AnsiHelpFormatter._ansi_style` helper.  The style palette
       is controlled through the :attr:`AnsiHelpFormatter.styles` class
       dictionary (see :class:`AnsiHelpFormatter` for the full list of
       keys).  This mechanism is always active regardless of the
       ``color`` parameter.

    2. **Python 3.14+ stdlib colour** (``color`` parameter): starting
       with Python 3.14, the standard library gained built-in colour
       support through the ``color`` keyword on
       :class:`~argparse.ArgumentParser` and
       :class:`~argparse.HelpFormatter`.  The stdlib uses the
       ``_colorize`` module to query terminal capabilities and applies
       its own theme (``self._theme``) to the *usage line* only (via
       :meth:`~argparse.HelpFormatter._get_actions_usage_parts`).  This
       is completely separate from the deluxe ``styles`` dictionary and
       does not alter how descriptions, group headings, or argument help
       are coloured.  On Python versions prior to 3.14 the ``color``
       parameter is accepted but silently ignored.

    The two systems are orthogonal: deluxe styles always emit ANSI codes
    for the full help output, while the stdlib ``color`` flag controls
    terminal-aware colour in the usage line on Python 3.14+.  Setting
    ``color=False`` disables only the stdlib portion; deluxe styles
    remain active and can be customized through :attr:`AnsiHelpFormatter.styles`.

    Errors Handling
    _______________

    When ``exit_on_error`` is ``True`` (the default), argument errors raise
    :exc:`~argparse.ArgumentError` instead of calling ``sys.exit()``. This
    makes the parser suitable for library use where errors should be caught
    and handled programmatically rather than terminating the host application.
    If you set ``exit_on_error`` to ``False``, the parser falls back to the
    standard behaviour of printing an error message and exiting the process.
    You can also override the :meth:`error` method to implement fully custom
    error handling logic.

    Setting Version
    _______________

    A ``-v``/``--version`` option is added automatically when a ``version``
    string is provided to the constructor. Running the program with this
    option prints the program name followed by the version string and exits.

    Prefix
    ______

    The default ``"usage: "`` prefix that appears at the beginning of the
    usage line can be replaced with any custom string through the ``prefix``
    parameter, which is useful for programmes that need a different label
    in their usage output.

    Shell Completion
    ________________

    Optional shell completion is available through `argcomplete
    <https://github.com/kislyuk/argcomplete>`_ for bash, zsh, fish, and
    powershell. When enabled with ``shell_completion=True``, a hidden
    ``--completion`` option is registered. Invoking the program with
    ``--completion SHELL`` (where *SHELL* is one of ``bash``, ``zsh``,
    ``fish``, or ``powershell``) prints the corresponding shell integration
    script to stdout and exits. The ``argcomplete`` package must be
    installed; if it is not found, an :exc:`ImportWarning` is emitted
    and shell completion is silently disabled for the rest of the session.


    For full documentation of the base parser API, see
    :class:`~argparse.ArgumentParser`.

    Args:
        prog (:obj:`str`): The name of the program (used in usage messages).
        version (:obj:`str` | ``None``): If provided, a ``-v``/``--version``
            option is added automatically. Default: ``None``.
        description (:obj:`str` | ``None``): Text to display before the
            argument help. Default: ``None``.
        usage (:obj:`str` | ``None``): Custom usage string. If ``None``,
            it is generated from the added arguments. Default: ``None``.
        prefix (:obj:`str` | ``None``): Custom prefix for the usage message
            (replaces the default ``"usage: "``). Default: ``None``.
        epilog (:obj:`str` | ``None``): Text to display after the
            argument help. Default: ``None``.
        parents (:obj:`Sequence` [:class:`~argparse.ArgumentParser`] | ``None``):
            A list of :class:`~argparse.ArgumentParser` objects whose
            arguments will be added to this parser. Default: ``None``.
        formatter_class (:obj:`type` [:class:`~argparse.HelpFormatter`]):
            A class for customizing the help output. Defaults to
            :class:`PrettyHelpFormatter`.
        prefix_chars (:obj:`str`): The set of characters that prefix
            optional arguments. Default: ``"-"``.
        fromfile_prefix_chars (:obj:`str` | ``None``): The set of characters
            that prefix files from which additional arguments are read.
            Default: ``None``.
        argument_default (:obj:`object`): The default value for all
            arguments. Default: ``None``.
        conflict_handler (:obj:`str`): Determines how conflicts between
            existing and added arguments are handled (``"error"`` or
            ``"resolve"``). Default: ``"error"``.
        add_help (:obj:`bool`): If ``True``, a ``-h``/``--help`` option
            is added. Default: ``True``.
        allow_abbrev (:obj:`bool`): If ``True``, allow long options to
            be abbreviated uniquely. Default: ``True``.
        exit_on_error (:obj:`bool`): If ``True``, raises
            :exc:`~argparse.ArgumentError` on errors instead of calling
            :func:`sys.exit`. Default: ``True``.
        shell_completion (:obj:`bool`): If ``True``, attempts to enable
            shell auto-completion via ``argcomplete``. A ``--completion``
            option is added. If ``argcomplete`` is not installed, a
            warning is emitted and completion is disabled.
            Default: ``False``.
        color (:obj:`bool`): If ``True``, allow color output in help
            messages.  Forwarded to the base parser on Python 3.14+;
            ignored on older versions where the stdlib does not support
            this parameter. Default: ``True``.
        suggest_on_error (:obj:`bool`): If ``True``, suggest closest
            matches when a subcommand or argument is mistyped.
            Forwarded to the base parser on Python 3.14+; ignored on
            older versions where the stdlib does not support this
            parameter. Default: ``False``.

    Attributes:
        exit_on_error: Whether to raise :exc:`~argparse.ArgumentError` on errors.
        prefix: Custom prefix for usage messages.
        version: Version string for the ``--version`` option.
        shell_completion: Whether shell completion support is enabled.

    .. warning::
        When ``shell_completion=True`` and ``argcomplete`` is not installed,
        an :exc:`ImportWarning` is emitted and shell completion is
        silently disabled.
    """

    def __init__(  # noqa: PLR0917
        self,
        prog: str,
        version: str | None = None,
        description: str | None = None,
        usage: str | None = None,
        prefix: str | None = None,
        epilog: str | None = None,
        parents: Sequence[argparse.ArgumentParser] | None = None,
        formatter_class: type[argparse.HelpFormatter] = PrettyHelpFormatter,
        prefix_chars: str = "-",
        fromfile_prefix_chars: str | None = None,
        argument_default: object = None,
        conflict_handler: str = "error",
        add_help: bool = True,
        allow_abbrev: bool = True,
        exit_on_error: bool = True,
        shell_completion: bool = False,
        color: bool = True,
        suggest_on_error: bool = False,
        **_extra: Any,
    ) -> None:
        if parents is None:
            parents = []

        # Forward version-specific kwargs to the base parser.
        # Python 3.14+ added 'color' and 'suggest_on_error' to
        # ArgumentParser.__init__; earlier versions do not accept them.
        base_kwargs: dict[str, Any] = {
            "prog": prog,
            "usage": usage,
            "description": description,
            "epilog": epilog,
            "parents": parents,
            "formatter_class": formatter_class,
            "prefix_chars": prefix_chars,
            "fromfile_prefix_chars": fromfile_prefix_chars,
            "argument_default": argument_default,
            "conflict_handler": conflict_handler,
            "add_help": add_help,
            "allow_abbrev": allow_abbrev,
            "exit_on_error": exit_on_error,
        }
        if (sys.version_info.major, sys.version_info.minor) >= (3, 14):  # pragma: >=3.14 cover
            base_kwargs["color"] = color
            base_kwargs["suggest_on_error"] = suggest_on_error
        base_kwargs.update(_extra)

        super().__init__(**base_kwargs)
        self.exit_on_error: bool = exit_on_error
        self.prefix: str = prefix or ""
        self.version: str = version or ""
        self.shell_completion: bool = shell_completion

        if self.version:
            self.add_argument(
                "-v",
                "--version",
                action="version",
                version=f"{self.prog} {self.version}",
                default=argparse.SUPPRESS,
                help="print version",
            )

        if self.shell_completion:
            try:
                argcomplete = self._find_argcomplete()
            except ImportError:
                self.shell_completion = False
                warnings.warn(
                    "auto-completion requested but argcomplete was not found.",
                    category=ImportWarning,
                    stacklevel=1,
                )
            else:
                self.argcomplete: ModuleType = argcomplete
                self.add_argument(
                    "--completion",
                    dest="shell_compl",
                    metavar="SHELL",
                    action=_ShellCompletion,
                    choices=SHELL_COMPLETION,
                    default=argparse.SUPPRESS,
                    help=f"Generate completion scripts for the given shell {SHELL_COMPLETION}",
                )

    @staticmethod
    def _find_argcomplete() -> ModuleType:
        if importlib.util.find_spec(name="argcomplete"):
            return importlib.import_module(name="argcomplete")
        raise ImportError

    def _autocomplete(self) -> None:
        """Activate support for shell completion.

        Adds support for shell completion via argcomplete
        if found on the path.
        """
        # NOTE: https://github.com/kislyuk/argcomplete/tree/develop/contrib
        self.argcomplete.autocomplete(self)

    def parse_args(  # pyright:ignore[reportIncompatibleMethodOverride]
        self, args: Sequence[str] | None = None, namespace: argparse.Namespace | None = None
    ) -> argparse.Namespace | None:
        """Parse command line arguments.

        Args:
            args (Sequence[str], optional): The command line arguments to parse.
                Defaults to None.
            namespace (argparse.Namespace, optional): An optional namespace
                object to populate with the parsed arguments. Defaults to None.

        Returns:
            argparse.Namespace or None: The parsed command line arguments
            as a namespace object, or None if no arguments were provided.
        """
        if self.shell_completion:
            self._autocomplete()
        return super().parse_args(args, namespace)

    def format_usage(self) -> str:
        """Ask HelpFormatter to format the usage string.

        Returns:
            str: The formatted usage string.
        """
        formatter = self._get_formatter()
        formatter.add_usage(
            usage=self.usage,
            actions=self._actions,
            groups=self._mutually_exclusive_groups,
            prefix=self.prefix,
        )
        return formatter.format_help()

    def format_help(self) -> str:
        """Ask HelpFormatter to format the help string.

        Returns:
            str: The formatted help string.
        """
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(
            usage=self.usage,
            actions=self._actions,
            groups=self._mutually_exclusive_groups,
            prefix=self.prefix,
        )

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def exit(  # pyright:ignore[reportIncompatibleMethodOverride]  # noqa: PLR6301
        self, status: int = 0, message: str | None = None
    ) -> None:
        """Either raise an ArgumentError or a SystemExit exception.

        Args:
            status (int, optional): The exit status. Defaults to 0.
            message (str, optional): The error message. Defaults to None.

        Raises:
            argparse.ArgumentError: with the specified `message` or a default
                "unknown error" message If the `status` argument is non-zero.
            SystemExit: with the specified `message` otherwise
        """
        if status:
            raise argparse.ArgumentError(None, message or "unknown error")
        raise SystemExit(message)

    def error(  # pyright:ignore[reportIncompatibleMethodOverride] # dead: disable
        self, message: str
    ) -> None:
        """Prints a usage message.

        Prints a usage message incorporating the message to stderr
        and exits. If you override this in a subclass, it should
        not return -- it should either exit or raise an exception.

        Args:
            message (str): The error message to be incorporated into
            the usage message.

        Raises:
            argparse.ArgumentError: If the `exit_on_error` flag is set
                to `True`, an `argparse.ArgumentError` is raised.
        """
        self.print_usage()
        if self.exit_on_error:
            args = {"message": message}
            self.exit(2, _("error: %(message)s\n") % args)
        raise argparse.ArgumentError(None, message)

    def print_usage(self, file: IO[str] | None = None) -> None:
        """Prints the usage message."""
        if file is None:
            file = sys.stderr
        self._print_message(self.format_usage(), file)

    def print_help(self, file: IO[str] | None = None) -> None:  # dead: disable
        """Prints the help message."""
        if file is None:
            file = sys.stderr
        self._print_message(self.format_help(), file)

    def _print_message(  # noqa: PLR6301
        self, message: str, file: IO[str] | None = None
    ) -> None:
        if message:
            file_ = sys.stderr if file is None else file
            file_.write(message)
