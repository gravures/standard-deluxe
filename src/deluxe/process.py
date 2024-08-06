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
"""Process module."""

from __future__ import annotations

import getpass
import locale
import pwd
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    import os


def get_real_users() -> set[str]:
    """Return a set of all real user accounts on the system.

    This function retrieves a set of all user accounts on the system
    that have a valid shell and a home directory starting with "/home".
    It excludes system accounts with a UID less than the minimum UID
    defined in the /etc/login.defs file.

    Returns:
        set[str]: A list of usernames for all real user accounts on the system.
    """
    with Path("/etc/login.defs").open(
        "r",
        encoding=locale.getpreferredencoding(False),  # noqa: FBT003
    ) as lgn:
        min_uid = int(sch[1]) if (sch := re.search("^UID_MIN\\s+(\\d+)", lgn.read())) else 1000
    return {
        p.pw_name
        for p in pwd.getpwall()
        if (
            p.pw_uid >= min_uid
            and p.pw_shell not in {"/usr/sbin/nologin", "/bin/false"}
            and p.pw_dir.startswith("/home")
        )
    }


class Command:
    """System command class."""

    SYS_USERS: set[str] = get_real_users()

    class Error(Exception):
        def __init__(self, msg: str, retcode: int = 0, cmd: list[str] | None = None) -> None:
            if retcode and cmd:
                _cmd = " ".join(cmd)
                msg = f"command <{_cmd}> returned non-zero exit status {retcode}.\n{msg}"
                self.returncode = retcode
            self.msg = msg
            super().__init__(msg)

    __slots__ = ("_user", "command", "name")

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
        self._user: str = user or getpass.getuser()
        self.name: str = name

    @property
    def user(self) -> str:
        """Returns the user associated with this command."""
        return self._user

    @user.setter
    def user(self, user: str) -> None:
        if user not in Command.SYS_USERS or user != "root":
            msg = f"User {user} not found on your system."
            raise Command.Error(msg)
        self._user = user

    def _create_exception(self) -> type:
        return type(f"{self.name.capitalize()}Error", (Command.Error,), {})

    def _run(self, *args: str, user: str, capture: bool = True, **kwargs: Any) -> str:
        """Run the command and return stdout when command completes successfully."""
        _args = ["sudo", "-u", user]

        if kwargs.get("env") is not None:
            _env = ",".join(kwargs["env"].keys())
            _args.append(f"--preserve-env={_env}")

        _args.append(self.command)
        _args.extend(args)
        cp = subprocess.run(  # noqa: S603
            _args,
            capture_output=capture,
            shell=False,
            check=False,
            encoding="UTF-8",
            text=True,
            **kwargs,
        )
        if cp.returncode:
            raise self._create_exception()(cp.stderr, cp.returncode, _args)
        return cp.stdout or ""  # noqa: DOC201

    def __call__(self, *args: str, capture: bool = True, **kwargs: Any) -> str:  # noqa: D102
        return self._run(*args, user=self._user, capture=capture, **kwargs)
