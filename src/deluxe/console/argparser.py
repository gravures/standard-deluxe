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
"""Argument parser module."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import warnings
from typing import IO, TYPE_CHECKING, Any, ClassVar, cast

from deluxe.console import ansi
from deluxe.console.wrap import AnsiTextWrapper


try:
    from gettext import gettext as _
    from gettext import ngettext  # pyright:ignore[reportUnusedImport, reportAssignmentType]
except ImportError:

    def _(message: str) -> str:
        return message

    def ngettext(singular: Any, plural: Any, n: int) -> Any:  # noqa: D103
        return singular if n == 1 else plural


if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from types import ModuleType


SHELL_COMPLETION = {"bash", "zsh", "fish", "powershell"}


class AnsiHelpFormatter(argparse.HelpFormatter):
    @staticmethod
    def _ansi_aware_pad(text: str, width: int, char: str = " ") -> str:
        return text + char * (width - ansi.length(text))

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

    def _format_args(self, action: argparse.Action, default_metavar: str) -> str:
        result = super()._format_args(action, default_metavar)
        if action.nargs == argparse.ZERO_OR_MORE:
            metavar = self._metavar_formatter(action, default_metavar)(1)
            if len(metavar) == 2:
                result = f"[{ansi.strip(metavar[0])} [{ansi.strip(metavar[1])} ...]]"
            else:
                result = f"[{ansi.strip(metavar[0])} ...]"
        return result

    def _format_action(self, action: argparse.Action) -> str:
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        indent_first: int = -1

        if not action.help:
            # no help; start on same line and add a final newline
            tup = self._current_indent, "", action_header
            action_header = "%*s%s\n" % tup
        elif ansi.length(action_header) <= action_width:
            # short action name; start on the same line and pad two spaces
            tup = self._current_indent, "", self._ansi_aware_pad(action_header, action_width)
            action_header = "%*s%s  " % tup
            indent_first = 0
        else:
            # long action name; start on the next line
            tup = self._current_indent, "", action_header
            action_header = "%*s%s\n" % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        if action.help and action.help.strip():
            # if there was help for the action, add lines of help text
            if help_text := self._expand_help(action):
                help_lines = self._split_lines(help_text, help_width)
                parts.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                parts.extend("%*s%s\n" % (help_position, "", line) for line in help_lines[1:])
        elif not action_header.endswith("\n"):
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
            _format = self._format_actions_usage
            action_usage = _format(optionals + positionals, groups)
            usage = " ".join([s for s in [prog, action_usage] if s])

            text_width = self._width - self._current_indent
            if prefix_len + ansi.length(usage) > text_width:
                # wrap the usage parts if it's too long
                # break usage into wrappable parts
                part_regexp = r"\(.*?\)+(?=\s|$)|\[.*?\]+(?=\s|$)|\S+"
                opt_usage = _format(optionals, groups)
                pos_usage = _format(positionals, groups)
                opt_parts = re.findall(part_regexp, opt_usage)
                pos_parts = re.findall(part_regexp, pos_usage)
                if " ".join(opt_parts) != opt_usage or " ".join(pos_parts) != pos_usage:
                    raise AssertionError

                def get_lines(
                    parts: list[str], indent: str, prefix: str | None = None
                ) -> list[str]:
                    """Helper for wrapping lines."""
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
                    return lines  # noqa: DOC201

                len_prog = ansi.length(prog)
                if prefix_len + len_prog <= 0.75 * text_width:
                    # if prog is short, follow it with optionals or positionals
                    indent = " " * (prefix_len + len_prog + 1)
                    if opt_parts:
                        lines = get_lines([prog, *opt_parts], indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog, *pos_parts], indent, prefix)
                    else:
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
        old_max = self._action_max_length
        super().add_argument(action)
        # the self._action_max_length updated above
        # won't account for color codes,
        # so we need to update it here as well
        if action.help is not argparse.SUPPRESS:
            self._action_max_length = old_max
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            invocations.extend(
                get_invocation(subaction) for subaction in self._iter_indented_subactions(action)
            )
            invocation_length = max(ansi.length(invocation) for invocation in invocations)
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length, action_length)


class ColorsHelpFormatter(AnsiHelpFormatter):
    styles: ClassVar[dict[str, str]] = {
        "argparse.args": ansi.style(ansi.FG.CYAN),
        "argparse.groups": ansi.style(ansi.FG.LIGHT_MAGENTA),
        "argparse.help": ansi.style(ansi.MOD.RESET_ALL),
        "argparse.metavar": ansi.style(ansi.FG.CYAN),
        "argparse.syntax": ansi.style(ansi.MOD.BRIGHT),
        "argparse.text": ansi.style(ansi.MOD.RESET_ALL),
        "argparse.prog": ansi.style(ansi.FG.LIGHT_WHITE),
        "argparse.default": ansi.style(ansi.MOD.ITALIC),
    }

    def _style(self, text: str, style: str) -> str:
        return f"{self.styles[style]}{text}{ansi.style(ansi.MOD.RESET_ALL)}"

    def format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings:
            return self._style(self._format_action_invocation(action), style="argparse.args")
        parts: list[str] = []
        if action.nargs == 0:
            # if the Optional doesn't take a value, format is: -s, --long
            parts.extend(self._style(o, "argparse.args") for o in action.option_strings)
        else:
            # if the Optional takes a value, format is: -s ARGS, --long ARGS
            default = self._get_default_metavar_for_optional(action)
            args = self._format_args(action, default)
            parts.extend(
                f"{self._style(o, 'argparse.args')} {args}" for o in action.option_strings
            )
        return ", ".join(parts)

        # action_header = ", ".join(
        #     self._style(o, "argparse.args") for o in action.option_strings
        # )
        # if action.nargs != 0:
        #     default = self._get_default_metavar_for_optional(action)
        #     action_header.append(" ")
        #     for metavar_part, colorize in self._rich_metavar_parts(action, default):
        #         style = "argparse.metavar" if colorize else None
        #         action_header.append(metavar_part, style=style)
        # return action_header


class PrettyHelpFormatter(  # pyright:ignore[reportUnsafeMultipleInheritance]
    argparse.RawDescriptionHelpFormatter,
    argparse.ArgumentDefaultsHelpFormatter,
    ColorsHelpFormatter,
):
    """HelpFormatter."""

    # NOTE:  https://github.com/hamdanal/rich-argparse

    def __init__(
        self,
        prog: str,
        metavar_typed: bool = False,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
    ) -> None:
        super().__init__(prog, indent_increment, max_help_position, width)
        self.metavar_typed = metavar_typed

    def _get_default_metavar_for_optional(self, action: argparse.Action) -> str:
        if self.metavar_typed and hasattr(action, "type") and action.type:
            return action.type.__name__  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]
        return super()._get_default_metavar_for_optional(action)

    def _get_default_metavar_for_positional(self, action: argparse.Action) -> str:
        if self.metavar_typed and hasattr(action, "type") and action.type:
            return action.type.__name__  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]
        return super()._get_default_metavar_for_positional(action)

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],  # pyright:ignore[reportPrivateUsage]
        prefix: str | None,
    ) -> str:
        _usage: str = super()._format_usage(usage, actions, groups, None)
        return f"{prefix}\n\n{_usage}"


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
            str,
            parser.argcomplete.shell_integration.shellcode(
                executables=[parser.prog],
                use_defaults=False,  # bash only
                shell=values,
            ),
        )
        parser._print_message(message=hook, file=sys.stdout)  # pyright:ignore[reportPrivateUsage]
        parser.exit()


class PrettyParser(argparse.ArgumentParser):
    """Class for parsing command line strings into Python objects.

    Overrides argparse print_usage(), print_help(), and error() methods to allow
    for explicit control over the format of a calling utility's description
    and usage strings.

    However, the description and usage_str fields are required.
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
        formatter_class: argparse._FormatterClass = PrettyHelpFormatter,  # pyright:ignore[reportPrivateUsage]
        prefix_chars: str = "-",
        fromfile_prefix_chars: str | None = None,
        argument_default: Any = None,
        conflict_handler: str = "error",
        add_help: bool = True,
        allow_abbrev: bool = True,
        exit_on_error: bool = True,
        shell_completion: bool = False,
    ) -> None:
        if parents is None:
            parents = []

        super().__init__(
            prog=prog,
            usage=usage,
            description=description,
            epilog=epilog,
            parents=parents,
            formatter_class=formatter_class,
            prefix_chars=prefix_chars,
            fromfile_prefix_chars=fromfile_prefix_chars,
            argument_default=argument_default,
            conflict_handler=conflict_handler,
            add_help=add_help,
            allow_abbrev=allow_abbrev,
            exit_on_error=exit_on_error,
        )
        self.exit_on_error: bool = exit_on_error
        self.prefix: str = prefix or ""
        self.version: str = version or ""
        self.shell_completion = shell_completion

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
                self.argcomplete = argcomplete
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

    # def format_help(self, command: Command = None):
    #     formatter = self._get_formatter()
    #     colorize = (Fore.YELLOW + "{}" + Fore.RESET).format

    #     if self.usage:
    #         formatter.add_usage(
    #             usage=self.usage,
    #             actions=self._actions,
    #             groups=self._mutually_exclusive_groups,
    #             prefix=colorize(self.prefixes["usage"]),
    #         )

    #     if command and not command.match and not command.group:
    #         msg = "{}ERROR:{} command not found"
    #         formatter.add_text(msg.format(Fore.RED, Fore.RESET))

    #     if self.description:
    #         formatter.add_text(colorize(self.prefixes["description"]) + self.description)
    #     if self.url:
    #         formatter.add_text(colorize(self.prefixes["url"]) + self.url)

    #     for action_group in self._action_groups:
    #         title = action_group.title or ""
    #         formatter.start_section(colorize(title.upper()))
    #         formatter.add_text(action_group.description)
    #         formatter.add_arguments(action_group._group_actions)
    #         formatter.end_section()
    #     self._format_commands(formatter=formatter, command=command)
    #     if self.epilog:
    #         formatter.add_text(colorize(self.prefixes["epilog"]) + self.epilog)
    #     return formatter.format_help()

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
            _file = sys.stderr if file is None else file
            _file.write(message)
