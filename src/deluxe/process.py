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
"""Process module.

This module provides the Command class for working with system processes.
"""

from __future__ import annotations

import asyncio
import locale
import os
import pwd
import re
import shutil
import subprocess
from asyncio import Future, Task
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias, overload

from deluxe.availability import availability, supported


if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Mapping


_USER_SUPPORT: bool = supported(only=("posix",), but=("wasi", "ios"))


@availability(only=("posix",), but=("wasi", "ios"))
def get_real_users() -> set[str]:
    """Return a set of all real user accounts on the system.

    This function retrieves a set of all user accounts on the system
    that have a valid shell and a home directory starting with "/home".
    It excludes system accounts with a UID less than the minimum UID
    defined in the /etc/login.defs file.

    Availability: Unix, not WASI, not iOS

    Returns:
        set[str]: A list of usernames for all real user accounts on the system.
    """
    with Path("/etc/login.defs").open(
        "r",
        encoding=locale.getpreferredencoding(False),  # noqa: FBT003
    ) as lgn:
        min_uid = int(sch[1]) if (sch := re.search(r"^UID_MIN\s+(\d+)", lgn.read())) else 1000
    return {
        p.pw_name
        for p in pwd.getpwall()
        if (
            p.pw_uid >= min_uid
            and p.pw_shell not in {"/usr/sbin/nologin", "/bin/false"}
            and p.pw_dir.startswith("/home")
        )
    }


StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]


class Command:
    """System command class.

    This class represents a system command and provides methods for running the command
    and handling the output.

    It also supports specifying the user to run the command as on POSIX systems.
    The actual implementation use the sudo command to eecute the command
    if user is specified.

    Commands are never executed through a shell.

    This class supports asynchronous execution of the subprocess using asyncio.

    Args:
        name (str): The name of the command.
        path (os.PathLike[str] | None): The path to the command executable.
        user (str | None): The user to run the command as

    Raises:
        Command.Error: If the command is not found on the system.
        NotmplementedError: if user is specified on non POSIX systems.
    """

    _SYS_USERS: set[str] = get_real_users()

    class Error(Exception):
        def __init__(
            self, msg: str | bytes | None, retcode: int = 0, cmd: tuple[str, ...] | None = None
        ) -> None:
            if retcode and cmd:
                cmd_ = " ".join(cmd)
                msg = f"command <{cmd_}> returned non-zero exit status {retcode}.\n{msg or ''}"
                self.returncode: int = retcode
            self.msg: str = msg.decode() if isinstance(msg, bytes) else msg or ""
            super().__init__(msg)

    __slots__: tuple[str, ...] = ("_user", "command", "name")

    def __init__(
        self,
        name: str,
        *,
        path: os.PathLike[str] | None = None,
        user: str | None = None,
    ) -> None:
        if path and Path(path).is_file():
            command = str(path)

        if not (command := shutil.which(name)):
            msg = f"Command {path or name} not found on your system."
            raise Command.Error(msg)

        self.command: str = command
        self.name: str = name

        if not _USER_SUPPORT and user:
            msg = "specifying user is only supported on POSIX plateforms."
            raise NotImplementedError(msg)

        self._user: str | None
        self.user = user

    @property
    def user(self) -> str | None:
        """Returns the user associated with this command."""
        return self._user

    @user.setter
    @availability(only=("posix",), but=("wasi", "ios"))
    def user(self, user: str | None) -> None:
        if user and (user not in Command._SYS_USERS or user != "root"):
            msg = f"User {user} not found on your system."
            raise Command.Error(msg)
        self._user = user

    def _create_exception(self) -> type[Command.Error]:
        return type(f"{self.name.capitalize()}Error", (Command.Error,), {})

    def _compose(self, *args: str) -> tuple[str, ...]:
        if self._user:
            return ("sudo", "-u", self._user, "--preserve-env", self.command, *args)
        return (self.command, *args)

    @overload
    def __call__(
        self,
        *args: str,
        input: bytes | None = None,  # noqa: A002
        capture: bool = True,
        text: Literal[False],
        encoding: str | None = "UTF-8",
        cwd: StrOrBytesPath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> bytes: ...

    @overload
    def __call__(
        self,
        *args: str,
        input: str | None = None,  # noqa: A002
        capture: bool = True,
        text: Literal[True] = True,
        encoding: str | None = "UTF-8",
        cwd: StrOrBytesPath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str: ...

    def __call__(
        self,
        *args: str,
        input: str | bytes | None = None,  # noqa: A002
        capture: bool = True,
        text: bool = True,
        encoding: str | None = "UTF-8",
        cwd: StrOrBytesPath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str | bytes:
        """Run this command.

        Args:
            *args (str): The arguments to pass to the command.
            input (str | bytes | None): The input to pass to the command.
            capture (bool): Whether to capture the command output.
            text (bool): Whether to return the output as text or bytes.
            encoding (str | None): The encoding to use for text output.
            cwd (StrOrBytesPath | None): The current working directory for the command.
            env (Mapping[str, str] | None): The environment variables for the command.

        Returns:
            str | bytes: The output of the command when command completes successfully.

        Raises:
            Command.Error: If the command returns with a non-zero exit status.
        """
        args_ = self._compose(*args)
        cp = subprocess.run(  # noqa: S603
            args_,
            capture_output=capture,
            shell=False,
            check=False,
            input=input,
            text=text,
            encoding=encoding if text else None,
            cwd=cwd,
            env=env,
        )
        return cp.stdout or "" if text else b""

    async def async_call(
        self,
        *args: str,
        input: bytes | None = None,  # noqa: A002
        capture: bool = True,
        cwd: StrOrBytesPath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> Task[Future[bytes]]:
        """Run this command asynchronously.

        Args:
            *args (str): The arguments to pass to the command.
            input (bytes | None): The input to pass to the command.
            capture (bool): Whether to capture the command output.
            cwd (StrOrBytesPath | None): The current working directory for the command.
            env (Mapping[str, str] | None): The environment variables for the command.

        Returns:
            asyncio.Task: A task representing the command execution.
        """
        args_ = self._compose(*args)

        proc = await asyncio.subprocess.create_subprocess_exec(
            *args_,
            stdin=subprocess.PIPE if input else None,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            cwd=cwd,
            env=env,
        )
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        async def _wait_co(
            proc: Process, input_: bytes | None, future: Future[bytes]
        ) -> Future[bytes]:
            stdout, stderr = await proc.communicate(input_)
            if proc.returncode and proc.returncode < 0:
                future.set_exception(
                    self._create_exception()(
                        stderr,
                        proc.returncode,
                        args_,
                    ),
                )
            else:
                future.set_result(stdout or b"")
            return future

        return loop.create_task(
            _wait_co(proc, input, future),
            name=self.name,
        )
