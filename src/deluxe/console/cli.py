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
"""Cli application framework."""

from __future__ import annotations

import argparse
import fileinput
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, final

from deluxe.console.argparser import PrettyParser


if TYPE_CHECKING:
    from collections.abc import Sequence


class CliError(Exception):
    """Exception for CLI errors.

    Args:
        msg (str | None): The error message.
        quiet (bool): Whether to suppress error output.

    Attributes:
        msg (str): The error message.
        quiet (bool): Whether to suppress error output.
        code (int): The error code associated with the exception.
    """

    _error_codes: ClassVar[list[type[BaseException | None]]] = [
        SystemExit,
        Exception,
    ]

    def __init__(self, msg: str | None, quiet: bool) -> None:
        self.msg: str = msg or ""
        self.quiet: bool = quiet
        super().__init__()
        if isinstance(self.__cause__, OSError):
            self.code: int | None = getattr(self.__cause__, "winerror", self.__cause__.errno)
        else:
            self.code = self.get_code(type(self.__cause__))

    @classmethod
    def get_code(cls, exce: type[BaseException | None]) -> int:
        try:
            return cls._error_codes.index(exce)
        except ValueError:
            return 1

    @classmethod
    def register(cls, *exce: type[Exception]) -> None:
        for e in exce:
            if e not in cls._error_codes:
                cls._error_codes.append(e)


class Cli(ABC):
    """Command line interface abstract base class."""

    def __init__(
        self,
        name: str | None = None,
        version: str | None = None,
        prefix: bool = True,
        completion: bool = False,
    ) -> None:
        self._name: str = name or sys.argv[0]
        self._prefix: str | None = f"{name} {version}" if prefix else None
        self._parser: PrettyParser = PrettyParser(
            prog=self._name,
            version=version,
            prefix=self._prefix,
            exit_on_error=False,
            shell_completion=completion,
        )
        self.namespace: argparse.Namespace = argparse.Namespace()

    @abstractmethod
    def configure(self, parser: PrettyParser) -> None:
        raise NotImplementedError

    @abstractmethod
    def main(self, namespace: argparse.Namespace) -> None:
        raise NotImplementedError

    @abstractmethod
    def cleanup(self, namespace: argparse.Namespace) -> None:
        raise NotImplementedError

    def _parse(self, argv: Sequence[str] | None = None) -> None:
        try:
            self._parser.parse_args(argv, namespace=self.namespace)
        except (argparse.ArgumentError, argparse.ArgumentTypeError) as e:
            raise CliError(msg=str(e), quiet=False) from None
        except SystemExit as e:
            raise CliError(msg=None, quiet=False) from e

    @staticmethod
    def read_stdin() -> str | None:
        """Read input from stdin."""
        if not sys.stdin.isatty():
            with fileinput.input(files="-", mode="r") as _file:
                return "".join(list(_file))
        return None

    @final
    def __call__(self, *args: str) -> int:
        """Main entry point of the program.

        Args:
            args: Command line arguments.

        Returns:
            int: The exit code of the program.
        """
        try:
            self.configure(self._parser)
            self._parse(argv=args or None)
            self.main(self.namespace)
        except CliError as e:
            if e.msg:
                self._message(value=e.msg, quiet=e.quiet)
            return e.code or 1
        else:
            return 0
        finally:
            self.cleanup(self.namespace)

    def _message(self, value: str, quiet: bool) -> None:
        if not quiet:
            sys.stderr.write(f"{self._name}: {value}\n")
