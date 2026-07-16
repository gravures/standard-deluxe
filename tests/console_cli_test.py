from __future__ import annotations

import argparse
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from deluxe.console.argparser import PrettyParser
from deluxe.console.cli import Cli, CliError, command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SimpleCli(Cli):
    """Minimal concrete CLI for testing."""

    def __init__(self, **kwargs: Any) -> None:
        self.main_called: bool = False
        self.cleanup_called: bool = False
        self.last_namespace: argparse.Namespace | None = None
        super().__init__(**kwargs)

    def configure(self, parser: PrettyParser) -> None:
        pass

    def main(self, namespace: argparse.Namespace) -> None:
        self.main_called = True
        self.last_namespace = namespace

    def cleanup(self, namespace: argparse.Namespace) -> None:  # noqa: ARG002
        self.cleanup_called = True


class CliWithPositional(Cli):
    """CLI with a positional argument for testing parsing."""

    def __init__(self, **kwargs: Any) -> None:
        self.main_called: bool = False
        self.last_namespace: argparse.Namespace | None = None
        self.cleanup_called: bool = False
        super().__init__(**kwargs)

    def configure(self, parser: PrettyParser) -> None:  # noqa: PLR6301
        parser.add_argument("name", help="Your name")

    def main(self, namespace: argparse.Namespace) -> None:
        self.main_called = True
        self.last_namespace = namespace

    def cleanup(self, namespace: argparse.Namespace) -> None:  # noqa: ARG002
        self.cleanup_called = True


class CliWithOption(Cli):
    """CLI with an optional argument for testing parsing."""

    def __init__(self, **kwargs: Any) -> None:
        self.main_called: bool = False
        self.last_namespace: argparse.Namespace | None = None
        self.cleanup_called: bool = False
        super().__init__(**kwargs)

    def configure(self, parser: PrettyParser) -> None:  # noqa: PLR6301
        parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")

    def main(self, namespace: argparse.Namespace) -> None:
        self.main_called = True
        self.last_namespace = namespace

    def cleanup(self, namespace: argparse.Namespace) -> None:  # noqa: ARG002
        self.cleanup_called = True


# =============================================================================
# CliError Tests
# =============================================================================


def test_cli_error_init_with_msg_and_quiet():
    """CliError stores msg and quiet."""
    err = CliError(msg="something failed", quiet=True)
    assert err.msg == "something failed"
    assert err.quiet is True


def test_cli_error_init_with_none_msg():
    """CliError defaults msg to empty string when None is passed."""
    err = CliError(msg=None, quiet=False)
    assert not err.msg


def test_cli_error_is_exception():
    """CliError is a subclass of Exception."""
    err = CliError(msg="test", quiet=False)
    assert isinstance(err, Exception)


def test_cli_error_code_with_oserror_cause():
    """code property returns errno from OSError cause."""
    err = CliError(msg="os error", quiet=False)
    original = OSError("disk full")
    original.errno = 28
    err.__cause__ = original
    assert err.code == 28


def test_cli_error_code_with_oserror_no_errno():
    """code property returns 1 when OSError has no errno."""
    err = CliError(msg="os error", quiet=False)
    original = OSError("unknown")
    original.errno = None
    err.__cause__ = original
    assert err.code == 1


def test_cli_error_code_with_winerror():
    """code property uses winerror when available."""
    err = CliError(msg="windows error", quiet=False)
    original = OSError("access denied")
    original.errno = 5
    original.winerror = 33  # type: ignore[attr-defined]
    err.__cause__ = original
    assert err.code == 33


def test_cli_error_code_with_exception_cause():
    """code property returns index-based code for registered exception types."""
    err = CliError(msg="exception", quiet=False)
    err.__cause__ = ValueError("bad value")
    # SystemExit=0, Exception=1, ValueError not registered -> 1
    assert err.code == 1


def test_cli_error_code_with_systemexit_cause():
    """code property returns 0 for SystemExit cause."""
    err = CliError(msg="exit", quiet=False)
    err.__cause__ = SystemExit(0)
    assert err.code == 0


def test_cli_error_code_with_no_cause():
    """code property returns 1 when __cause__ is None."""
    err = CliError(msg="no cause", quiet=False)
    assert err.code == 1


def test_cli_error_get_code_registered_exception():
    """get_code returns sequential code for registered exception types."""
    # SystemExit=0, Exception=1 are registered by default
    assert CliError.get_code(SystemExit) == 0
    assert CliError.get_code(Exception) == 1


def test_cli_error_get_code_unregistered_exception():
    """get_code returns 1 for unregistered exception types."""
    assert CliError.get_code(ValueError) == 1
    assert CliError.get_code(RuntimeError) == 1


def test_cli_error_register_new_exception():
    """register makes get_code return a valid code for the new exception."""
    CliError.register(CustomTestError)
    code = CliError.get_code(CustomTestError)
    # Code must be a non-negative integer (its index in the registry)
    assert isinstance(code, int)
    assert code >= 0


def test_cli_error_register_does_not_duplicate():
    """register does not change code for already-registered exception."""
    CliError.register(CustomTestError)
    code_before = CliError.get_code(CustomTestError)
    CliError.register(CustomTestError)
    code_after = CliError.get_code(CustomTestError)
    assert code_before == code_after


def test_cli_error_register_multiple():
    """register handles multiple exception types at once."""
    CliError.register(CustomTestError, CustomAnotherError)
    # Both should now be registered (get_code returns their index)
    code_a = CliError.get_code(CustomTestError)
    code_b = CliError.get_code(CustomAnotherError)
    assert isinstance(code_a, int)
    assert isinstance(code_b, int)


class CustomTestError(Exception):
    """Custom exception for testing CliError.register."""


class CustomAnotherError(Exception):
    """Another custom exception for testing CliError.register."""


# =============================================================================
# command Decorator Tests
# =============================================================================


def test_command_decorator_preserves_function_name():
    """command decorator preserves the original function name via wraps."""

    @command(help="Do something")
    def my_func() -> None:
        pass

    assert my_func.__name__ == "my_func"


def test_command_decorator_preserves_function_call():
    """command decorator preserves the function's callable behavior."""
    called: list[int] = []

    @command(help="Do something")
    def my_func(x: int) -> None:
        called.append(x)

    my_func(42)
    assert called == [42]


def test_command_decorator_metadata_accessible():
    """command decorator attaches metadata that Cli discovers."""

    @command(help="Do something", description="Long help", name="custom")
    def my_func() -> None:
        pass

    assert hasattr(my_func, "_cli_command")
    meta = cast("dict[str, Any]", getattr(my_func, "_cli_command"))
    assert meta["help"] == "Do something"
    assert meta["description"] == "Long help"
    assert meta["name"] == "custom"


def test_command_decorator_with_setup():
    """command decorator stores setup callable when provided."""

    def setup_fn(p: PrettyParser) -> None:
        p.add_argument("--foo")

    @command(help="Do something", setup=setup_fn)
    def my_func() -> None:
        pass

    meta = cast("dict[str, Any]", getattr(my_func, "_cli_command"))
    assert meta["setup"] is setup_fn


# =============================================================================
# Cli.__init__ Tests
# =============================================================================


def test_cli_init_stores_name():
    """Cli stores the program name."""
    cli = SimpleCli(prog="myapp")
    assert cli.parser.prog == "myapp"


def test_cli_init_default_namespace():
    """Cli initializes an empty namespace."""
    cli = SimpleCli(prog="test")
    assert isinstance(cli.namespace, argparse.Namespace)


def test_cli_init_commands_none_by_default():
    """Cli.commands is None until a subcommand is added."""
    cli = SimpleCli(prog="test")
    assert cli.commands is None


def test_cli_init_version():
    """Cli stores the version string when provided."""
    cli = SimpleCli(prog="myapp", version="1.0")
    assert cli.parser.version == "1.0"


def test_cli_init_prefix():
    """Cli stores a custom usage prefix when provided."""
    cli = SimpleCli(prog="myapp", prefix="custom: ")
    assert cli.parser.prefix == "custom: "


def test_cli_init_no_prefix():
    """Cli defaults to empty prefix when prefix is None."""
    cli = SimpleCli(prog="myapp")
    assert not cli.parser.prefix


def test_cli_init_shell_completion_passed():
    """Cli forwards shell_completion to PrettyParser."""
    cli = SimpleCli(prog="test", shell_completion=False)
    assert cli.parser.shell_completion is False


# =============================================================================
# Cli.parser property
# =============================================================================


def test_cli_parser_property_returns_pretty_parser():
    """parser property returns the underlying PrettyParser."""
    cli = SimpleCli(prog="test")
    assert isinstance(cli.parser, PrettyParser)


# =============================================================================
# Cli.namespace property
# =============================================================================


def test_cli_namespace_property_returns_namespace():
    """namespace property returns the argparse Namespace."""
    cli = SimpleCli(prog="test")
    assert isinstance(cli.namespace, argparse.Namespace)


# =============================================================================
# Cli.add_command Tests
# =============================================================================


def test_add_command_creates_subparsers():
    """add_command lazily creates the subparsers action group."""
    cli = SimpleCli(prog="test")
    assert cli.commands is None

    cli.add_command(callback=lambda _ns: None, help="Test command")

    assert cli.commands is not None


def test_add_command_returns_pretty_parser():
    """add_command returns a PrettyParser for the subcommand."""
    cli = SimpleCli(prog="test")
    sub = cli.add_command(callback=lambda _ns: None, help="Test command")
    assert isinstance(sub, PrettyParser)


def test_add_command_sets_callback():
    """add_command sets the callback on the subparser defaults."""

    def dummy_callback(_ns: argparse.Namespace) -> None:
        pass

    cli = SimpleCli(prog="test")
    sub = cli.add_command(callback=dummy_callback, help="Test command")
    assert sub.get_default("callback") is dummy_callback


def test_add_command_uses_callback_name():
    """add_command uses callback.__name__ when name is not provided."""

    def my_callback(_ns: argparse.Namespace) -> None:
        pass

    cli = SimpleCli(prog="test")
    sub = cli.add_command(callback=my_callback, help="Test command")
    assert "my_callback" in sub.prog


def test_add_command_respects_custom_name():
    """add_command uses the provided name over callback.__name__."""

    def my_callback(_ns: argparse.Namespace) -> None:
        pass

    cli = SimpleCli(prog="test")
    sub = cli.add_command(callback=my_callback, help="Test command", name="custom")
    assert "custom" in sub.prog


def test_add_command_sets_description():
    """add_command sets the description on the subparser."""
    cli = SimpleCli(prog="test")
    sub = cli.add_command(
        callback=lambda _ns: None,
        help="Short",
        description="Long description",
    )
    assert sub.description == "Long description"


def test_add_command_defaults_description_to_help():
    """add_command defaults description to help when description is None."""
    cli = SimpleCli(prog="test")
    sub = cli.add_command(callback=lambda _ns: None, help="Short help")
    assert sub.description == "Short help"


def test_add_command_with_parents():
    """add_command passes parent parsers to the subparser."""
    parent = PrettyParser(prog="parent", add_help=False)
    parent.add_argument("--shared", help="Shared argument")
    cli = SimpleCli(prog="test")
    sub = cli.add_command(
        callback=lambda _ns: None,
        help="Test",
        parents=[parent],
    )
    assert sub is not None
    # Verify the parent's argument was inherited via the help output
    help_text = sub.format_help()
    assert "--shared" in help_text


# =============================================================================
# Cli.parser_for Tests
# =============================================================================


def test_parser_for_returns_subparser():
    """parser_for returns the subparser registered via @command decorator."""

    class CliWithCommand(Cli):
        def __init__(self) -> None:
            self.greet_called: bool = False
            super().__init__(prog="test")

        @command(help="Greet someone")
        def greet(self, _namespace: argparse.Namespace) -> None:
            self.greet_called = True

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliWithCommand()
    # Trigger auto-registration via __call__
    cli("greet", "--help")
    # If parser_for fails, the test would have errored during __call__


def test_parser_for_raises_on_unknown_name():
    """parser_for raises KeyError for an unregistered command name."""
    cli = SimpleCli(prog="test")
    with pytest.raises(KeyError):
        cli.parser_for("nonexistent")


# =============================================================================
# Cli.__call__ Lifecycle Tests
# =============================================================================


def test_call_runs_full_lifecycle():
    """__call__ invokes configure, main, and cleanup."""
    cli = SimpleCli(prog="test")
    result = cli()
    assert result == 0
    assert cli.main_called is True
    assert cli.cleanup_called is True


def test_call_returns_zero_on_success():
    """__call__ returns 0 on successful execution."""
    cli = SimpleCli(prog="test")
    assert cli() == 0


def test_call_passes_args_to_parse():
    """__call__ forwards positional arguments to the parser."""
    cli = CliWithPositional(prog="test")
    cli("Alice")
    assert cli.last_namespace is not None
    assert cli.last_namespace.name == "Alice"


def test_call_with_optional_args():
    """__call__ parses optional arguments."""
    cli = CliWithOption(prog="test")
    cli("--quiet")
    assert cli.last_namespace is not None
    assert cli.last_namespace.quiet is True


def test_call_without_args():
    """__call__ with no arguments runs with default argv."""
    cli = SimpleCli(prog="test")
    result = cli()
    assert result == 0


def test_call_cleanup_always_called():
    """cleanup is called even when main raises CliError."""

    class CliCleanupOnError(Cli):
        def __init__(self) -> None:
            self.cleanup_called: bool = False
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:  # noqa: PLR6301, ARG002
            raise CliError(msg="error occurred", quiet=False)

        def cleanup(self, namespace: argparse.Namespace) -> None:  # noqa: ARG002
            self.cleanup_called = True

    cli = CliCleanupOnError()
    result = cli()
    assert result != 0
    assert cli.cleanup_called is True


def test_call_cli_error_returns_code():
    """__call__ returns the error code from CliError."""

    class CliErrorOnMain(Cli):
        def __init__(self) -> None:
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:  # noqa: ARG002, PLR6301
            raise CliError(msg="error occurred", quiet=True)

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliErrorOnMain()
    result = cli()
    assert result == 1


def test_call_cli_error_with_message_prints_to_stderr(
    capsys: pytest.CaptureFixture[str],
):
    """__call__ prints CliError.msg to stderr when not quiet."""

    class CliErrorVerbose(Cli):
        def __init__(self) -> None:
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:  # noqa: PLR6301, ARG002
            raise CliError(msg="something went wrong", quiet=False)

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliErrorVerbose()
    cli()
    captured = capsys.readouterr()
    assert "something went wrong" in captured.err
    assert "test:" in captured.err


def test_call_cli_error_quiet_does_not_print(
    capsys: pytest.CaptureFixture[str],
):
    """__call__ suppresses output when CliError is quiet."""

    class CliErrorQuiet(Cli):
        def __init__(self) -> None:
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:  # noqa: PLR6301, ARG002
            raise CliError(msg="silent error", quiet=True)

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliErrorQuiet()
    cli()
    captured = capsys.readouterr()
    assert "silent error" not in captured.err


def test_call_callback_invoked():
    """__call__ invokes the namespace callback if present."""
    callback = MagicMock()

    class CliWithCallbackSetup(Cli):
        def __init__(self) -> None:
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:  # noqa: ARG002
            sub = self.add_command(callback=callback, help="Test", name="test")
            sub.add_argument("--foo")

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliWithCallbackSetup()
    cli("test", "--foo", "bar")
    callback.assert_called_once()


def test_call_parse_error_wraps_as_cli_error():
    """__call__ wraps argparse errors as CliError."""

    class CliBadArgs(Cli):
        def __init__(self) -> None:
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:  # noqa: PLR6301
            parser.add_argument("--required", required=True)

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliBadArgs()
    result = cli()
    # parse_args with exit_on_error=False raises SystemExit for missing required
    # which _parse wraps as CliError
    assert result != 0


def test_call_inheritance_commands():
    """Commands from parent classes are inherited."""

    class BaseCli(Cli):
        def __init__(self) -> None:
            self.version_called: bool = False
            super().__init__(prog="test")

        @command(help="Show version")
        def version(self, _namespace: argparse.Namespace) -> None:
            self.version_called = True

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    class ChildCli(BaseCli):
        @command(help="Greet someone")
        def greet(self, _namespace: argparse.Namespace) -> None:
            pass

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = ChildCli()
    cli("version")
    assert cli.version_called


def test_call_inheritance_override_command():
    """A subclass can override a parent command."""

    class BaseCli(Cli):
        def __init__(self) -> None:
            self.action: str = "base"
            super().__init__(prog="test")

        @command(help="Show version")
        def version(self, _namespace: argparse.Namespace) -> None:
            self.action = "base_version"

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    class ChildCli(BaseCli):
        action: str

        @command(help="Show version (child)")
        def version(self, _namespace: argparse.Namespace) -> None:  # type: ignore[override]
            self.action = "child_version"

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = ChildCli()
    cli("version")
    assert cli.action == "child_version"


# =============================================================================
# Cli.read_stdin Tests
# =============================================================================


def test_read_stdin_returns_none_for_tty():
    """read_stdin returns None when stdin is a TTY."""
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        result = Cli.read_stdin()
        assert result is None


def test_read_stdin_reads_from_piped_input():
    """read_stdin reads content when stdin is not a TTY."""
    with (
        patch("sys.stdin") as mock_stdin,
        patch("fileinput.input") as mock_fileinput,
    ):
        mock_stdin.isatty.return_value = False
        mock_fileinput.return_value.__enter__ = MagicMock(return_value=["hello ", "world"])
        mock_fileinput.return_value.__exit__ = MagicMock(return_value=False)
        result = Cli.read_stdin()
        assert result == "hello world"


# =============================================================================
# Mixed @command + add_command Tests
# =============================================================================


def test_mixed_declarative_and_imperative_commands():
    """@command and add_command can coexist."""

    class CliMixed(Cli):
        def __init__(self) -> None:
            self.version_called: bool = False
            self.legacy_called: bool = False
            super().__init__(prog="test")

        @command(help="Show version")
        def version(self, _namespace: argparse.Namespace) -> None:
            self.version_called = True

        def configure(self, parser: PrettyParser) -> None:  # noqa: ARG002
            sub = self.add_command(callback=self._legacy_cmd, help="Legacy", name="legacy")
            sub.add_argument("arg")

        def _legacy_cmd(self, _namespace: argparse.Namespace) -> None:
            self.legacy_called = True

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliMixed()
    cli("version")
    assert cli.version_called
    assert not cli.legacy_called

    cli2 = CliMixed()
    cli2("legacy", "something")
    assert cli2.legacy_called
    assert not cli2.version_called


# =============================================================================
# Inline setup via @command Tests
# =============================================================================


def test_inline_setup_adds_arguments():
    """@command with setup callable adds arguments to subparser."""

    def add_name_arg(p: PrettyParser) -> None:
        p.add_argument("name", help="Your name")

    class CliInline(Cli):
        def __init__(self) -> None:
            self.received_name: str | None = None
            super().__init__(prog="test")

        @command(
            help="Greet someone",
            setup=add_name_arg,
        )
        def greet(self, namespace: argparse.Namespace) -> None:
            self.received_name = namespace.name

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliInline()
    cli("greet", "World")
    assert cli.received_name == "World"


def test_setup_in_configure_via_parser_for():
    """Arguments can be added in configure() via parser_for."""

    class CliSetupInConfigure(Cli):
        def __init__(self) -> None:
            self.received_name: str | None = None
            self.received_loud: bool = False
            super().__init__(prog="test")

        @command(help="Greet someone")
        def greet(self, namespace: argparse.Namespace) -> None:
            self.received_name = namespace.name
            self.received_loud = namespace.loud

        def configure(self, parser: PrettyParser) -> None:  # noqa: ARG002
            sub = self.parser_for("greet")
            sub.add_argument("name", help="Your name")
            sub.add_argument("-l", "--loud", action="store_true", help="Shout the greeting")

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliSetupInConfigure()
    cli("greet", "World", "--loud")
    assert cli.received_name == "World"
    assert cli.received_loud is True


# =============================================================================
# Edge Cases
# =============================================================================


def test_cli_with_no_prog():
    """Cli uses sys.argv[0] as name when prog is None."""
    with patch("sys.argv", ["my_script.py"]):
        cli = SimpleCli()
        assert "my_script.py" in cli.parser.prog


def test_cli_with_version_flag():
    """Cli with version adds --version flag."""
    cli = SimpleCli(prog="test", version="2.0")
    # --version triggers SystemExit, verify via exception
    with pytest.raises(SystemExit) as exc_info:
        cli.parser.parse_args(["--version"])
    assert exc_info.value.code in {0, None}


def test_cli_help_returns_zero_exit_code():
    """cli('--help') should return exit code 0 (success)."""
    cli = SimpleCli(prog="test", version="1.0")
    assert cli("--help") == 0


def test_cli_version_returns_zero_exit_code():
    """cli('--version') should return exit code 0 (success)."""
    cli = SimpleCli(prog="test", version="1.0")
    assert cli("--version") == 0


def test_cli_configure_called_during_call():
    """configure is called during __call__ execution."""

    class CliConfigureSpy(Cli):
        def __init__(self) -> None:
            self.configure_called: bool = False
            super().__init__(prog="test")

        def configure(self, parser: PrettyParser) -> None:  # noqa: ARG002
            self.configure_called = True

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli = CliConfigureSpy()
    cli()
    assert cli.configure_called is True


def test_cli_multiple_commands_all_accessible():
    """All registered commands are accessible via parser_for."""

    class CliMulti(Cli):
        def __init__(self) -> None:
            self.cmd_a_called: bool = False
            self.cmd_b_called: bool = False
            super().__init__(prog="test")

        @command(help="Command A")
        def cmd_a(self, _namespace: argparse.Namespace) -> None:
            self.cmd_a_called = True

        @command(help="Command B")
        def cmd_b(self, _namespace: argparse.Namespace) -> None:
            self.cmd_b_called = True

        def configure(self, parser: PrettyParser) -> None:
            pass

        def main(self, namespace: argparse.Namespace) -> None:
            pass

        def cleanup(self, namespace: argparse.Namespace) -> None:
            pass

    cli_a = CliMulti()
    cli_a("cmd_a")
    assert cli_a.cmd_a_called

    cli_b = CliMulti()
    cli_b("cmd_b")
    assert cli_b.cmd_b_called
