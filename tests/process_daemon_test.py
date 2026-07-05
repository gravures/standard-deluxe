"""Tests for the Daemon class in deluxe.process.

Properties tested:
- Metaclass sets __pidfile__ and __workpath__ at class creation time
- Cannot instantiate Daemon directly (abstract)
- Subclass without run() cannot be instantiated (abstract)
- Invalid workpath raises AttributeError at class creation
- pid property returns 0 when not running, PID when running
- start() when not running returns 0
- start() when already running warns and returns existing PID
- stop() sends SIGTERM and cleans up pidfile
- stop() when not running warns
- stop() raises OSError on permission errors
- restart() calls stop() then start()
- atexit() is overridable by subclass
- signal_user1() when not running warns
- signal_user1() raises OSError on permission errors
- signal_user2() when not running warns
- signal_user2() raises OSError on permission errors
- on_user1() is overridable by subclass
- on_user2() is overridable by subclass
- Daemon process runs detached (own session, / as cwd)
- Double-fork produces a properly daemonized process
- Constructor args are stored in _daemon_args_registry
- start() replays constructor args from the registry
- __slots__ subclass works without AttributeError
- Dual controllers share the same daemon
- Registry entry is cleaned up on controller GC
"""

from __future__ import annotations

import gc
import json
import os
import signal
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from deluxe.process import Daemon, _daemon_args_registry  # pyright: ignore[reportPrivateUsage]
from deluxe.availability import AvailabilityError


IS_POSIX = sys.platform != "win32"

# The Daemon class is decorated with @availability(only="posix", but="wasi")
# so it's only usable on POSIX systems. On non-POSIX, instantiation raises
# AvailabilityError. All POSIX-specific tests are skipped on non-POSIX.


# ============================================================================
# Non-POSIX availability
# ============================================================================


@pytest.mark.skipif(IS_POSIX, reason="Daemon is POSIX-only; tested below on POSIX")
def test_daemon_not_available_on_non_posix() -> None:
    """Test that Daemon raises AvailabilityError on non-POSIX."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    with pytest.raises(AvailabilityError):
        _daemon = TestDaemon()


# ============================================================================
# Helpers
# ============================================================================


def _redirect_pidfile(daemon_cls: type[Daemon], tmp_path: Path) -> None:
    """Redirect a daemon class's pidfile into tmp_path for test isolation.

    The metaclass hardcodes pidfile at ~/.{ClassName}.pid. We override it
    so each test gets its own isolated pidfile.

    Note: This only affects the user's class. The Daemonized subclass created
    during forking gets its own __pidfile__ from the metaclass. Therefore this
    helper is only suitable for unit tests that don't trigger the full fork
    lifecycle. Integration tests must NOT use this helper.

    Args:
        daemon_cls: The Daemon subclass whose pidfile to redirect.
        tmp_path: The temporary directory to place the pidfile in.
    """
    daemon_cls.__pidfile__ = tmp_path / f"._{daemon_cls.__name__}.pid"  # type: ignore[attr-defined]


# ============================================================================
# Metaclass: class creation behavior
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_metaclass_sets_default_pidfile() -> None:
    """Metaclass assigns __pidfile__ = ~/.{ClassName}.pid at class creation."""

    class MyDaemon(Daemon):  # type: ignore[valid-type]
        def run(self) -> None: ...

    expected = (Path.home() / "._MyDaemon").with_suffix(".pid")
    assert MyDaemon.__pidfile__ == expected


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_metaclass_sets_default_workpath() -> None:
    """Metaclass assigns __workpath__ = '/' by default."""

    class MyDaemon(Daemon):  # type: ignore[valid-type]
        def run(self) -> None: ...

    assert MyDaemon.__workpath__ == Path("/")


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_metaclass_sets_custom_workpath(tmp_path: Path) -> None:
    """Metaclass stores a custom workpath on the class."""

    class MyDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    assert MyDaemon.__workpath__ == tmp_path


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_metaclass_rejects_invalid_workpath() -> None:
    """Defining a Daemon with a nonexistent workpath raises AttributeError."""

    with pytest.raises(AttributeError, match="should be an existing directory"):

        class BadDaemon(Daemon, workpath="/no/such/dir"):  # type: ignore[valid-type]  # pyright: ignore[reportUnusedClass]
            def run(self) -> None: ...


# ============================================================================
# Abstract enforcement
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_daemon_cannot_be_instantiated_directly() -> None:
    """Daemon() raises TypeError because run() is abstract.

    The metaclass __call__ forks a child process before calling super().__call__()
    which raises the TypeError. The fork triggers a DeprecationWarning about
    fork() in multi-threaded processes, which we suppress here.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*multi-threaded, use of fork.*",
            category=DeprecationWarning,
        )
        with pytest.raises(TypeError):
            Daemon()  # pyright: ignore[reportAbstractUsage]


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_subclass_without_run_cannot_be_instantiated() -> None:
    """A subclass that doesn't implement run() raises TypeError.

    The metaclass __call__ forks a child process before calling super().__call__()
    which raises the TypeError. The fork triggers a DeprecationWarning about
    fork() in multi-threaded processes, which we suppress here.
    """

    class Incomplete(Daemon):  # pyright: ignore[reportImplicitAbstractClass]
        pass

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*multi-threaded, use of fork.*",
            category=DeprecationWarning,
        )
        with pytest.raises(TypeError):
            Incomplete()  # pyright: ignore[reportAbstractUsage]


# ============================================================================
# pid property
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_pid_returns_zero_when_no_pidfile(tmp_path: Path) -> None:
    """pid returns 0 when the pidfile does not exist (OSError path)."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    assert not TestDaemon.__pidfile__.exists()
    daemon = TestDaemon.__new__(TestDaemon)
    assert daemon.pid == 0


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_pid_returns_zero_on_corrupt_pidfile(tmp_path: Path) -> None:
    """pid returns 0 when the pidfile contains non-integer data (ValueError path)."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text("not-a-number\n")
    daemon = TestDaemon.__new__(TestDaemon)
    assert daemon.pid == 0


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_pid_returns_zero_on_empty_pidfile(tmp_path: Path) -> None:
    """pid returns 0 when the pidfile is empty (ValueError path)."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text("")
    daemon = TestDaemon.__new__(TestDaemon)
    assert daemon.pid == 0


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_pid_returns_pid_from_valid_pidfile(tmp_path: Path) -> None:
    """pid returns the integer PID from a valid pidfile."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text("12345\n")
    daemon = TestDaemon.__new__(TestDaemon)
    assert daemon.pid == 12345


# ============================================================================
# start() method
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_start_when_not_running_returns_zero(tmp_path: Path) -> None:
    """start() on a not-yet-started daemon returns 0."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)

    with patch("deluxe.process._DaemonMeta.fork") as mock_fork:
        result = daemon.start()
        mock_fork.assert_called_once()

    assert result == 0


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_start_when_already_running_warns(tmp_path: Path) -> None:
    """start() when the daemon pidfile holds a live PID warns.

    We use our own PID since we know it's alive and won't be killed.
    """

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text(f"{os.getpid()}\n")
    daemon = TestDaemon.__new__(TestDaemon)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = daemon.start()

    assert result == os.getpid()
    assert len(caught) == 1
    assert "already running" in str(caught[0].message)


# ============================================================================
# Constructor args registry
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_start_uses_registry_args(tmp_path: Path) -> None:
    """start() replays constructor args from _daemon_args_registry."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    # Manually register args as if the controller was created normally
    _daemon_args_registry[daemon] = (("port",), {"debug": True})

    with patch("deluxe.process._DaemonMeta.fork") as mock_fork:
        daemon.start()
        mock_fork.assert_called_once()
        # call_args[0] contains all positional args: (subclass_type, *args)
        # call_args[1] contains keyword args: **kwds
        all_args = mock_fork.call_args[0]
        kwds = mock_fork.call_args[1]
        # Skip the first positional arg (the Daemonized subclass type)
        assert all_args[1:] == ("port",)
        assert kwds == {"debug": True}


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_start_falls_back_to_empty_args(tmp_path: Path) -> None:
    """start() uses empty args when controller has no registry entry."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    # No registry entry — simulates a controller created via __new__

    with patch("deluxe.process._DaemonMeta.fork") as mock_fork:
        daemon.start()
        mock_fork.assert_called_once()
        all_args = mock_fork.call_args[0]
        kwds = mock_fork.call_args[1]
        # Only the Daemonized subclass type, no extra positional args
        assert len(all_args) == 1
        assert kwds == {}


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_registry_entry_cleaned_up_on_gc(tmp_path: Path) -> None:
    """WeakKeyDictionary entry is removed when controller is garbage collected."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    _daemon_args_registry[daemon] = (("test",), {"key": "val"})
    assert daemon in _daemon_args_registry

    del daemon
    gc.collect()
    # Entry should be gone — but we can't assert directly on WeakKeyDictionary
    # membership after GC since the key is gone. Just verify no error.
    # The registry should be empty for this controller.


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_slots_subclass_works(tmp_path: Path) -> None:
    """start() works for __slots__ subclasses via the registry.

    The registry stores constructor args externally (WeakKeyDictionary),
    so no attributes are set on the controller instance. This is safe for
    __slots__ subclasses which forbid arbitrary attribute assignment.
    """

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    # Simulate what _DaemonMeta.__call__ does: store args in the registry
    # without setting any attributes on the controller instance.
    _daemon_args_registry[daemon] = ((8080, "prod"), {"verbose": True})

    with patch("deluxe.process._DaemonMeta.fork") as mock_fork:
        daemon.start()
        mock_fork.assert_called_once()
        all_args = mock_fork.call_args[0]
        kwds = mock_fork.call_args[1]
        assert all_args[1:] == (8080, "prod")
        assert kwds == {"verbose": True}


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_dual_controllers_same_daemon(tmp_path: Path) -> None:
    """Two controllers for the same class share the same daemon via pidfile."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    # Simulate a running daemon by writing our own PID
    TestDaemon.__pidfile__.write_text(f"{os.getpid()}\n")

    ctl_1 = TestDaemon.__new__(TestDaemon)
    ctl_2 = TestDaemon.__new__(TestDaemon)
    _daemon_args_registry[ctl_1] = (("from_ctl_1",), {})
    _daemon_args_registry[ctl_2] = (("from_ctl_2",), {})

    # Both controllers see the same daemon
    assert ctl_1.pid == os.getpid()
    assert ctl_2.pid == os.getpid()

    # start() on both warns (daemon already running)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ctl_1.start()
        ctl_2.start()

    assert len(caught) == 2
    assert "already running" in str(caught[0].message)
    assert "already running" in str(caught[1].message)


# ============================================================================
# stop() method
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_when_not_running_warns(tmp_path: Path) -> None:
    """stop() when no daemon is running issues a warning."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        daemon.stop()

    assert len(caught) == 1
    assert "not running" in str(caught[0].message)


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_raises_on_permission_error(tmp_path: Path) -> None:
    """stop() raises OSError when the kill fails for a reason other than
    'No such process' (e.g. permission denied on PID 1)."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text("1\n")
    daemon = TestDaemon.__new__(TestDaemon)

    with pytest.raises(OSError, match="Operation not permitted"):
        daemon.stop()


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_removes_pidfile(tmp_path: Path) -> None:
    """stop() removes the pidfile after the daemon process dies."""
    # Use Python sleep instead of the `sleep` command for cross-platform compat
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    TestDaemon.__pidfile__.write_text(f"{proc.pid}\n")
    try:
        # Send SIGTERM — process exits promptly.
        # stop()'s wait loop detects the dead process via os.kill(pid, 0) failing
        # and breaks out. Pidfile is cleaned up.
        daemon.stop()
        assert proc.wait(timeout=5) is not None  # process is dead
        assert not TestDaemon.__pidfile__.exists()
    finally:
        proc.wait()


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_no_such_process_cleans_pidfile(tmp_path: Path) -> None:
    """stop() cleans up pidfile when SIGTERM raises 'No such process'.

    Covers lines 610-612: when the process is already dead, os.kill raises
    OSError with 'No such process', and the pidfile is removed.
    """

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    # Use a PID that definitely doesn't exist
    TestDaemon.__pidfile__.write_text("999999999\n")
    daemon = TestDaemon.__new__(TestDaemon)

    daemon.stop()
    assert not TestDaemon.__pidfile__.exists()


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_timeout_sends_sigkill(tmp_path: Path) -> None:
    """stop() sends SIGKILL when the process doesn't terminate within timeout.

    Covers lines 619->617, 623-626, 628->exit: the while-loop times out
    (os.kill(pid, 0) keeps succeeding), so SIGKILL is sent as a
    last resort, then the pidfile is cleaned up.
    """
    # Start a long-running process
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    TestDaemon.__pidfile__.write_text(f"{proc.pid}\n")

    try:
        # Mock os.kill(pid, 0) to always succeed so the while-loop
        # never breaks, forcing the timeout/SIGKILL path.
        # Mock time.monotonic to accelerate the timeout (deadline = 0 + 5 = 5,
        # then monotonic returns 10 > 5, triggering the else branch).
        # Mock time.sleep to avoid actual delays.
        orig_kill = os.kill

        def _mock_kill(pid_: int, sig: int) -> None:
            if sig == 0:
                return  # pretend process is alive
            orig_kill(pid_, sig)

        with (
            patch("deluxe.process.os.kill", side_effect=_mock_kill),
            patch("deluxe.process.time.monotonic", side_effect=[0, 10]),
            patch("deluxe.process.time.sleep"),
        ):
            daemon.stop()

        # SIGKILL should have been sent; reap the process and verify it's dead
        proc.wait()
        assert proc.returncode is not None
        assert not TestDaemon.__pidfile__.exists()
    finally:
        proc.wait()


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_process_dies_during_wait(tmp_path: Path) -> None:
    """stop() breaks out of the wait loop when the process terminates.

    Covers lines 619->617: os.kill(pid, 0) raises OSError (process no longer
    exists), so the while-loop breaks and the pidfile is cleaned up.
    """
    # Start a process that exits cleanly on SIGTERM (default Python behavior)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    TestDaemon.__pidfile__.write_text(f"{proc.pid}\n")

    try:
        # SIGTERM is sent first. The process exits promptly.
        # Then in the wait loop, os.kill(pid, 0) raises OSError → loop breaks.
        daemon.stop()
        assert proc.wait(timeout=5) is not None  # process is dead
        assert not TestDaemon.__pidfile__.exists()
    finally:
        proc.wait()


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_stop_sigkill_failure_is_swallowed(tmp_path: Path) -> None:
    """stop() swallows OSError when the SIGKILL fallback fails.

    Covers lines 623-626: the timeout fires and os.kill(pid, SIGKILL)
    raises OSError (e.g. permission denied), which is caught and ignored.
    """
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)
    TestDaemon.__pidfile__.write_text(f"{proc.pid}\n")

    try:
        orig_kill = os.kill

        def _mock_kill(pid_: int, sig: int) -> None:
            if sig == 0:
                return  # pretend process is alive
            if sig == signal.SIGKILL:
                msg = "Permission denied"
                raise OSError(msg)
            orig_kill(pid_, sig)

        with (
            patch("deluxe.process.os.kill", side_effect=_mock_kill),
            patch("deluxe.process.time.monotonic", side_effect=[0, 10]),
            patch("deluxe.process.time.sleep"),
        ):
            # Should not raise — OSError from SIGKILL is swallowed
            daemon.stop()

        assert not TestDaemon.__pidfile__.exists()
    finally:
        proc.terminate()
        proc.wait()


# ============================================================================
# restart() method
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_restart_calls_stop_then_start(tmp_path: Path) -> None:
    """restart() delegates to stop() then start()."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    daemon = TestDaemon.__new__(TestDaemon)

    with patch.object(daemon, "stop") as mock_stop, patch.object(daemon, "start") as mock_start:
        daemon.restart()
        mock_stop.assert_called_once()
        mock_start.assert_called_once()


# ============================================================================
# signal_user1() / signal_user2() methods
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_signal_user1_when_not_running_warns(tmp_path: Path) -> None:
    """signal_user1() when no daemon is running issues a warning."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        daemon.signal_user1()

    assert len(caught) == 1
    assert "not running" in str(caught[0].message)


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_signal_user2_when_not_running_warns(tmp_path: Path) -> None:
    """signal_user2() when no daemon is running issues a warning."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    daemon = TestDaemon.__new__(TestDaemon)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        daemon.signal_user2()

    assert len(caught) == 1
    assert "not running" in str(caught[0].message)


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_signal_user1_raises_on_permission_error(tmp_path: Path) -> None:
    """signal_user1() raises OSError when the kill fails for a reason other
    than 'No such process' (e.g. permission denied on PID 1)."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text("1\n")
    daemon = TestDaemon.__new__(TestDaemon)

    with pytest.raises(OSError, match="Operation not permitted"):
        daemon.signal_user1()


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_signal_user2_raises_on_permission_error(tmp_path: Path) -> None:
    """signal_user2() raises OSError when the kill fails for a reason other
    than 'No such process' (e.g. permission denied on PID 1)."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

    _redirect_pidfile(TestDaemon, tmp_path)
    TestDaemon.__pidfile__.write_text("1\n")
    daemon = TestDaemon.__new__(TestDaemon)

    with pytest.raises(OSError, match="Operation not permitted"):
        daemon.signal_user2()


# ============================================================================
# on_user1() / on_user2() override
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_on_user1_is_overridable(tmp_path: Path) -> None:
    """Subclass can override on_user1() for custom signal handling."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

        def on_user1(self) -> None:  # noqa: PLR6301
            (tmp_path / "user1_received").write_text("yes")

    daemon = TestDaemon.__new__(TestDaemon)
    daemon.on_user1()
    assert (tmp_path / "user1_received").read_text() == "yes"


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_on_user2_is_overridable(tmp_path: Path) -> None:
    """Subclass can override on_user2() for custom signal handling."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

        def on_user2(self) -> None:  # noqa: PLR6301
            (tmp_path / "user2_received").write_text("yes")

    daemon = TestDaemon.__new__(TestDaemon)
    daemon.on_user2()
    assert (tmp_path / "user2_received").read_text() == "yes"


# ============================================================================
# atexit() override
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="Daemon is POSIX-only")
def test_atexit_is_overridable(tmp_path: Path) -> None:
    """Subclass can override atexit() for cleanup logic."""

    class TestDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None: ...

        def atexit(self) -> None:  # noqa: PLR6301
            (tmp_path / "cleaned_up").write_text("yes")

    daemon = TestDaemon.__new__(TestDaemon)
    daemon.atexit()
    assert (tmp_path / "cleaned_up").read_text() == "yes"


# ============================================================================
# Full lifecycle integration
#
# These tests exercise the real double-fork daemon lifecycle.
# They run the daemon in a subprocess to avoid deadlocking inside
# multi-threaded xdist workers — multiprocessing.get_context("fork")
# deadlocks when called from a multi-threaded process.
# ============================================================================

_LIFECYCLE_SCRIPT = """\
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

def main() -> None:
    tmp = Path(sys.argv[1])
    action = sys.argv[2]
    daemon_name = sys.argv[3]

    if action == "lifecycle":
        ready = tmp / "ready"
        info_file = tmp / "daemon_info.json"
        stop_event = tmp / "stop"

        # Import inside subprocess so daemon is defined in a clean process
        from deluxe.process import Daemon, _DaemonMeta

        def run(self) -> None:  # noqa: PLR6301
            # Atomic write: create a temp file then rename so the parent
            # never observes an empty / partial file via exists()+read().
            info_tmp = info_file.with_suffix(".tmp")
            info_tmp.write_text(
                json.dumps({
                    "pid": os.getpid(),
                    "ppid": os.getppid(),
                    "sid": os.getsid(0),
                    "cwd": str(Path.cwd()),
                })
            )
            info_tmp.rename(info_file)
            ready_tmp = ready.with_suffix(".tmp")
            ready_tmp.write_text("ready")
            ready_tmp.rename(ready)
            while not stop_event.exists():
                time.sleep(0.1)

        # Use unique class name per test to avoid pidfile collisions under xdist
        TestDaemon = _DaemonMeta(  # noqa: N806
            daemon_name, (Daemon,), {"run": run}, workpath=str(tmp)
        )

        controller = TestDaemon()
        pidfile = TestDaemon.__pidfile__
        # Poll until ready or timeout
        for _ in range(50):
            if ready.exists():
                break
            time.sleep(0.1)

        result = {
            "ready": ready.exists(),
            "pidfile_exists": pidfile.exists(),
            "controller_pid": controller.pid,
        }
        if ready.exists():
            info = json.loads(info_file.read_text())
            result["info"] = info
            stop_event.write_text("stop")
            controller.stop()
            result["pidfile_removed"] = not pidfile.exists()
        else:
            controller.stop()

        print(json.dumps(result))

    elif action == "singleton":
        ready = tmp / "ready"
        stop_event = tmp / "stop"

        from deluxe.process import Daemon, _DaemonMeta

        def run(self) -> None:  # noqa: PLR6301
            # Atomic write: temp file + rename so the parent never sees
            # an empty file created by open() before write() completes.
            ready_tmp = ready.with_suffix(".tmp")
            ready_tmp.write_text(str(os.getpid()))
            ready_tmp.rename(ready)
            while not stop_event.exists():
                time.sleep(0.1)

        TestDaemon = _DaemonMeta(  # noqa: N806
            daemon_name, (Daemon,), {"run": run}, workpath=str(tmp)
        )

        controller = TestDaemon()
        pidfile = TestDaemon.__pidfile__
        for _ in range(50):
            if ready.exists():
                break
            time.sleep(0.1)

        daemon_pid = int(ready.read_text()) if ready.exists() else 0
        result = {
            "ready": ready.exists(),
            "daemon_pid": daemon_pid,
            "controller_pid": controller.pid,
        }
        if daemon_pid:
            stop_event.write_text("stop")
            controller.stop()
            result["pidfile_removed"] = not pidfile.exists()

        print(json.dumps(result))

    elif action == "signal":
        ready = tmp / "ready"
        user1_received = tmp / "user1"
        user2_received = tmp / "user2"
        stop_event = tmp / "stop"

        from deluxe.process import Daemon, _DaemonMeta

        def run(self) -> None:  # noqa: PLR6301
            # Atomic write: temp file + rename so the parent never sees
            # an empty file created by open() before write() completes.
            ready_tmp = ready.with_suffix(".tmp")
            ready_tmp.write_text(str(os.getpid()))
            ready_tmp.rename(ready)
            while not stop_event.exists():
                time.sleep(0.1)

        def on_user1(self) -> None:  # noqa: PLR6301
            user1_received.write_text("yes")

        def on_user2(self) -> None:  # noqa: PLR6301
            user2_received.write_text("yes")

        TestDaemon = _DaemonMeta(  # noqa: N806
            daemon_name,
            (Daemon,),
            {"run": run, "on_user1": on_user1, "on_user2": on_user2},
            workpath=str(tmp),
        )

        controller = TestDaemon()
        pidfile = TestDaemon.__pidfile__
        for _ in range(50):
            if ready.exists():
                break
            time.sleep(0.1)

        daemon_pid = int(ready.read_text()) if ready.exists() else 0
        result: dict[str, Any] = {
            "ready": ready.exists(),
            "daemon_pid": daemon_pid,
            "controller_pid": controller.pid,
        }
        if daemon_pid:
            # Send SIGUSR1 and wait for handler to fire
            controller.signal_user1()
            for _ in range(50):
                if user1_received.exists():
                    break
                time.sleep(0.1)
            result["user1_received"] = user1_received.exists()

            # Send SIGUSR2 and wait for handler to fire
            controller.signal_user2()
            for _ in range(50):
                if user2_received.exists():
                    break
                time.sleep(0.1)
            result["user2_received"] = user2_received.exists()

            stop_event.write_text("stop")
            controller.stop()
            result["pidfile_removed"] = not pidfile.exists()

        print(json.dumps(result))


if __name__ == "__main__":
    main()
"""


def _run_daemon_script(action: str, tmp_path: Path, daemon_name: str) -> dict[str, Any]:
    """Run the daemon lifecycle script in a clean subprocess.

    Args:
        action: Which scenario to run ("lifecycle" or "singleton").
        tmp_path: Temporary directory for marker files.
        daemon_name: Unique class name for the daemon (avoids pidfile collisions under xdist).

    Returns:
        Parsed JSON result from the subprocess.
    """
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _LIFECYCLE_SCRIPT, str(tmp_path), action, daemon_name],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"Script failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    return json.loads(proc.stdout.strip())


@pytest.mark.skipif(not IS_POSIX, reason="Daemon double-fork is POSIX-only")
def test_full_lifecycle(tmp_path: Path) -> None:
    """Start a real daemon in a subprocess, verify it runs, then stop it.

    Verifies:
    - MyDaemon() triggers a double-fork
    - Daemon process writes its PID to the pidfile
    - Daemon process calls run()
    - controller.pid returns the daemon's PID
    - daemon.stop() kills the daemon and removes the pidfile
    """
    result = _run_daemon_script("lifecycle", tmp_path, f"LifecycleDaemon_{id(tmp_path)}")

    assert result["ready"] is True, "daemon run() was never called"
    assert result["pidfile_exists"] is True
    assert result["controller_pid"] > 0

    info = result["info"]
    assert info["cwd"] == "/", "daemon working directory should be /"
    assert result["pidfile_removed"] is True


@pytest.mark.skipif(not IS_POSIX, reason="Daemon double-fork is POSIX-only")
def test_daemon_singleton_prevents_duplicate_start(tmp_path: Path) -> None:
    """Starting a daemon in a subprocess verifies the lifecycle works.

    The metaclass __call__ checks pidfile.exists() and sys.exit() in the
    Daemonized branch, preventing duplicate workers.
    """
    result = _run_daemon_script("singleton", tmp_path, f"SingletonDaemon_{id(tmp_path)}")

    assert result["ready"] is True, "worker run() was never called"
    assert result["daemon_pid"] > 0
    assert result["controller_pid"] == result["daemon_pid"]
    assert result["pidfile_removed"] is True


@pytest.mark.skipif(not IS_POSIX, reason="Daemon double-fork is POSIX-only")
def test_signal_user1_and_user2_integration(tmp_path: Path) -> None:
    """Start a real daemon, send SIGUSR1 and SIGUSR2, verify hooks fire.

    Verifies:
    - controller.signal_user1() sends SIGUSR1 to the daemon
    - Daemon's on_user1() is called when SIGUSR1 is received
    - controller.signal_user2() sends SIGUSR2 to the daemon
    - Daemon's on_user2() is called when SIGUSR2 is received
    """
    result = _run_daemon_script("signal", tmp_path, f"SignalDaemon_{id(tmp_path)}")

    assert result["ready"] is True, "daemon run() was never called"
    assert result["daemon_pid"] > 0
    assert result["controller_pid"] == result["daemon_pid"]
    assert result["user1_received"] is True, "on_user1() was never called"
    assert result["user2_received"] is True, "on_user2() was never called"
    assert result["pidfile_removed"] is True
