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
"""Process utilities for working with system commands."""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import locale
import multiprocessing as mp
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import weakref
from abc import ABC, ABCMeta, abstractmethod
from asyncio import Future, Task
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeVar,
    cast,
    final,
    overload,
)
from warnings import warn

from deluxe.availability import availability, supported
from deluxe.types import Unset


_USER_SUPPORT: bool = supported(only=("posix",), but=("wasi", "ios"))

if _USER_SUPPORT:
    import pwd

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Mapping

    from deluxe.types import AnyFilePath


__all__ = ("Command", "Daemon", "get_real_users")


# Registry for daemon constructor arguments, keyed by controller instance.
# Uses weak references so entries are automatically cleaned up when the
# controller is garbage collected. This avoids setting attributes on the
# controller instance (which would break __slots__ subclasses) and avoids
# writing sensitive constructor arguments to disk.
_daemon_args_registry: weakref.WeakKeyDictionary[
    object, tuple[tuple[Any, ...], dict[str, Any]]
] = weakref.WeakKeyDictionary()

# Lock to prevent same-process fork races when multiple controllers
# call start() concurrently (e.g. from different threads).
_start_lock = threading.Lock()


@availability(only="posix", but=("wasi", "ios"))
def get_real_users() -> set[str]:
    """Return a set of all real user accounts on the system.

    Retrieves a set of all user accounts that have a valid login shell.
    On Linux, ``/etc/login.defs`` is parsed for the ``UID_MIN`` value.
    On other POSIX systems (macOS, BSD), a default minimum UID of ``500``
    is used, which correctly includes real users starting at ``501``.

    System accounts with a UID below the minimum are excluded, as are
    accounts with nologin-style shells.

    .. note:: Availability: Unix, not WASI, not iOS

    Returns:
        :obj:`set` [:obj:`str` ]: A set of usernames for all real user accounts
        on the system.
    """
    # Determine min UID: parse /etc/login.defs on Linux if available,
    # otherwise fall back to 500 (covers macOS/BSD real users starting at 501)
    min_uid = 500
    login_defs = Path("/etc/login.defs")
    if login_defs.exists():
        with login_defs.open(  # noqa: FURB101
            "r",
            encoding=locale.getpreferredencoding(False),  # noqa: FBT003
        ) as f:
            if sch := re.search(r"^UID_MIN\s+(\d+)", f.read()):  # pragma: no cover
                min_uid = int(sch[1])

    # Shells that indicate "no login"
    nologin_shells = {"/usr/sbin/nologin", "/bin/false", "/usr/bin/nologin", "/sbin/nologin"}

    return {
        p.pw_name
        for p in pwd.getpwall()  # pyright: ignore[reportPossiblyUnboundVariable]
        if p.pw_uid >= min_uid and p.pw_shell not in nologin_shells
    }


class Command:
    """System command class.

    Represents a system command and provides methods for running the command
    and handling the output.

    It also supports specifying the user to run the command as on POSIX systems.
    The actual implementation use the sudo command to execute the command
    if user is specified.

    Commands are never executed through a shell. On POSIX systems, if a
    ``user`` is specified, the command is executed via ``sudo -u <user>``.

    This class supports both synchronous execution via :meth:`__call__` and
    asynchronous execution via :meth:`async_call` using :mod:`asyncio`.

    Args:
        name (:obj:`str`): The name of the command.
        path (:obj:`os.PathLike` [:obj:`str` ] | ``None``): The path to the
            command executable. Default: ``None``.
        user (:obj:`str` | ``None`): The user to run the command as. Requires
            ``sudo`` to be available on the system. Default: ``None``.

    Raises:
        Command.Error: If the command is not found on the system.
        NotImplementedError: if user is specified on non POSIX systems.

    Examples::

        >>> cmd = Command("ls")
        >>> cmd("-la", "/tmp")

    User Switching
    ______________


    The ``user`` parameter is only available on POSIX systems (Linux, macOS,
    BSD). It is not supported on Windows. This section explains why and
    provides guidance for cross-platform development.

    **Why Windows is Different**

    On POSIX systems, ``sudo -u <user>`` allows running a command as a
    different user without knowing their password, provided the invoking
    user has sudo privileges. This model assumes:

    - A centralized authentication system (PAM, ``/etc/passwd``)
    - Passwordless sudo configuration (``/etc/sudoers``)
    - A flat UID-based user model (integer UIDs)

    Windows uses a fundamentally different security model:

    - **UAC (User Account Control)**: Elevation is per-process, not per-command.
      The ``runas`` verb triggers a UAC prompt, but it elevates the *current
      user* to Administrator — it does not switch to a different user account.

    - **No passwordless elevation**: Unlike ``sudo``, Windows ``runas``
      requires the user's password interactively. There is no equivalent of
      ``/etc/sudoers`` for passwordless cross-user execution.

    - **Separate security contexts**: An elevated process runs in a different
      security token. Standard ``subprocess`` cannot capture stdout/stderr
      from an elevated process because the pipes cannot cross the security
      boundary.

    - **SID-based identity**: Windows identifies users by SID (Security
      Identifier), not integer UIDs. User enumeration requires Windows API
      calls (``NetUserEnum``) rather than parsing ``/etc/passwd``.

    **Cross-Platform Guidance**

    If you need to run commands with elevated privileges across platforms,
    use platform-specific branches:

    .. code-block:: python

        import sys
        from deluxe.process import Command

        if sys.platform == "win32":
            # Windows: use PowerShell for elevation
            pws = Command("powershell")
            pws("-Command", "Start-Process regedit -Verb RunAs -Wait")
        else:
            # POSIX: use sudo
            apt = Command("apt")
            apt.user = "root"
            apt("update")

    **Summary of Platform Differences**

    +---------------------+---------------------+---------------------------+
    | Feature             | POSIX               | Windows                   |
    +=====================+=====================+===========================+
    | Run as different    | ``sudo -u <user>``  | Not possible without      |
    | user                |                     | password (use ``runas``)  |
    +---------------------+---------------------+---------------------------+
    | Elevate same user   | ``sudo <cmd>``      | ``runas`` verb (UAC       |
    |                     |                     | prompt)                   |
    +---------------------+---------------------+---------------------------+
    | Capture stdout      | ✅ Direct           | ❌ Separate security      |
    |                     |                     | context                   |
    +---------------------+---------------------+---------------------------+
    | Pass stdin          | ✅ Direct           | ❌ Not possible           |
    +---------------------+---------------------+---------------------------+
    | Wait for exit code  | ✅ Direct           | ⚠️ Requires pywin32       |
    +---------------------+---------------------+---------------------------+

    """

    _SYS_USERS: set[str] = get_real_users() if _USER_SUPPORT else Unset

    class Error(Exception):
        """Exception raised when a system command fails.

        Attributes:
            msg (:obj:`str`): The error message.
            returncode (:obj:`int`): The non-zero exit status code, if available.
        """

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
        elif not (command := shutil.which(name)):
            msg = f"Command {path or name} not found on your system."
            raise Command.Error(msg)

        self.command: str = command
        self.name: str = name

        if not _USER_SUPPORT and user:
            msg = "specifying user is only supported on POSIX plateforms."
            raise NotImplementedError(msg)

        self._user: str | None
        self._user = user if _USER_SUPPORT else None

    @property
    def user(self) -> str | None:
        """The user associated with this command.

        Returns:
            :obj:`str` | ``None``: The username, or ``None`` if not set.
        """
        return self._user

    @user.setter
    @availability(only=("posix",), but=("wasi", "ios"))
    def user(self, user: str | None) -> None:
        """Set the user to run the command as.

        Args:
            user (:obj:`str` | ``None``): The username, or ``None`` to clear.

        Raises:
            Command.Error: If the user is not found on the system.
        """
        if user and user not in Command._SYS_USERS and user != "root":
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
        cwd: AnyFilePath | None = None,
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
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str: ...

    def __call__(
        self,
        *args: str,
        input: str | bytes | None = None,  # noqa: A002
        capture: bool = True,
        text: bool = True,
        encoding: str | None = "UTF-8",
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str | bytes:
        """Run this command.

        Executes the command synchronously and returns its output.

        Args:
            *args (:obj:`str`): The arguments to pass to the command.
            input (:obj:`str` | :obj:`bytes` | ``None``): The input to pass to
                the command's stdin. Default: ``None``.
            capture (:obj:`bool`): Whether to capture the command output.
                Default: ``True``.
            text (:obj:`bool`): Whether to return the output as text or bytes.
                Default: ``True``.
            encoding (:obj:`str` | ``None``): The encoding to use for text output.
                Default: ``"UTF-8"``.
            cwd (:class:`~deluxe.types.AnyFilePath` | ``None``): The current
                working directory for the command. Default: ``None``.
            env (:obj:`~collections.abc.Mapping` [:obj:`str`, :obj:`str` ] | ``None``):
                The environment variables for the command. Default: ``None``.

        Returns:
            :obj:`str` | :obj:`bytes`: The output of the command when it completes
            successfully.

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
        return cp.stdout or ("" if text else b"")

    async def async_call(
        self,
        *args: str,
        input: bytes | None = None,  # noqa: A002
        capture: bool = True,
        cwd: AnyFilePath | None = None,
        env: Mapping[str, str] | None = None,
    ) -> Task[Future[bytes]]:
        """Run this command asynchronously.

        Executes the command as an :class:`asyncio.subprocess.Process` and
        returns a :class:`asyncio.Task` wrapping a :class:`asyncio.Future`
        that resolves to the command's stdout bytes.

        Args:
            *args (:obj:`str`): The arguments to pass to the command.
            input (:obj:`bytes` | ``None``): The input to pass to the command's
                stdin. Default: ``None``.
            capture (:obj:`bool`): Whether to capture the command output.
                Default: ``True``.
            cwd (:class:`~deluxe.types.AnyFilePath` | ``None``): The current
                working directory for the command. Default: ``None``.
            env (:obj:`~collections.abc.Mapping` [:obj:`str`, :obj:`str` ] | ``None``):
                The environment variables for the command. Default: ``None``.

        Returns:
            :class:`asyncio.Task` [:class:`asyncio.Future` [:obj:`bytes` ] ]: A task
            that resolves to the command's stdout bytes.

        Raises:
            Command.Error: A dynamically created subclass if the process
            exits due to a signal (negative return code).
        """  # noqa: DOC502
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


class _RealDaemon:  # pragma: no cover
    """Internal mixin that performs the Unix double-fork daemonization.

    This class is used internally by :class:`_DaemonMeta` to create the actual
    daemon process. It should not be instantiated directly.
    """

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

        # signal handler
        def _sigterm_handler(_signum: int, _frame: Any) -> None:
            sys.exit(0)

        signal.signal(signal.SIGTERM, _sigterm_handler)

        # user-defined signal handlers
        def _sigusr1_handler(_signum: int, _frame: Any) -> None:
            self.daemonized.on_user1()

        def _sigusr2_handler(_signum: int, _frame: Any) -> None:
            self.daemonized.on_user2()

        signal.signal(signal.SIGUSR1, _sigusr1_handler)
        signal.signal(signal.SIGUSR2, _sigusr2_handler)

    def atexit(self) -> None:
        self.daemonized.atexit()
        self.__pidfile__.unlink()


_T = TypeVar("_T")


_STOP_TIMEOUT: float = 5.0


class _DaemonMeta(ABCMeta):  # pragma: posix cover
    """Metaclass for the :class:`Daemon` abstract base class.

    Controls the daemon lifecycle: manages pidfile creation, process forking
    via :mod:`multiprocessing`, and the singleton pattern that prevents
    multiple instances of the same daemon from running simultaneously.
    """

    WORKPATH_VAR: str = "__workpath__"
    PIDFILE_VAR: str = "__pidfile__"

    def __new__(
        cls: type[type[_T]],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwds: Any,
    ) -> type[_T]:
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
    def subclass(daemon: type[_T]) -> type:
        return type("Daemonized", (_RealDaemon, daemon), {})

    def __call__(cls: type[_T], *args: Any, **kwds: Any) -> _T:
        if not supported(only=("posix",), but=("wasi")):  # pragma: win32 cover
            return super().__call__(*args, **kwds)

        if cls.__name__ == "Daemonized":  # pragma: no cover
            # return an instance of the Daemon if not already running
            pidfile: Path = getattr(cls, _DaemonMeta.PIDFILE_VAR)
            if pidfile.exists():
                sys.exit()
            return super().__call__(*args, **kwds)

        # return a Daemon controller kind instance
        _DaemonMeta.fork(_DaemonMeta.subclass(daemon=cls), *args, **kwds)
        controller = super().__call__(*args, **kwds)
        _daemon_args_registry[controller] = (args, kwds)
        return controller


@availability(only="posix", but="wasi")
class Daemon(ABC, metaclass=_DaemonMeta):  # pragma: posix cover
    """A generic Unix daemon abstract base class.

    Make instance of this class execute in a daemonized process
    using an Unix double fork mechanism.

    .. note:: Availability: Unix, not WASI

    Subclasses must implement the :meth:`run` method, which contains the
    daemon's working logic. User-defined :class:`Daemon` instances should
    not call :meth:`run` directly.
    The daemon writes a pidfile at its start to prevent multiple instances
    from running simultaneously. Once daemonized, the :meth:`run` method is
    called with no parameters.
    The daemon executes in its own detached session with no tty attached,
    so it will not inherit the standard files from the python interpreter
    where it was instancied.
    Code instantiating the daemon will receive a functional instance of the
    defined class. This instance acts as a daemon controller.

    Keyword Args:
        workpath (:class:`~pathlib.Path` | :obj:`str`): The working directory
            for the daemon process. Must be an existing directory.
            Default: ``"/"``.

    Interprocess Communication
    --------------------------

    Daemon subclasses will end up with two instances: the *controller*
    living in the calling process, and the *worker* living in its own
    detached session.
    The controller provides a built-in set of methods to manage the daemon's
    life cycle: :meth:`start`, :meth:`stop`, :meth:`restart`, :meth:`signal_user1`,
    and :meth:`signal_user2` (see next section for details).

    For richer communication channels (bidirectional pipes, shared memory,
    sockets, etc.), this class makes no provision for a specific protocol;
    it is up to the subclass implementation. Common Python options include:

    - :class:`multiprocessing.Queue` — thread-safe message passing between
      the controller and the daemon worker.
    - :class:`multiprocessing.connection.Connection` (via :func:`multiprocessing.Pipe`) —
      lightweight bidirectional byte stream.
    - :mod:`multiprocessing.shared_memory` — zero-copy shared data between
      processes (Python 3.8+).
    - :mod:`socket` — Unix domain sockets for structured protocols or
      TCP sockets for network-accessible daemons.
    - :mod:`asyncio` event loop with :class:`asyncio.Queue` — for daemons
      built on asynchronous I/O.

    Controller Semantics
    --------------------

    Instantiating a :class:`Daemon` subclass returns a *controller* — a
    lightweight handle that manages the daemon's lifecycle. The controller
    is not the daemon itself; it is a proxy that communicates with the
    daemon through the pidfile and signals.

    **Multiple controllers are allowed.** Several controller instances can
    coexist for the same daemon class within a single process or across
    processes. All controllers for a given class point to the same daemon
    process. Calling :meth:`stop`, :meth:`start`, :meth:`restart`,
    :meth:`signal_user1`, or :meth:`signal_user2` on
    *any* controller affects the shared daemon.

    **The daemon is a system-level singleton.** Only one daemon process
    runs at a time for a given class, enforced by the pidfile. When a new
    controller is created while the daemon is already running, the
    singleton guard prevents a duplicate daemon from starting. The new
    controller simply becomes another handle to the existing daemon.

    **Constructor arguments are preserved per controller.** Each controller
    retains the ``*args`` and ``**kwds`` passed to its constructor. When
    :meth:`start` is called to (re)launch the daemon, it uses the
    calling controller's original arguments. This means different
    controllers may hold different argument sets; the last controller to
    call :meth:`start` determines the daemon's configuration.

    .. warning::

        Constructor arguments are stored in memory for the lifetime of
        the controller and are never written to disk. If the controller
        is garbage collected, its arguments are lost. If a daemon dies
        and needs to be restarted, the controller calling :meth:`start`
        must have been created with the intended arguments.

    **Concurrency safety.** A process-level lock prevents two controllers
    in the same process from racing through :meth:`start` concurrently.
    Cross-process races are handled by the pidfile singleton guard.

    User Signals
    ^^^^^^^^^^^^

    The controller's :meth:`signal_user1` and :meth:`signal_user2` methods
    send ``SIGUSR1`` and ``SIGUSR2`` to the daemon process. When the
    daemon receives one of these signals, it calls the overridable hook
    method :meth:`on_user1` or :meth:`on_user2`. The default
    implementations are no-ops; override them in your subclass to define
    custom behavior.

    .. code-block:: python

        import time
        from deluxe.process import Daemon

        class Worker(Daemon):
            def run(self):
                while True:
                    time.sleep(1)

            def on_user1(self):
                # Called when controller sends SIGUSR1
                self.reloading = True

        daemon = Worker()
        daemon.start()
        daemon.signal_user1()  # sends SIGUSR1 -> on_user1()
        daemon.stop()

    .. note::

        The ``on_user1`` / ``on_user2`` hooks run inside a signal
        handler. Keep them lightweight: set a flag or event, and defer
        heavy work to the main ``run()`` loop.

    About The Unix Double Fork Mechanism
    ------------------------------------

    In Unix every process belongs to a group which in turn belongs
    to a session (session (SID) -> process Group (PGID) -> process (PID)).
    The first process in the session becomes the session leader.
    Every session can have one TTY associated with it and only a session
    leader can take control of a TTY.

    Normally, when launching a daemon, ``setsid`` is called (from the child
    process after calling ``fork``) to dissociate the daemon from its controlling
    terminal. However, calling ``setsid`` also means that the calling process
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
        """The PID of this daemon.

        Returns:
            :obj:`int`: The PID of the daemon if running, ``0`` otherwise.
        """
        try:
            with self.__pidfile__.open("r") as file:
                return int(file.read().strip())
        except (OSError, ValueError):
            return 0

    @final
    def stop(self) -> None:
        """Stop the daemon.

        Sends ``SIGTERM`` to the daemon process and waits for it to terminate.
        If the daemon does not terminate within a timeout, ``SIGKILL`` is sent
        as a last resort. If the daemon is not running, a warning is issued and
        the pidfile is cleaned up if present.

        Raises:
            OSError: If the daemon process could not be killed for a
                     reason other than it not existing.
        """
        if not (pid := self.pid):
            msg: str = "Daemon is not running.\n"
            warn(msg, stacklevel=1)
            return

        # Send SIGTERM once
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as err:
            if "No such process" in str(err):  # pragma: no cover
                if self.__pidfile__.exists():
                    self.__pidfile__.unlink()
                return
            raise

        # Wait for the process to terminate, with a timeout
        deadline = time.monotonic() + _STOP_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:  # pragma: no cover
                break
        else:
            # Timeout: force-kill with SIGKILL
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)

        if self.__pidfile__.exists():  # pragma: no cover
            self.__pidfile__.unlink()

    @final
    def start(self) -> int:
        """Start the daemon.

        If the daemon is not already running, it is daemonized. If it is
        already running, a warning is issued.

        Returns:
            :obj:`int`: The PID of the already-running daemon, or ``0`` if
            a new daemon was started.
        """
        if not (pid := self.pid):
            with _start_lock:
                # Double-check after acquiring the lock to prevent race
                # conditions when multiple controllers call start()
                # concurrently from the same process.
                if not (pid := self.pid):
                    args, kwds = _daemon_args_registry.get(self, ((), {}))
                    _DaemonMeta.fork(_DaemonMeta.subclass(daemon=self.__class__), *args, **kwds)
        else:
            msg: str = f"Daemon is already running with pid <{pid}>...\n"
            warn(msg, stacklevel=1)
        return pid

    @final
    def restart(self) -> None:
        """Restart the daemon.

        Stops the daemon if running, then starts it again.
        """
        self.stop()
        self.start()

    @final
    def signal_user1(self) -> None:
        """Send ``SIGUSR1`` to the daemon process.

        The daemon's :meth:`on_user1` method is invoked when this
        signal is received. Override :meth:`on_user1` in your subclass
        to define the response.

        If the daemon is not running, a warning is issued.
        """
        if not (pid := self.pid):
            msg: str = "Daemon is not running.\n"
            warn(msg, stacklevel=1)
            return
        os.kill(pid, signal.SIGUSR1)

    @final
    def signal_user2(self) -> None:
        """Send ``SIGUSR2`` to the daemon process.

        The daemon's :meth:`on_user2` method is invoked when this
        signal is received. Override :meth:`on_user2` in your subclass
        to define the response.

        If the daemon is not running, a warning is issued.
        """
        if not (pid := self.pid):
            msg: str = "Daemon is not running.\n"
            warn(msg, stacklevel=1)
            return
        os.kill(pid, signal.SIGUSR2)

    def atexit(self) -> None:  # noqa: PLR6301
        """Called when the daemon terminates.

        Override this method to include cleanup code. This method is registered
        via :func:`atexit.register` and will be executed upon normal interpreter
        termination.

        See Also:
            :func:`atexit.register`
        """
        return  # pragma: no cover

    @abstractmethod
    def run(self) -> None:
        """Daemon worker method.

        You must override this method when subclassing :class:`Daemon`.
        It will be called after the process has been daemonized by
        :meth:`start` or :meth:`restart`.
        """

    def on_user1(self) -> None:  # noqa: PLR6301
        """Handler for ``SIGUSR1`` received by the daemon.

        Override this method in your subclass to define custom behavior
        when the controller sends ``SIGUSR1`` via :meth:`signal_user1`.

        The default implementation is a no-op.

        .. note::

            This method is called from a signal handler. Keep the
            implementation lightweight and avoid blocking operations.
            Use a flag or event to defer heavy work to the main loop.
        """
        return  # pragma: no cover

    def on_user2(self) -> None:  # noqa: PLR6301
        """Handler for ``SIGUSR2`` received by the daemon.

        Override this method in your subclass to define custom behavior
        when the controller sends ``SIGUSR2`` via :meth:`signal_user2`.

        The default implementation is a no-op.

        .. note::

            This method is called from a signal handler. Keep the
            implementation lightweight and avoid blocking operations.
            Use a flag or event to defer heavy work to the main loop.
        """
        return  # pragma: no cover
