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
import sys
import warnings
from typing import IO, TYPE_CHECKING, Any, cast


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


class PrettyHelpFormatter(  # pyright:ignore[reportUnsafeMultipleInheritance]
    argparse.RawDescriptionHelpFormatter,
    argparse.ArgumentDefaultsHelpFormatter,
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

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],  # pyright:ignore[reportPrivateUsage]
        prefix: str | None,
    ) -> str:
        _usage: str = super()._format_usage(usage, actions, groups, None)
        return f"{prefix}\n\n{_usage}"

    def _get_default_metavar_for_optional(self, action: argparse.Action) -> str:
        if self.metavar_typed and hasattr(action, "type") and action.type:
            return action.type.__name__  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]
        return super()._get_default_metavar_for_optional(action)

    def _get_default_metavar_for_positional(self, action: argparse.Action) -> str:
        if self.metavar_typed and hasattr(action, "type") and action.type:
            return action.type.__name__  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]
        return super()._get_default_metavar_for_positional(action)


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

    def exit(  # pyright:ignore[reportIncompatibleMethodOverride]  # noqa: PLR6301
        self,
        status: int = 0,
        message: str | None = None,
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
        self,
        message: str,
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
        self,
        message: str,
        file: IO[str] | None = None,
    ) -> None:
        if message:
            _file = sys.stderr if file is None else file
            _file.write(message)
