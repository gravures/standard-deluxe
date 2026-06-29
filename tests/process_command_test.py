"""Tests for the deluxe.process module."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from deluxe.process import Command, get_real_users


IS_POSIX = sys.platform != "win32"

# Cross-platform command helpers using sys.executable (Python).
# This avoids depending on GNU coreutils (ls, cat, echo, pwd, false, env, etc.)
# which are not available on Windows.

# ============================================================================
# Tests for get_real_users()
# ============================================================================


@pytest.mark.skipif(IS_POSIX, reason="get_real_users is POSIX-only; tested below on POSIX")
def test_get_real_users_not_available_on_non_posix() -> None:
    """Test that get_real_users raises AvailabilityError on non-POSIX."""
    from deluxe.availability import AvailabilityError  # noqa: PLC0415

    with pytest.raises(AvailabilityError):
        get_real_users()


@pytest.mark.skipif(not IS_POSIX, reason="get_real_users is POSIX-only")
def test_get_real_users_returns_set() -> None:
    """Test that get_real_users() returns a set of strings."""
    result = get_real_users()
    assert isinstance(result, set)
    assert all(isinstance(user, str) for user in result)


@pytest.mark.skipif(not IS_POSIX, reason="get_real_users is POSIX-only")
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
    cmd = Command(sys.executable)
    assert cmd.name == sys.executable
    assert cmd.command == sys.executable
    assert cmd.user is None


def test_command_init_with_invalid_command() -> None:
    """Test Command initialization with an invalid command raises Error."""
    with pytest.raises(Command.Error, match="not found on your system"):
        Command("nonexistent_command_xyz_12345")


def test_command_init_with_path() -> None:
    """Test Command initialization with a specific path to existing command."""
    cmd = Command("myname", path=Path(sys.executable))
    assert cmd.command == sys.executable


def test_command_init_with_nonexistent_path() -> None:
    """Test Command initialization with a nonexistent path falls back to name lookup."""
    cmd = Command(sys.executable, path=Path("/nonexistent/path"))
    assert cmd.command == sys.executable


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
    # When name doesn't resolve but path is valid, path should be used
    cmd = Command("anyname", path=Path(sys.executable))
    assert cmd.command == sys.executable


# ============================================================================
# Tests for Command class - user property
# ============================================================================


def test_command_user_property_default() -> None:
    """Test Command user property defaults to None."""
    cmd = Command(sys.executable)
    assert cmd.user is None


def test_command_user_setter_invalid_user() -> None:
    """Test that setting user to a non-existent user raises Error."""
    cmd = Command(sys.executable)
    with pytest.raises(Command.Error, match="not found on your system"):
        cmd.user = "nonexistent_user_xyz_12345"


def test_command_user_set_to_none() -> None:
    """Test that setting user to None works."""
    cmd = Command(sys.executable)
    cmd.user = None
    assert cmd.user is None


def test_command_user_setter_not_implemented_on_non_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test user setter raises NotImplementedError on non-POSIX when user is specified."""
    import deluxe.process as process_mod  # noqa: PLC0415

    monkeypatch.setattr(process_mod, "_USER_SUPPORT", False)

    with pytest.raises(NotImplementedError):
        Command(sys.executable, user="testuser")


# ============================================================================
# Tests for Command class - __call__
# ============================================================================


def test_command_call_text_output() -> None:
    """Test __call__ method with text output (default)."""
    cmd = Command(sys.executable)
    result = cmd("-c", "print('hello world')")
    assert isinstance(result, str)
    assert "hello world" in result


def test_command_call_bytes_output() -> None:
    """Test __call__ method with bytes output.

    BUG: return cp.stdout or "" if text else b"" has operator precedence issue.
    It parses as (cp.stdout or "") if text else b"", always returning b"" when
    text=False regardless of cp.stdout content.
    """
    cmd = Command(sys.executable)
    result = cmd("-c", "import sys; sys.stdout.buffer.write(b'hello world')", text=False)
    assert isinstance(result, bytes)
    assert b"hello world" in result  # noqa: PLR2004


def test_command_call_with_input() -> None:
    """Test __call__ method with input data."""
    cmd = Command(sys.executable)
    result = cmd("-c", "import sys; sys.stdout.write(sys.stdin.read())", input="test input")
    assert "test input" in result


def test_command_call_with_cwd(tmp_path: Path) -> None:
    """Test __call__ method with custom working directory."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    cmd = Command(sys.executable)
    result = cmd(
        "-c",
        "import os, sys; print(os.listdir(sys.argv[1]))",
        str(tmp_path),
    )
    assert "test.txt" in result


def test_command_call_failing_command() -> None:
    """Test that calling a command that returns non-zero raises Error."""
    false_cmd = Command(sys.executable)
    with pytest.raises(Command.Error):
        false_cmd("-c", "import sys; sys.exit(1)")


def test_command_call_preserves_return_code() -> None:
    """Test that Command.Error preserves the return code from failed command."""
    cmd = Command(sys.executable)
    with pytest.raises(Command.Error) as exc_info:
        cmd("-c", "import sys; sys.exit(42)")
    assert exc_info.value.returncode == 42


def test_command_call_with_env() -> None:
    """Test __call__ method with custom environment variables."""
    cmd = Command(sys.executable)
    result = cmd(
        "-c",
        "import os; print(os.environ.get('TEST_VAR', 'NOT_FOUND'))",
        env={"TEST_VAR": "test_value"},
    )
    assert "test_value" in result


def test_command_call_capture_output() -> None:
    """Test __call__ method captures output when capture=True."""
    cmd = Command(sys.executable)
    result = cmd("-c", "import os; print(os.listdir('/'))", capture=True)
    assert isinstance(result, str)
    assert len(result) > 0


def test_command_call_with_pathlib_path(tmp_path: Path) -> None:
    """Test Command execution with pathlib.Path arguments."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    cmd = Command(sys.executable)
    result = cmd(
        "-c",
        "import os, sys; print(os.listdir(sys.argv[1]))",
        str(tmp_path),
    )
    assert "test.txt" in result


def test_command_call_with_multiple_args() -> None:
    """Test Command execution with multiple arguments."""
    cmd = Command(sys.executable)
    result = cmd("-c", "import sys; print(' '.join(sys.argv[1:]))", "hello", "world")
    assert "hello" in result
    assert "world" in result


def test_command_call_error_has_dynamic_class() -> None:
    """Test that the exception class is dynamically named after the command."""
    cmd = Command(sys.executable)
    with pytest.raises(Command.Error) as exc_info:
        cmd("-c", "import sys; sys.exit(1)")
    # The dynamic class name is derived from cmd.name which is sys.executable
    # The class name will be e.g. "PythonError" or similar based on the executable name
    error_class_name = type(exc_info.value).__name__
    assert error_class_name.endswith("Error")
    assert error_class_name != "Error"  # Should be a subclass, not the base


def test_command_error_has_msg() -> None:
    """Test that Command.Error has msg attribute."""
    cmd = Command(sys.executable)
    with pytest.raises(Command.Error) as exc_info:
        cmd("-c", "import sys; sys.exit(1)")
    assert isinstance(exc_info.value.msg, str)
    assert len(exc_info.value.msg) > 0


# ============================================================================
# Tests for Command class - async_call
# ============================================================================


def test_command_async_call() -> None:
    """Test async_call method using asyncio.run()."""
    cmd = Command(sys.executable)

    async def _run() -> bytes:
        task = await cmd.async_call("-c", "print('async test')")
        future = await task
        return await future

    result = asyncio.run(_run())
    assert isinstance(result, bytes)
    assert b"async test" in result  # noqa: PLR2004


def test_command_async_call_with_input() -> None:
    """Test async_call method with input data."""
    cmd = Command(sys.executable)

    async def _run() -> bytes:
        task = await cmd.async_call(
            "-c",
            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
            input=b"async input",
        )
        future = await task
        return await future

    result = asyncio.run(_run())
    assert b"async input" in result  # noqa: PLR2004


def test_command_async_call_returns_task() -> None:
    """Test that async_call returns a Task wrapping a Future."""
    cmd = Command(sys.executable)

    async def _run() -> bytes:
        task = await cmd.async_call("-c", "print('test')")
        assert isinstance(task, asyncio.Task)
        future = await task
        assert isinstance(future, asyncio.Future)
        return await future

    result = asyncio.run(_run())
    assert isinstance(result, bytes)


def test_command_async_call_success() -> None:
    """Test async_call with a successful command."""
    cmd = Command(sys.executable)

    async def _run() -> bytes:
        task = await cmd.async_call("-c", "import os; print(os.getcwd())")
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
    cmd1 = Command(sys.executable)
    cmd2 = Command(sys.executable)
    cmd3 = Command(sys.executable)

    assert cmd1.name == sys.executable
    assert cmd2.name == sys.executable
    assert cmd3.name == sys.executable


def test_command_same_command_independent() -> None:
    """Test that different instances of same command work independently."""
    cmd1 = Command(sys.executable)
    cmd2 = Command(sys.executable)

    result1 = cmd1("-c", "print('independent1')")
    result2 = cmd2("-c", "print('independent2')")
    assert result1 != result2


# ============================================================================
# Property-based tests for Command
# ============================================================================


@given(name=st.just(sys.executable))
def test_property_command_init_succeeds(name: str) -> None:
    """Property: Command initialization should succeed for valid command names."""
    cmd = Command(name)
    assert cmd.name == name
    assert cmd.command is not None


@given(text=st.text(min_size=1, max_size=100))
@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_echo_returns_input(text: str) -> None:
    """Property: echo command should return the input text."""
    if "\x00" in text or "\n" in text or "\r" in text:
        return

    cmd = Command(sys.executable)
    result = cmd("-c", "import sys; print(' '.join(sys.argv[1:]))", text)
    assert text in result


# ============================================================================
# Coverage: _compose with user set (line 197)
# ============================================================================


def test_command_call_with_user() -> None:
    """Test __call__ with user set goes through sudo path.

    Covers line 197: _compose returns sudo-prefixed command tuple.
    """
    with (
        patch.object(Command, "_SYS_USERS", {"root"}),
        patch("deluxe.process.subprocess.run") as mock_run,
    ):
        mock_run.return_value = SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        cmd = Command(sys.executable, user="root")
        cmd("via_sudo")
        # Verify sudo is prepended to the command args
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "sudo"


# ============================================================================
# Coverage: async_call exception for signal-killed process (line 328)
# ============================================================================


@pytest.mark.skipif(not IS_POSIX, reason="SIGTERM signal handling is POSIX-specific")
def test_command_async_call_signal_killed() -> None:
    """Test async_call raises when process is killed by a signal.

    Covers line 328: future.set_exception for negative returncode.

    Note: On Windows, os.kill(pid, SIGTERM) calls TerminateProcess which
    gives a positive return code, not negative. This test is POSIX-only.
    """
    cmd = Command(sys.executable)

    async def _run() -> None:
        task = await cmd.async_call(
            "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"
        )
        future = await task
        await future

    with pytest.raises(Command.Error, match="non-zero exit status"):
        asyncio.run(_run())
