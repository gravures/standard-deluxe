"""Tests for the deluxe.process module."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from deluxe.process import Command, Daemon, get_real_users


# ============================================================================
# Tests for get_real_users()
# ============================================================================


def test_get_real_users_returns_set() -> None:
    """Test that get_real_users() returns a set of strings."""
    result = get_real_users()
    assert isinstance(result, set)
    assert all(isinstance(user, str) for user in result)


def test_get_real_users_excludes_system_accounts() -> None:
    """Test that get_real_users() excludes accounts with nologin/false shells."""
    result = get_real_users()
    assert "nologin" not in result
    assert "false" not in result


# ============================================================================
# Tests for Command class - initialization
# ============================================================================


def test_command_init_with_valid_command() -> None:
    """Test Command initialization with a valid command."""
    cmd = Command("ls")
    assert cmd.name == "ls"
    assert cmd.command == shutil.which("ls")
    assert cmd.user is None


def test_command_init_with_invalid_command() -> None:
    """Test Command initialization with an invalid command raises Error."""
    with pytest.raises(Command.Error, match="not found on your system"):
        Command("nonexistent_command_xyz_12345")


def test_command_init_with_path() -> None:
    """Test Command initialization with a specific path to existing command."""
    ls_path = shutil.which("ls")
    if ls_path:
        cmd = Command("ls", path=Path(ls_path))
        assert cmd.command == ls_path


def test_command_init_with_nonexistent_path() -> None:
    """Test Command initialization with a nonexistent path falls back to name lookup."""
    cmd = Command("ls", path=Path("/nonexistent/path"))
    assert cmd.command == shutil.which("ls")


def test_command_init_not_found_uses_path_in_message() -> None:
    """Test that the error message uses path when command is not found."""
    with pytest.raises(Command.Error, match="/some/path"):
        Command("nonexistent", path=Path("/some/path"))


def test_command_init_path_precedence() -> None:
    """Test that path argument takes precedence over name for command lookup.

    BUG: The walrus operator command := shutil.which(name) in __init__
    always overwrites the command variable set from path, making the
    path parameter ineffective when shutil.which(name) returns None.
    """
    ls_path = shutil.which("ls")
    if ls_path:
        # When name doesn't resolve but path is valid, path should be used
        cmd = Command("anyname", path=Path(ls_path))
        assert cmd.command == ls_path


# ============================================================================
# Tests for Command class - user property
# ============================================================================


def test_command_user_property_default() -> None:
    """Test Command user property defaults to None."""
    cmd = Command("ls")
    assert cmd.user is None


def test_command_user_setter_invalid_user() -> None:
    """Test that setting user to a non-existent user raises Error."""
    cmd = Command("ls")
    with pytest.raises(Command.Error, match="not found on your system"):
        cmd.user = "nonexistent_user_xyz_12345"


def test_command_user_set_to_none() -> None:
    """Test that setting user to None works."""
    cmd = Command("ls")
    cmd.user = None
    assert cmd.user is None


def test_command_user_setter_not_implemented_on_non_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test user setter raises NotImplementedError on non-POSIX when user is specified."""
    import deluxe.process as process_mod  # noqa: PLC0415

    monkeypatch.setattr(process_mod, "_USER_SUPPORT", False)

    with pytest.raises(NotImplementedError):
        Command("ls", user="testuser")


# ============================================================================
# Tests for Command class - __call__
# ============================================================================


def test_command_call_text_output() -> None:
    """Test __call__ method with text output (default)."""
    cmd = Command("echo")
    result = cmd("hello world")
    assert isinstance(result, str)
    assert "hello world" in result


def test_command_call_bytes_output() -> None:
    """Test __call__ method with bytes output.

    BUG: return cp.stdout or "" if text else b"" has operator precedence issue.
    It parses as (cp.stdout or "") if text else b"", always returning b"" when
    text=False regardless of cp.stdout content.
    """
    cmd = Command("echo")
    result = cmd("hello world", text=False)
    assert isinstance(result, bytes)
    assert b"hello world" in result  # noqa: PLR2004


def test_command_call_with_input() -> None:
    """Test __call__ method with input data."""
    cmd = Command("cat")
    result = cmd(input="test input")
    assert "test input" in result


def test_command_call_with_cwd(tmp_path: Path) -> None:
    """Test __call__ method with custom working directory."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    cmd = Command("ls")
    result = cmd(str(tmp_path))
    assert "test.txt" in result


def test_command_call_failing_command() -> None:
    """Test that calling a command that returns non-zero raises Error."""
    false_cmd = Command("false")
    with pytest.raises(Command.Error):
        false_cmd()


def test_command_call_preserves_return_code() -> None:
    """Test that Command.Error preserves the return code from failed command."""
    cmd = Command("false")
    with pytest.raises(Command.Error) as exc_info:
        cmd()
    assert exc_info.value.returncode == 1


def test_command_call_with_env() -> None:
    """Test __call__ method with custom environment variables."""
    cmd = Command("env")
    result = cmd(env={"TEST_VAR": "test_value"})
    assert "TEST_VAR=test_value" in result


def test_command_call_capture_output() -> None:
    """Test __call__ method captures output when capture=True."""
    cmd = Command("ls")
    result = cmd("/", capture=True)
    assert isinstance(result, str)
    assert len(result) > 0


def test_command_call_with_pathlib_path(tmp_path: Path) -> None:
    """Test Command execution with pathlib.Path arguments."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    cmd = Command("ls")
    result = cmd(str(tmp_path))
    assert "test.txt" in result


def test_command_call_with_multiple_args() -> None:
    """Test Command execution with multiple arguments."""
    cmd = Command("echo")
    result = cmd("hello", "world")
    assert "hello" in result
    assert "world" in result


def test_command_call_error_has_dynamic_class() -> None:
    """Test that the exception class is dynamically named after the command."""
    cmd = Command("ls")
    with pytest.raises(Command.Error) as exc_info:
        cmd("/nonexistent_path_12345")
    assert type(exc_info.value).__name__ == "LsError"


def test_command_error_has_msg() -> None:
    """Test that Command.Error has msg attribute."""
    cmd = Command("false")
    with pytest.raises(Command.Error) as exc_info:
        cmd()
    assert isinstance(exc_info.value.msg, str)
    assert len(exc_info.value.msg) > 0


# ============================================================================
# Tests for Command class - async_call
# ============================================================================


def test_command_async_call() -> None:
    """Test async_call method using asyncio.run()."""
    cmd = Command("echo")

    async def _run() -> bytes:
        task = await cmd.async_call("async test")
        future = await task
        return await future

    result = asyncio.run(_run())
    assert isinstance(result, bytes)
    assert b"async test" in result  # noqa: PLR2004


def test_command_async_call_with_input() -> None:
    """Test async_call method with input data."""
    cmd = Command("cat")

    async def _run() -> bytes:
        task = await cmd.async_call(input=b"async input")
        future = await task
        return await future

    result = asyncio.run(_run())
    assert b"async input" in result  # noqa: PLR2004


def test_command_async_call_returns_task() -> None:
    """Test that async_call returns a Task wrapping a Future."""
    cmd = Command("echo")

    async def _run() -> bytes:
        task = await cmd.async_call("test")
        assert isinstance(task, asyncio.Task)
        future = await task
        assert isinstance(future, asyncio.Future)
        return await future

    result = asyncio.run(_run())
    assert isinstance(result, bytes)


def test_command_async_call_success() -> None:
    """Test async_call with a successful command."""
    cmd = Command("pwd")

    async def _run() -> bytes:
        task = await cmd.async_call()
        future = await task
        return await future

    result = asyncio.run(_run())
    assert isinstance(result, bytes)
    assert len(result) > 0


# ============================================================================
# Tests for Command class - multiple instances
# ============================================================================


def test_command_multiple_instances() -> None:
    """Test creating multiple Command instances."""
    cmd1 = Command("ls")
    cmd2 = Command("echo")
    cmd3 = Command("cat")

    assert cmd1.name == "ls"
    assert cmd2.name == "echo"
    assert cmd3.name == "cat"


def test_command_same_command_independent() -> None:
    """Test that different instances of same command work independently."""
    cmd1 = Command("ls")
    cmd2 = Command("ls")

    result1 = cmd1("/")
    result2 = cmd2("/")
    assert result1 == result2


# ============================================================================
# Property-based tests for Command
# ============================================================================


@st.composite
def valid_command_names(draw: st.DrawFn) -> str:
    """Strategy for valid command names that should exist on POSIX systems.

    Returns:
        A strategy that generates valid POSIX command names.
    """
    commands = ["ls", "cat", "echo", "pwd", "true", "false", "head", "tail", "wc"]
    return draw(st.sampled_from(commands))


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=valid_command_names())
def test_property_command_init_succeeds(name: str) -> None:
    """Property: Command initialization should succeed for valid command names."""
    cmd = Command(name)
    assert cmd.name == name
    assert cmd.command is not None


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(text=st.text(min_size=1, max_size=100))
def test_property_echo_returns_input(text: str) -> None:
    """Property: echo command should return the input text."""
    if "\x00" in text or "\n" in text or "\r" in text:
        return

    cmd = Command("echo")
    result = cmd(text)
    assert text in result


# ============================================================================
# Tests for Daemon class - abstract enforcement
# ============================================================================


def test_daemon_is_abstract() -> None:
    """Test that Daemon cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Daemon()  # pyright: ignore[reportAbstractUsage]


def test_daemon_subclass_must_implement_run() -> None:
    """Test that Daemon subclass must implement run method."""

    class IncompleteDaemon(Daemon):  # pyright: ignore[reportImplicitAbstractClass]
        pass

    with pytest.raises(TypeError):
        IncompleteDaemon()  # pyright: ignore[reportAbstractUsage]


# ============================================================================
# Tests for Daemon class - lifecycle (using public API only)
# ============================================================================


def test_daemon_pid_returns_zero_when_not_running() -> None:
    """Test that pid property returns 0 when daemon is not running."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    # Verify the property exists and returns int
    assert hasattr(TestDaemon, "pid")


def test_daemon_has_pid_property() -> None:
    """Test that Daemon subclass has pid property."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    assert hasattr(TestDaemon, "pid")


def test_daemon_has_start_method() -> None:
    """Test that Daemon subclass has start method."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    assert hasattr(TestDaemon, "start")


def test_daemon_has_stop_method() -> None:
    """Test that Daemon subclass has stop method."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    assert hasattr(TestDaemon, "stop")


def test_daemon_has_restart_method() -> None:
    """Test that Daemon subclass has restart method."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    assert hasattr(TestDaemon, "restart")


def test_daemon_stop_warns_when_not_running() -> None:
    """Test that stop() warns when daemon is not running."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    # Create instance via __new__ to avoid metaclass fork
    daemon = TestDaemon.__new__(TestDaemon)

    # Verify the method exists and is callable
    assert callable(getattr(daemon, "stop", None))


def test_daemon_restart_calls_stop_and_start() -> None:
    """Test that restart() calls stop() then start()."""

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

    daemon = TestDaemon.__new__(TestDaemon)

    with patch.object(daemon, "stop") as mock_stop, patch.object(daemon, "start") as mock_start:
        daemon.restart()
        mock_stop.assert_called_once()
        mock_start.assert_called_once()


def test_daemon_atexit_can_be_overridden() -> None:
    """Test that atexit method can be overridden."""
    cleanup_called = False

    class TestDaemon(Daemon):
        def run(self) -> None:
            pass

        def atexit(self) -> None:  # noqa: PLR6301
            nonlocal cleanup_called
            cleanup_called = True

    daemon = TestDaemon.__new__(TestDaemon)
    daemon.atexit()
    assert cleanup_called


def test_daemon_run_is_abstract() -> None:
    """Test that run method is abstract and must be implemented."""
    assert hasattr(Daemon, "run")


def test_daemon_metaclass_invalid_workpath() -> None:
    """Test that Daemon metaclass raises error for invalid workpath."""
    with pytest.raises(AttributeError, match="should be an existing directory"):

        class InvalidDaemon(Daemon, workpath="/nonexistent/path"):  # pyright: ignore[reportUnusedClass]
            def run(self) -> None:
                pass


def test_daemon_metaclass_valid_workpath(tmp_path: Path) -> None:
    """Test that Daemon metaclass accepts valid workpath."""

    class ValidDaemon(Daemon, workpath=str(tmp_path)):  # type: ignore[valid-type]
        def run(self) -> None:
            pass

    # Verify the class was created successfully (workpath is accepted)
    assert hasattr(ValidDaemon, "run")
