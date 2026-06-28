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
"""Command-line interface application framework.

This module provides the :class:`Cli` abstract base class for building
structured command-line applications with subcommand support. It wraps
Python's :mod:`argparse` module, adding pretty-printed help output with
ANSI markup, shell completion, and a clean lifecycle
(``configure`` → ``parse`` → ``main`` → ``cleanup``).

Subclass :class:`Cli` and implement the abstract methods to define
your CLI application. Subcommands can be registered imperatively via
:meth:`Cli.add_command` in :meth:`~Cli.configure`, or declaratively
via the :func:`command` decorator on methods.
"""

from __future__ import annotations

import argparse
import fileinput
import functools
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar, TypeVar, final

from deluxe.console.argparser import PrettyParser


if TYPE_CHECKING:
    from collections.abc import Sequence


__all__ = ("Cli", "CliError", "command")


class CliError(Exception):
    """Exception for CLI errors.

    Args:
        msg (str | None): The error message.
        quiet (bool): Whether to suppress error output.

    Attributes:
        msg (str): The error message.
        quiet (bool): Whether to suppress error output.
    """

    _error_codes: ClassVar[list[type[BaseException | None]]] = [
        SystemExit,
        Exception,
    ]

    def __init__(self, msg: str | None, quiet: bool) -> None:
        self.msg: str = msg or ""
        self.quiet: bool = quiet
        super().__init__()

    @property
    def code(self) -> int:
        """The exit code derived from the chained cause.

        Computes the code lazily so that ``__cause__`` (set by
        ``raise ... from ...``) is available at access time.
        """
        if isinstance(self.__cause__, OSError):
            return getattr(self.__cause__, "winerror", self.__cause__.errno) or 1
        return self.get_code(type(self.__cause__))

    @classmethod
    def get_code(cls, exce: type[BaseException | None]) -> int:
        """Map an exception type to an integer exit code.

        Args:
            exce (:obj:`type` [ :class:`BaseException` ] | ``None``): The exception type.

        Returns:
            :obj:`int`: The corresponding exit code, or ``1`` if unregistered.
        """
        try:
            return cls._error_codes.index(exce)
        except ValueError:
            return 1

    @classmethod
    def register(cls, *exce: type[Exception]) -> None:
        """Register exception types for exit code mapping.

        Registered exceptions are assigned sequential codes starting from
        ``len(_error_codes)``. This allows custom exceptions to produce
        distinct exit codes.

        Args:
            *exce (:obj:`type` [ :class:`Exception` ]): Exception types to register.
        """
        for e in exce:
            if e not in cls._error_codes:
                cls._error_codes.append(e)


_C = TypeVar("_C", bound="Cli")
_F = Callable[[_C], None]


def command(
    help: str,  # noqa: A002
    description: str | None = None,
    name: str | None = None,
    parents: list[PrettyParser] | None = None,
    setup: Callable[[PrettyParser], None] | None = None,
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """Decorator to register a method as a CLI subcommand.

    The decorated method becomes the callback invoked when the
    subcommand is selected. It receives the parsed
    :class:`argparse.Namespace`.

    Arguments can be added to the subparser in two ways:

    1. **Inline** via the ``setup`` callable, which receives the
       subparser during registration.
    2. **In ``configure()``** via ``self.parser_for(name)``.

    Args:
        help: Short help text shown in the parent parser.
        description: Long description. Defaults to ``help``.
        name: Subcommand name. Defaults to the method name.
        parents: Parent parsers to inherit arguments from.
        setup: Optional callable that receives the subparser for
            inline argument configuration.

    Returns:
        The decorated method with ``_cli_command`` metadata attached.
    """

    def decorator(func: Callable[..., None]) -> Callable[..., None]:

        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> None:
            return func(*args, **kwargs)

        wrapper._cli_command = {  # pyright: ignore[reportAttributeAccessIssue]
            "help": help,
            "description": description,
            "name": name,
            "parents": parents,
            "setup": setup,
        }
        return wrapper

    return decorator


class Cli(ABC):
    """Abstract base class for command-line interface applications.

    Subclass this to build a CLI tool. The lifecycle is:

    1. ``__init__`` — configure parser with program metadata.
    2. :meth:`configure` — add arguments and subcommands to the parser.
    3. :meth:`main` — execute the application logic after parsing.
    4. :meth:`cleanup` — release resources, always called (even on error).

    Call the instance (``cli()``) to run the full lifecycle.

    Subcommands can be registered in two ways:

    - **Imperative**: call :meth:`add_command` in :meth:`configure`.
    - **Declarative**: decorate a method with :func:`command`. The
      decorated method becomes the callback, and a subparser is created
      automatically before :meth:`configure` is called. Use
      :meth:`parser_for` in :meth:`configure` to add arguments to it.

    Usages
    ______

    **Simple CLI** without subcommands::

        __version__ = "1.0"

        CliError.register(
            ValueError,
        )

        class Greet(Cli):
            def __init__(self) -> None:
                super().__init__(
                    prog="greet",
                    version=__version__,
                    prefix=True,
                )

            def configure(self, parser):
                parser.add_argument("name", help="Your name")
                parser.add_argument(
                    "-q",
                    "--quiet",
                    dest="quiet",
                    action="store_true",
                    help="don't print any message to stderr",
                )

            def verify_name(self, name):
                if name == "cheese":
                    raise ValueError()

            def main(self, namespace):
                try:
                    self.verify_name(namespace.name)
                except ValueError as err:
                    raise CliError(
                        msg=f"can't greet a {namespace.name}",
                        quiet=namespace.quiet,
                        ) from err
                print(f"Hello, {namespace.name}!")

            def cleanup(self, namespace):
                # clean any resources
                pass

        if __name__ == "__main__":
            cli = Greet()
            sys.exit(cli())


    **Inline setup** — configure the subparser directly in the
    decorator via ``setup``::

        class MyApp(Cli):
            @command(
                help="Greet someone",
                setup=lambda p: p.add_argument("name", help="Your name"),
            )
            def greet(self, namespace):
                print(f"Hello, {namespace.name}!")

            def configure(self, parser):
                pass  # all setup is inline

            def main(self, namespace):
                pass

            def cleanup(self, namespace):
                pass

    **Setup in configure()** — use :meth:`parser_for` to add
    arguments in :meth:`configure`::

        class MyApp(Cli):
            @command(help="Greet someone")
            def greet(self, namespace):
                print(f"Hello, {namespace.name}!")

            def configure(self, parser):
                sub = self.parser_for("greet")
                sub.add_argument("name", help="Your name")
                sub.add_argument(
                    "-l", "--loud",
                    action="store_true",
                    help="Shout the greeting",
                )

            def main(self, namespace):
                pass

            def cleanup(self, namespace):
                pass

    **Mixed** — ``@command`` methods coexist with imperative
    ``add_command`` calls::

        class MyApp(Cli):
            @command(help="Show version")
            def version(self, namespace):
                print("1.0")

            def configure(self, parser):
                pass  # @command methods already registered

                # Also register a non-decorated subcommand:
                sub = self.add_command(callback=self._legacy_cmd, help="Legacy")
                sub.add_argument("arg")

            def _legacy_cmd(self, namespace):
                print(namespace.arg)

            def main(self, namespace):
                pass

            def cleanup(self, namespace):
                pass

    **Inheritance** — commands are inherited from parent classes.
    A subclass can override a parent's command by redefining the
    method::

        class BaseCli(Cli):
            @command(help="Show version")
            def version(self, namespace):
                print("1.0")

            def main(self, namespace):
                pass

            def cleanup(self, namespace):
                pass

        class MyApp(BaseCli):
            @command(help="Greet someone")
            def greet(self, namespace):
                print(f"Hello, {namespace.name}!")

            def configure(self, parser):
                self.parser_for("greet").add_argument("name")

            def main(self, namespace):
                pass

            def cleanup(self, namespace):
                pass
    """

    _cli_commands: ClassVar[dict[str, Callable[..., object]]] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        commands: dict[str, Callable[..., object]] = {}
        for base in reversed(cls.__mro__):
            if base is cls:
                continue
            base_cmds = getattr(base, "_cli_commands", None)
            if base_cmds is not None:
                commands.update(base_cmds)
        for attr_name in vars(cls):
            attr = getattr(cls, attr_name, None)
            if attr is not None and callable(attr) and hasattr(attr, "_cli_command"):
                commands[attr_name] = attr
        cls._cli_commands = commands

    def __init__(  # noqa: PLR0917
        self,
        prog: str | None = None,
        version: str | None = None,
        description: str | None = None,
        usage: str | None = None,
        epilog: str | None = None,
        prefix: bool = True,
        prefix_chars: str = "-",
        fromfile_prefix_chars: str | None = None,
        add_help: bool = True,
        argument_default: object = None,
        conflict_handler: str = "error",
        allow_abbrev: bool = True,
        shell_completion: bool = False,
    ) -> None:
        self._name: str = prog or sys.argv[0]
        self._prefix: str | None = f"{prog} {version}" if prefix else None
        self._parser: PrettyParser = PrettyParser(
            prog=self._name,
            version=version,
            description=description,
            usage=usage,
            epilog=epilog,
            prefix=self._prefix,
            prefix_chars=prefix_chars,
            fromfile_prefix_chars=fromfile_prefix_chars,
            add_help=add_help,
            argument_default=argument_default,
            conflict_handler=conflict_handler,
            allow_abbrev=allow_abbrev,
            exit_on_error=False,
            shell_completion=shell_completion,
        )
        self._namespace: argparse.Namespace = argparse.Namespace()
        self._commands: argparse._SubParsersAction[PrettyParser] | None = None  # pyright: ignore[reportPrivateUsage]
        self._command_parsers: dict[str, PrettyParser] = {}
        self._commands_registered: bool = False

    @property
    def parser(self) -> PrettyParser:
        """The underlying :class:`~deluxe.console.argparser.PrettyParser` instance."""
        return self._parser

    @property
    def commands(self) -> argparse._SubParsersAction[PrettyParser] | None:  # pyright: ignore[reportPrivateUsage]
        """The subcommands action group for registering subcommands.

        Lazily initialized on first access. No subparser positional argument
        is added to the parser until a subcommand is actually registered.
        """
        return self._commands

    @property
    def namespace(self):
        """The :class:`argparse.Namespace` populated after argument parsing."""
        return self._namespace

    def parser_for(self, name: str) -> PrettyParser:
        """Return the subparser for a named command.

        Use this in :meth:`configure` to add arguments to a
        subcommand that was registered via :func:`command`.

        Args:
            name: The subcommand name.

        Returns:
            The :class:`PrettyParser` for that subcommand.
        """
        return self._command_parsers[name]

    def _auto_register_commands(self) -> None:
        if self._commands_registered:
            return
        self._commands_registered = True
        for method_name, method in self._cli_commands.items():
            config = method._cli_command  # pyright: ignore[reportFunctionMemberAccess]
            cmd_name = config["name"] or method_name
            sub = self.add_command(
                callback=getattr(self, method_name),  # type: ignore[arg-type]
                help=config["help"],
                description=config["description"] or config["help"],
                name=cmd_name,
                parents=config["parents"],
            )
            self._command_parsers[cmd_name] = sub
            if config["setup"] is not None:
                config["setup"](sub)

    @abstractmethod
    def configure(self, parser: PrettyParser) -> None:
        """Configure the argument parser with arguments and subcommands.

        Args:
            parser (:class:`~deluxe.console.argparser.PrettyParser`): The parser
                to configure. Use :meth:`add_argument` and :meth:`add_command`
                to define the CLI interface.
        """
        raise NotImplementedError

    @abstractmethod
    def main(self, namespace: argparse.Namespace) -> None:
        """Execute the main application logic.

        This method is called after arguments have been parsed.

        Args:
            namespace (:class:`argparse.Namespace`): The parsed arguments.
        """
        raise NotImplementedError

    @abstractmethod
    def cleanup(self, namespace: argparse.Namespace) -> None:
        """Clean up resources after execution.

        Always called, even if an error occurs. Use this for releasing
        file handles, closing connections, etc.

        Args:
            namespace (:class:`argparse.Namespace`): The parsed arguments.
        """
        raise NotImplementedError

    def _parse(self, argv: Sequence[str] | None = None) -> None:
        try:
            self._parser.parse_args(argv, namespace=self._namespace)
        except (argparse.ArgumentError, argparse.ArgumentTypeError) as e:
            raise CliError(msg=str(e), quiet=False) from None
        except SystemExit as e:  # pragma: no cover
            raise CliError(msg=None, quiet=False) from e

    @staticmethod
    def read_stdin() -> str | None:
        """Read all input from stdin if it is not a terminal.

        Returns:
            :obj:`str` | ``None``: The input content, or ``None`` if stdin is a TTY.
        """
        if not sys.stdin.isatty():
            with fileinput.input(files="-", mode="r") as file_:
                return "".join(list(file_))
        return None

    def add_command(
        self,
        callback: Callable[[argparse.Namespace], None],
        help: str,  # noqa: A002
        description: str | None = None,
        name: str | None = None,
        parents: list[PrettyParser] | None = None,
    ) -> PrettyParser:
        """Register a subcommand.

        Args:
            callback (:obj:`Callable` [ [:class:`argparse.Namespace`] ]): Function
                invoked when this subcommand is selected.
            help (:obj:`str`): Short help text shown in the parent parser.
            description (:obj:`str` | ``None``): Long description. Default: ``help``.
            name (:obj:`str` | ``None``): Subcommand name. Default: ``callback.__name__``.
            parents (:obj:`list` [ :class:`PrettyParser` ] | ``None``): Parent parsers
                to inherit arguments from.

        Returns:
            :class:`~deluxe.console.argparser.PrettyParser`: The new subparser.
        """
        if self._commands is None:
            self._commands = self._parser.add_subparsers(title="commands")
        cmd = self._commands.add_parser(
            name=name or callback.__name__,
            help=help,
            description=description or help,
            parents=parents or [],
        )
        cmd.set_defaults(callback=callback)
        return cmd

    @final
    def __call__(self, *args: str) -> int:
        """Run the full CLI lifecycle.

        Args:
            *args: Command-line arguments. Default: ``sys.argv[1:]``.

        Returns:
            Exit code (0 on success, non-zero on error).
        """
        self._auto_register_commands()
        try:
            self.configure(self._parser)
            self._parse(argv=args or None)
            self.main(self._namespace)
            if hasattr(self._namespace, "callback"):
                self._namespace.callback(self._namespace)
        except CliError as err:
            if err.msg:
                self._message(value=err.msg, quiet=err.quiet)
            return err.code or 1
        else:
            return 0
        finally:
            self.cleanup(self._namespace)

    def _message(self, value: str, quiet: bool) -> None:
        if not quiet:
            sys.stderr.write(f"{self._name}: {value}\n")
