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
import atexit
import locale
import multiprocessing as mp
import os
import pwd
import re
import shutil
import signal
import subprocess
import sys
import time
from abc import ABC, ABCMeta, abstractmethod
from asyncio import Future, Task
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    TypeVar,
    cast,
    final,
    overload,
)
from warnings import warn

from deluxe.availability import availability, supported


if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Mapping


_USER_SUPPORT: bool = supported(only=("posix",), but=("wasi", "ios"))


@availability(only="posix", but=("wasi", "ios"))
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
        encoding=locale.getpreferredencoding(do_setlocale=False),
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


PathLike: TypeAlias = str | os.PathLike[str]
StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]


class Command:
    """System command class.

    This class represents a system command and provides methods for running the command
    and handling the output.

    It also supports specifying the user to run the command as on POSIX systems.
    The actual implementation use the sudo command to execute the command
    if user is specified.

    Commands are never executed through a shell.

    This class supports asynchronous execution of the subprocess using asyncio.

    Args:
        name (str): The name of the command.
        path (os.PathLike[str] | None): The path to the command executable.
        user (str | None): The user to run the command as

    Raises:
        Command.Error: If the command is not found on the system.
        NotImplementedError: if user is specified on non POSIX systems.
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
            msg = "specifying user is only supported on POSIX platforms."
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
        input: bytes | None = None,
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
        input: str | None = None,
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
        """  # noqa: DOC502
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
        if cp.returncode:
            raise self._create_exception()(cp.stderr, cp.returncode, args_)
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


##
# Disabling those Ruff rules:
#   <'open()' should be replaced by 'path.open()'>,
#   is more convenient for standard files
#
#   <use context handler for opening file>,
#   standard file should not be closed
#
# ruff: noqa: PTH123, SIM115


class _RealDaemon:
    """RealDaemon class."""

    __workpath__: ClassVar[Path]
    __pidfile__: ClassVar[Path]

    def __init__(self, *args: Any, **kwds: Any) -> None:
        self.running: bool = False

        self.daemonize()
        super().__init__(*args, **kwds)
        self.daemonized: Daemon = cast("Daemon", super())
        self.daemonized.run()

    def daemonize(self) -> None:
        """Daemonize the process using an Unix double fork mechanism."""
        pid_tmp: int

        try:  # decouple from parent environment
            os.chdir("/")
        except OSError as err:
            sys.stderr.write(f"chdir to <{self.__workpath__}> failed:\n{err}\n")
            sys.exit(1)
        else:
            os.setsid()
            os.umask(0)

        try:  # do the second fork
            pid_tmp = os.fork()
            if pid_tmp > 0:
                sys.exit(0)  # exit from second parent
        except OSError as err:
            sys.stderr.write(f"fork #2 failed: {err}\n")
            sys.exit(1)

        ##
        # Daemon code only here
        pid_tmp = os.getpid()

        # redirect standard file descriptors to devnull
        sys.stdout.flush()
        sys.stderr.flush()

        si = open(os.devnull, encoding=None)
        so = open(os.devnull, "a+", encoding=None)
        se = open(os.devnull, "a+", encoding=None)

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.atexit)
        with self.__pidfile__.open("w+") as file:
            file.write(f"{pid_tmp}\n")

    def atexit(self) -> None:
        self.daemonized.atexit()
        self.__pidfile__.unlink()


T = TypeVar("T")


class _DaemonMeta(ABCMeta):
    """Daemon metaclass."""

    WORKPATH_VAR: str = "__workpath__"
    PIDFILE_VAR: str = "__pidfile__"

    def __new__(
        cls: type[type[T]],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwds: Any,
    ) -> type[T]:
        workpath = kwds.pop("workpath", "/")
        if not (workpath := Path(workpath)).is_dir():
            msg = f"<{workpath}> should be an existing directory."
            raise AttributeError(msg)

        if name == "Daemonized":
            pidfile = (Path.home() / f"._{bases[-1].__name__}").with_suffix(".pid")
        else:
            pidfile = (Path.home() / f"._{name}").with_suffix(".pid")

        namespace[_DaemonMeta.PIDFILE_VAR] = pidfile
        namespace[_DaemonMeta.WORKPATH_VAR] = workpath
        return super().__new__(cls, name, bases, namespace, **kwds)

    @staticmethod
    def fork(cls_: type, *args: Any, **kwds: Any) -> None:
        ctx = mp.get_context("fork")
        ps = ctx.Process(target=cls_, args=args, kwargs=kwds)
        ps.start()
        ps.join()

    @staticmethod
    def subclass(daemon: type[T]) -> type:
        return type("Daemonized", (_RealDaemon, daemon), {})

    def __call__(cls: type[T], *args: Any, **kwds: Any) -> T:
        if cls.__name__ == "Daemonized":
            # return a instance of the Daemon if not already running
            pidfile: Path = getattr(cls, _DaemonMeta.PIDFILE_VAR)
            if pidfile.exists():
                sys.exit()
            return super().__call__(*args, **kwds)

        # return a Daemon controller kind instance
        _DaemonMeta.fork(_DaemonMeta.subclass(daemon=cls), *args, **kwds)
        return super().__call__(*args, **kwds)


@availability(only="posix", but="wasi")
class Daemon(ABC, metaclass=_DaemonMeta):
    """A generic Unix daemon abstract base class.

    Make instance of this class execute in a daemonized process
    using an Unix double fork mechanism.

    Availability:
        - Unix, not WASI

    Usage Details
    -------------

    Subclass of the abstract Daemon class should implement the run()
    method. It's where the working logic of the daemon begin. User
    defined Daemon instances should not call this method directly.

    The daemon will write a lock file on the system at its start process.
    This will prevent multiple instances to be created at the same time.
    As soon as the instance is daemonized its run method is called with
    no parameter.

    The daemon executes in its own detached session with no tty attached,
    so it will not inherit the standard files from the python interpreter
    where it was instanciated.

    Code instancing the daemon, as any could expect will received
    a functional instance of the class they defined. This instance
    will act as a daemon controller with the help of its stop(), start()
    and restart() methods.

    Interprocess Communication
    --------------------------

    Daemon subclass will ends up with two instances, the 'controller'
    living in the calling process and the 'worker' living in its own
    detached session. This class make no prevention in regard of a specific
    protocol for interprocess communication, it's up to the class
    implementation.

    About The Unix Double Fork Mechanism
    ------------------------------------

    In Unix every process belongs to a group which in turn belongs
    to a session (session (SID) -> process Group (PGID) -> process (PID)).
    The first process in the session becomes the session leader.
    Every session can have one TTY associated with it and only a session
    leader can take control of a TTY.

    Normally, when launching a daemon, setsid is called (from the child
    process after calling fork) to dissociate the daemon from its controlling
    terminal. However, calling setsid also means that the calling process
    will be the session leader of the new session, which leaves open
    the possibility that the daemon could reacquire a controlling terminal
    in the future.

    The double-fork technique ensures that the daemon process is no longer
    a session leader, making the init process responsible for its cleanup.
    Forking a second child and exiting immediately prevents zombies
    and causes the second child process to be orphaned, preventing it from
    ever acquiring inadvertently a controlling terminal.
    """

    __workpath__: ClassVar[Path]
    __pidfile__: ClassVar[Path]

    @final
    @property
    def pid(self) -> int:
        """The pid of this Daemon.

        Returns:
            int: pid of the daemon if running, 0 otherwise.
        """
        try:
            with self.__pidfile__.open("r") as file:
                return int(file.read().strip())
        except (OSError, ValueError):
            return 0

    @final
    def stop(self) -> None:
        """Stop the daemon.

        Raises:
            OSError: if the daemon could not be killed.
        """
        if not (pid := self.pid):
            msg: str = "Daemon is not running.\n"
            warn(msg, stacklevel=1)
        else:  # Try killing the daemon process
            try:
                while 1:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError as err:
                if str(err.args).find("No such process") > 0:
                    if self.__pidfile__.exists():
                        self.__pidfile__.unlink()
                else:
                    raise OSError(err) from err

    @final
    def start(self) -> int:
        """Starts the daemon.

        If the daemon is not already running daemonize it.

        Returns:
            int: the pid of the daemon.
        """
        if not (pid := self.pid):
            # FIXME: should cache *args and **kwds to passed it to the new daemon
            self.__class__.__new__(self.__class__)
        else:
            msg: str = f"Daemon is already running with pid <{pid}>...\n"
            warn(msg, stacklevel=1)
        return pid

    @final
    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        self.start()

    def atexit(self) -> None:  # noqa: PLR6301
        """Call when the daemon terminate.

        You could overwrite this method to include your cleanup code.
        This method will be executed upon normal interpreter termination.

        see: https://docs.python.org/3/library/atexit
        """
        return

    @abstractmethod
    def run(self) -> None:
        """Daemon Worker method.

        You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized
        by start() or restart().
        """
