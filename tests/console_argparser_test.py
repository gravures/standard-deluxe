from __future__ import annotations

import argparse
import re
from io import StringIO
from typing import Any, TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from deluxe.console.argparser import (
    SHELL_COMPLETION,
    AnsiHelpFormatter,
    ArgumentDefaultsAnsiHelpFormatter,
    PrettyHelpFormatter,
    PrettyParser,
    RawAnsiHelpFormatter,
    RawDescriptionAnsiHelpFormatter,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""  # noqa: DOC201
    return _ANSI_RE.sub("", text)


def _parser(width: int = 80, prog: str = "test", **kwargs: Any) -> PrettyParser:
    """Create a :class:`PrettyParser` that uses a formatter with a fixed *width*.

    ``PrettyParser`` does not forward *width* to the underlying
    ``ArgumentParser``.  We work around this by injecting a custom
    ``formatter_class`` that sets the width at formatter construction time.
    """  # noqa: DOC201

    class _WidthFormatter(PrettyHelpFormatter):
        def __init__(self, **fmt_kwargs: Any) -> None:
            fmt_kwargs.setdefault("width", width)
            super().__init__(**fmt_kwargs)

    return PrettyParser(prog=prog, formatter_class=_WidthFormatter, **kwargs)


# =============================================================================
# AnsiHelpFormatter Tests
# =============================================================================


def test_ansi_help_formatter_styles_dict_has_required_keys():
    """Test that AnsiHelpFormatter.styles contains all required style keys."""
    required_keys = {
        "argparse.args",
        "argparse.groups",
        "argparse.help",
        "argparse.metavar",
        "argparse.syntax",
        "argparse.text",
        "argparse.prog",
        "argparse.default",
    }
    assert required_keys.issubset(set(AnsiHelpFormatter.styles.keys()))


def test_ansi_style_wraps_text_with_ansi_codes():
    """Test that help output contains ANSI escape codes."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert "\x1b[" in help_text


def test_ansi_style_all_styles_produce_valid_escapes():
    """Test that every registered style key produces ANSI escape codes."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert "\x1b[" in help_text


def test_ansi_aware_pad_pads_text_to_width():
    """Test that help text pads arguments to consistent width."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert "Foo help" in help_text


def test_ansi_aware_pad_with_ansi_codes():
    """Test that padding accounts for ANSI escape codes."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert "Foo help" in help_text


def test_fill_text_wraps_long_text():
    """Test that help text wraps long descriptions."""
    parser = _parser(width=40)
    parser.add_argument(
        "--foo",
        help="This is a long help text that should be wrapped to fit within the width",
    )
    help_text = parser.format_help()
    assert "\n" in help_text


def test_fill_text_preserves_indent():
    """Test that help text preserves indentation."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="Short text")
    help_text = parser.format_help()
    assert "Short text" in help_text


def test_format_action_returns_string():
    """Test that format_help contains the argument name."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert "foo" in help_text.lower()


def test_format_action_positional_argument():
    """Test that format_help handles positional arguments."""
    parser = _parser(width=80)
    parser.add_argument("input", help="Input file")
    help_text = parser.format_help()
    assert "input" in help_text.lower()


def test_format_action_no_help_text():
    """Test format_help when argument has no help text."""
    parser = _parser(width=80)
    parser.add_argument("--foo")
    help_text = parser.format_help()
    assert isinstance(help_text, str)


def test_format_action_with_subactions():
    """Test format_help when parser has sub-actions (subparsers)."""
    parser = _parser(width=80)
    subparsers = parser.add_subparsers(dest="command")
    subparser_a = subparsers.add_parser("a", help="Command A")
    subparser_a.add_argument("--foo", help="Foo")
    help_text = parser.format_help()
    assert isinstance(help_text, str)


def test_format_action_long_action_name():
    """Test format_help when action name exceeds action_width."""
    parser = _parser(width=80)
    long_name = "--" + "x" * 60
    parser.add_argument(long_name, help="Help text")
    help_text = parser.format_help()
    assert isinstance(help_text, str)


def test_format_action_invocation_nargs_zero():
    """Test format_help with nargs=0 (store_true)."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--verbose", action="store_true", help="Verbose mode")
    help_text = parser.format_help()
    assert "verbose" in help_text.lower()


def test_format_action_help_empty_after_expand():
    """Test format_help when help expands to empty string."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="%(prog)s")
    help_text = parser.format_help()
    assert isinstance(help_text, str)


def test_format_action_whitespace_only_help():
    """Test format_help when help text is whitespace-only."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="   ")
    help_text = parser.format_help()
    assert isinstance(help_text, str)


def test_add_argument_updates_action_max_length():
    """Test that multiple arguments are all present in help."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--short", help="Short")
    parser.add_argument("--very-long-option-name", help="Long")
    help_text = parser.format_help()
    assert "Short" in help_text
    assert "Long" in help_text


def test_add_argument_suppress_help_does_not_update_max_length():
    """Test that SUPPRESS help hides the argument from help."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--visible", help="Visible help")
    parser.add_argument("--hidden", help=argparse.SUPPRESS)
    help_text = parser.format_help()
    assert "Visible help" in help_text


def test_get_default_metavar_for_optional_returns_styled_dest():
    """Test that optional argument metavar is uppercase in help."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo")
    help_text = parser.format_help()
    assert "FOO" in _strip_ansi(help_text)


def test_get_default_metavar_for_positional_returns_styled_dest():
    """Test that positional argument metavar is present in help."""
    parser = PrettyParser(prog="test")
    parser.add_argument("foo")
    help_text = parser.format_help()
    assert "foo" in _strip_ansi(help_text)


def test_expand_help_returns_help_string():
    """Test that help text includes the help string."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help text")
    help_text = parser.format_help()
    assert "Foo help text" in help_text


def test_expand_help_with_choices():
    """Test that help text includes choices."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--mode", choices=["fast", "slow"], help="Mode: %(choices)s")
    help_text = parser.format_help()
    assert "fast" in _strip_ansi(help_text)
    assert "slow" in _strip_ansi(help_text)


def test_expand_help_with_default_value():
    """Test that help text includes default value."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", default="bar", help="Foo help (default: %(default)s)")
    help_text = parser.format_help()
    assert "bar" in help_text


def test_section_format_help_returns_string():
    """Test that sections produce formatted help text."""
    parser = PrettyParser(prog="test", description="Test Section")
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert isinstance(help_text, str)


def test_section_format_help_with_parent():
    """Test that help text contains description and epilog."""
    parser = PrettyParser(prog="test", description="Parent", epilog="Child")
    parser.add_argument("--foo", help="Foo help")
    help_text = parser.format_help()
    assert "Parent" in help_text
    assert "Child" in help_text


def test_section_format_help_empty_section():
    """Test that help text is produced even with no description/epilog."""
    parser = PrettyParser(prog="test")
    help_text = parser.format_help()
    assert "usage:" in help_text.lower()


def test_section_with_suppress_heading():
    """Test help output when argument help is suppressed."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help=argparse.SUPPRESS)
    help_text = parser.format_help()
    stripped = _strip_ansi(help_text).lower()
    # SUPPRESS hides the help text but the argument may still appear in usage
    assert "foo" not in stripped or "usage:" in stripped


# =============================================================================
# format_usage — tests via public API
# =============================================================================


def test_format_usage_with_explicit_usage():
    """Test that format_usage uses the provided usage string."""
    parser = PrettyParser(prog="test", usage="custom usage: %(prog)s")
    usage = parser.format_usage()
    assert "custom usage: test" in usage


def test_format_usage_with_no_actions():
    """Test that format_usage handles empty actions list."""
    parser = PrettyParser(prog="test")
    usage = parser.format_usage()
    assert "test" in usage
    assert "usage:" in usage.lower()


def test_format_usage_explicit_usage_with_prog():
    """Test format_usage with explicit usage containing %(prog)s."""
    parser = PrettyParser(prog="myapp", usage="Usage: %(prog)s do something")
    usage = parser.format_usage()
    assert "Usage: myapp do something" in usage


def test_format_usage_auto_generated_no_actions():
    """Test format_usage auto-generated, no actions."""
    parser = _parser(width=80)
    usage = parser.format_usage()
    assert "usage:" in usage.lower()
    assert "test" in usage


def test_format_usage_auto_generated_short_usage():
    """Test format_usage auto-generated usage fits in one line."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="Foo help")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()
    assert "test" in usage


def test_format_usage_auto_generated_very_narrow_width():
    """Test format_usage with extremely narrow width to force wrapping."""
    parser = _parser(width=20)
    parser.add_argument("--foo", help="Foo help")
    parser.add_argument("--bar", help="Bar help")
    parser.add_argument("input", help="Input file")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()
    assert "\n" in usage


def test_format_usage_auto_generated_width_10():
    """Test format_usage with width=10 to force wrapping."""
    parser = _parser(width=10, prog="myapp")
    parser.add_argument("--foo", help="Foo help")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()


def test_format_usage_auto_generated_long_prog_wraps():
    """Test format_usage with long prog name triggers long-prog branch."""
    long_prog = "a" * 60
    parser = _parser(width=60, prog=long_prog)
    parser.add_argument("--foo", help="Foo help")
    parser.add_argument("input", help="Input file")
    usage = parser.format_usage()
    assert long_prog in usage


def test_format_usage_auto_generated_long_prog_multiple_lines():
    """Test format_usage with long prog and many args, multi-line split."""
    long_prog = "a" * 60
    parser = _parser(width=60, prog=long_prog)
    parser.add_argument("--foo", help="Foo help")
    parser.add_argument("--bar", help="Bar help")
    parser.add_argument("--baz", help="Baz help")
    parser.add_argument("input", help="Input file")
    parser.add_argument("output", help="Output file")
    usage = parser.format_usage()
    assert long_prog in usage


def test_format_usage_auto_generated_with_mutually_exclusive():
    """Test format_usage with mutually exclusive group."""
    parser = _parser(width=40)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--foo", help="Foo help")
    group.add_argument("--bar", help="Bar help")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()


def test_format_usage_auto_generated_short_prog_positionals_only():
    """Test format_usage with short prog and only positionals."""
    parser = _parser(width=25, prog="t")
    parser.add_argument("input", help="Input file")
    parser.add_argument("output", help="Output file")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()


def test_format_usage_auto_generated_short_prog_only_positionals_narrow():
    """Test format_usage with short prog, positionals only, add_help=False."""
    parser = _parser(width=15, prog="ab", add_help=False)
    parser.add_argument("input", help="Input file")
    parser.add_argument("output", help="Output file")
    parser.add_argument("extra", help="Extra file")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()
    assert "ab" in usage


def test_format_usage_auto_generated_short_prog_no_args_wraps():
    """Test format_usage with short prog and no args at narrow width."""
    parser = _parser(width=3, prog="t")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()


def test_format_usage_auto_generated_long_prog_with_optionals_and_positionals():
    """Test format_usage with long prog, optionals, and positionals."""
    long_prog = "c" * 60
    parser = _parser(width=60, prog=long_prog)
    parser.add_argument("--foo", help="Foo help")
    parser.add_argument("--bar", help="Bar help")
    parser.add_argument("input", help="Input file")
    usage = parser.format_usage()
    assert long_prog in usage


def test_format_usage_auto_generated_long_prog_width_70():
    """Test format_usage with long prog, width=70, many args."""
    long_prog = "d" * 55
    parser = _parser(width=70, prog=long_prog)
    parser.add_argument("--foo", help="Foo help")
    parser.add_argument("--bar", help="Bar help")
    parser.add_argument("input", help="Input file")
    usage = parser.format_usage()
    assert long_prog in usage


def test_format_usage_uses_get_actions_usage_parts():
    """Test format_usage when _get_actions_usage_parts is available."""
    parser = _parser(width=80)
    parser.add_argument("--foo", help="Foo help")
    usage = parser.format_usage()
    assert "usage:" in usage.lower()


# =============================================================================
# Metavar tests — via public format_usage
# =============================================================================


def test_metavar_parts_nargs_none():
    """Test metavar with nargs=None (positional, default)."""
    parser = PrettyParser(prog="test")
    parser.add_argument("foo")
    usage = _strip_ansi(parser.format_usage())
    assert "foo" in usage


def test_metavar_parts_nargs_optional():
    """Test metavar with nargs=OPTIONAL."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.OPTIONAL)
    usage = _strip_ansi(parser.format_usage())
    assert "[FOO]" in usage


def test_metavar_parts_nargs_zero_or_more_with_two_metavars():
    """Test metavar with nargs=ZERO_OR_MORE, two metavars."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.ZERO_OR_MORE, metavar=("A", "B"))
    usage = _strip_ansi(parser.format_usage())
    assert "[A" in usage


def test_metavar_parts_nargs_zero_or_more_with_one_metavar():
    """Test metavar with nargs=ZERO_OR_MORE, one metavar."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.ZERO_OR_MORE, metavar="X")
    usage = _strip_ansi(parser.format_usage())
    assert "[X" in usage


def test_metavar_parts_nargs_one_or_more():
    """Test metavar with nargs=ONE_OR_MORE."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.ONE_OR_MORE, metavar="X")
    usage = _strip_ansi(parser.format_usage())
    assert "[X ..." in usage


def test_metavar_parts_nargs_remainder():
    """Test metavar with nargs=REMAINDER."""
    parser = PrettyParser(prog="test")
    parser.add_argument("foo", nargs=argparse.REMAINDER)
    usage = _strip_ansi(parser.format_usage())
    assert "..." in usage


def test_metavar_parts_nargs_parser():
    """Test metavar with nargs=PARSER."""
    parser = PrettyParser(prog="test")
    parser.add_argument("foo", nargs=argparse.PARSER)
    usage = _strip_ansi(parser.format_usage())
    assert "..." in usage


def test_metavar_parts_nargs_suppress():
    """Test metavar with nargs=SUPPRESS."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.SUPPRESS, help=argparse.SUPPRESS)
    usage = _strip_ansi(parser.format_usage())
    assert "foo" not in usage.lower()


def test_metavar_parts_nargs_numeric():
    """Test metavar with a numeric nargs (e.g. 2)."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=2)
    usage = _strip_ansi(parser.format_usage())
    assert "FOO FOO" in usage


# =============================================================================
# PrettyHelpFormatter Tests
# =============================================================================


def test_pretty_help_formatter_init():
    """Test that PrettyHelpFormatter initializes correctly."""
    formatter = PrettyHelpFormatter(prog="test")
    assert formatter._prog == "test"


def test_pretty_help_formatter_default_width():
    """Test that PrettyHelpFormatter uses default width."""
    formatter = PrettyHelpFormatter(prog="test")
    assert formatter._width > 0


def test_pretty_help_formatter_custom_width():
    """Test that PrettyHelpFormatter respects custom width."""
    formatter = PrettyHelpFormatter(prog="test", width=60)
    assert formatter._width == 60


def test_pretty_help_formatter_metavar_typed_default():
    """Test that metavar_typed defaults to False."""
    formatter = PrettyHelpFormatter(prog="test")
    assert formatter.metavar_typed is False


def test_pretty_help_formatter_get_default_metavar_for_optional_with_typed():
    """Test metavar_typed=True shows type name for optional args."""
    PrettyHelpFormatter.metavar_typed = True
    try:
        parser = PrettyParser(prog="test")
        parser.add_argument("--foo", type=int)
        help_text = _strip_ansi(parser.format_help())
        assert "int" in help_text
    finally:
        PrettyHelpFormatter.metavar_typed = False


def test_pretty_help_formatter_get_default_metavar_for_positional_with_typed():
    """Test metavar_typed=True shows type name for positional args."""
    PrettyHelpFormatter.metavar_typed = True
    try:
        parser = PrettyParser(prog="test")
        parser.add_argument("foo", type=float)
        help_text = _strip_ansi(parser.format_help())
        assert "float" in help_text
    finally:
        PrettyHelpFormatter.metavar_typed = False


def test_pretty_help_formatter_get_default_metavar_for_optional_without_typed():
    """Test metavar_typed=False shows dest name for optional args."""
    PrettyHelpFormatter.metavar_typed = False
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo")
    help_text = _strip_ansi(parser.format_help())
    assert "FOO" in help_text


def test_pretty_help_formatter_metavar_typed_no_type_attribute():
    """Test metavar_typed=True with no type attribute falls back to dest."""
    PrettyHelpFormatter.metavar_typed = True
    try:
        parser = PrettyParser(prog="test")
        parser.add_argument("--foo")
        help_text = _strip_ansi(parser.format_help())
        assert "FOO" in help_text
    finally:
        PrettyHelpFormatter.metavar_typed = False


def test_pretty_help_formatter_metavar_typed_positional_no_type():
    """Test metavar_typed=True positional with no type falls back to dest."""
    PrettyHelpFormatter.metavar_typed = True
    try:
        parser = PrettyParser(prog="test")
        parser.add_argument("foo")
        help_text = _strip_ansi(parser.format_help())
        assert "foo" in help_text
    finally:
        PrettyHelpFormatter.metavar_typed = False


# =============================================================================
# PrettyParser Tests
# =============================================================================


def test_pretty_parser_init():
    """Test that PrettyParser initializes correctly."""
    parser = PrettyParser(prog="test")
    assert parser.prog == "test"
    assert parser.exit_on_error is True
    assert parser.shell_completion is False


def test_pretty_parser_init_with_version():
    """Test that PrettyParser adds version argument when provided."""
    parser = PrettyParser(prog="test", version="1.0.0")
    assert parser.version == "1.0.0"
    assert any("--version" in a.option_strings for a in parser._actions)


def test_pretty_parser_init_without_version():
    """Test that PrettyParser doesn't add version when not provided."""
    parser = PrettyParser(prog="test")
    assert not parser.version
    assert not any("--version" in a.option_strings for a in parser._actions)


def test_pretty_parser_init_with_description():
    """Test that PrettyParser stores description."""
    parser = PrettyParser(prog="test", description="My description")
    assert parser.description == "My description"


def test_pretty_parser_init_with_epilog():
    """Test that PrettyParser stores epilog."""
    parser = PrettyParser(prog="test", epilog="My epilog")
    assert parser.epilog == "My epilog"


def test_pretty_parser_init_with_usage():
    """Test that PrettyParser stores custom usage."""
    parser = PrettyParser(prog="test", usage="custom %(prog)s usage")
    assert parser.usage == "custom %(prog)s usage"


def test_pretty_parser_init_with_prefix():
    """Test that PrettyParser stores prefix."""
    parser = PrettyParser(prog="test", prefix="Custom: ")
    assert parser.prefix == "Custom: "


def test_pretty_parser_init_default_prefix_is_empty():
    """Test that PrettyParser default prefix is empty string."""
    parser = PrettyParser(prog="test")
    assert not parser.prefix


def test_pretty_parser_exit_on_error_true_raises_argument_error():
    """Test that exit raises ArgumentError when status is non-zero."""
    parser = PrettyParser(prog="test", exit_on_error=True)
    with pytest.raises(argparse.ArgumentError):
        parser.exit(1, "error message")


def test_pretty_parser_exit_on_error_zero_raises_system_exit():
    """Test that exit raises SystemExit when status is zero."""
    parser = PrettyParser(prog="test", exit_on_error=True)
    with pytest.raises(SystemExit):
        parser.exit(0, "exit message")


def test_pretty_parser_exit_no_message():
    """Test that exit raises SystemExit with None message."""
    parser = PrettyParser(prog="test")
    with pytest.raises(SystemExit) as exc_info:
        parser.exit(0)
    assert exc_info.value.args[0] is None


def test_pretty_parser_exit_nonzero_no_message():
    """Test exit with non-zero status and no message."""
    parser = PrettyParser(prog="test", exit_on_error=True)
    with pytest.raises(argparse.ArgumentError, match="unknown error"):
        parser.exit(1)


def test_pretty_parser_error_raises_argument_error():
    """Test that error raises ArgumentError with the message."""
    parser = PrettyParser(prog="test", exit_on_error=True)
    with pytest.raises(argparse.ArgumentError, match="test error"):
        parser.error("test error")


def test_pretty_parser_error_exit_on_error_false():
    """Test error() when exit_on_error=False."""
    parser = PrettyParser(prog="test", exit_on_error=False)
    with pytest.raises(argparse.ArgumentError, match="test error"):
        parser.error("test error")


def test_pretty_parser_parse_args_returns_namespace():
    """Test that parse_args returns a Namespace object."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", default="bar")
    result = parser.parse_args([])
    assert result is not None
    assert isinstance(result, argparse.Namespace)
    assert result.foo == "bar"


def test_pretty_parser_parse_args_with_arguments():
    """Test that parse_args correctly parses arguments."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", required=True)
    parser.add_argument("baz")
    result = parser.parse_args(["--foo", "value", "positional"])
    assert result is not None
    assert result.foo == "value"
    assert result.baz == "positional"


def test_pretty_parser_parse_args_with_custom_namespace():
    """Test that parse_args populates custom namespace."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo")
    namespace = argparse.Namespace(bar="existing")
    result = parser.parse_args(["--foo", "value"], namespace)
    assert result is not None
    assert result.foo == "value"
    assert result.bar == "existing"


def test_pretty_parser_shell_completion_default_false():
    """Test that shell_completion defaults to False."""
    parser = PrettyParser(prog="test")
    assert parser.shell_completion is False


def test_pretty_parser_shell_completion_argcomplete_not_found():
    """Test that shell completion is disabled when argcomplete not found."""
    with (
        patch(
            "deluxe.console.argparser.importlib.util.find_spec",
            return_value=None,
        ),
        pytest.warns(ImportWarning, match="auto-completion requested"),
    ):
        parser = PrettyParser(prog="test", shell_completion=True)
    assert parser.shell_completion is False


def test_pretty_parser_shell_completion_argcomplete_found():
    """Test that shell completion is enabled when argcomplete found."""
    mock_argcomplete = MagicMock()
    with (
        patch(
            "deluxe.console.argparser.importlib.util.find_spec",
            return_value=True,
        ),
        patch(
            "deluxe.console.argparser.importlib.import_module",
            return_value=mock_argcomplete,
        ),
    ):
        parser = PrettyParser(prog="test", shell_completion=True)
        assert parser.shell_completion is True
        assert parser.argcomplete is mock_argcomplete
        assert any("--completion" in a.option_strings for a in parser._actions)


def test_pretty_parser_shell_completion_via_parse_args():
    """Test that shell completion raises ArgumentError for invalid shell."""
    mock_argcomplete = MagicMock()
    with (
        patch(
            "deluxe.console.argparser.importlib.util.find_spec",
            return_value=True,
        ),
        patch(
            "deluxe.console.argparser.importlib.import_module",
            return_value=mock_argcomplete,
        ),
    ):
        parser = PrettyParser(prog="test", shell_completion=True, exit_on_error=True)
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(["--completion", "invalid_shell"])


def test_pretty_parser_shell_completion_valid_shell_via_parse_args():
    """Test that shell completion succeeds for a valid shell."""
    mock_argcomplete = MagicMock()
    mock_argcomplete.shell_integration.shellcode.return_value = "# completion script for bash"
    with (
        patch(
            "deluxe.console.argparser.importlib.util.find_spec",
            return_value=True,
        ),
        patch(
            "deluxe.console.argparser.importlib.import_module",
            return_value=mock_argcomplete,
        ),
    ):
        parser = PrettyParser(prog="test", shell_completion=True)
    with patch.object(parser, "exit") as mock_exit:
        parser.parse_args(["--completion", "bash"])
        mock_exit.assert_called_once()


def test_pretty_parser_no_help_argument():
    """Test that PrettyParser can be created without help argument."""
    parser = PrettyParser(prog="test", add_help=False)
    assert not any("--help" in a.option_strings for a in parser._actions)


def test_pretty_parser_custom_prefix_chars():
    """Test that PrettyParser respects custom prefix_chars."""
    parser = PrettyParser(prog="test", prefix_chars="+")
    parser.add_argument("+foo")
    result = parser.parse_args(["+foo", "value"])
    assert result is not None
    assert result.foo == "value"


def test_pretty_parser_conflict_handler_resolve():
    """Test that PrettyParser can resolve conflicts."""
    parser = PrettyParser(prog="test", conflict_handler="resolve")
    parser.add_argument("--foo")
    parser.add_argument("--foo", dest="bar")
    result = parser.parse_args(["--foo", "value"])
    assert result is not None
    assert result.bar == "value"


def test_pretty_parser_with_parents():
    """Test that PrettyParser can use parent parsers."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--parent-arg", help="Parent argument")
    parser = PrettyParser(prog="test", parents=[parent])
    result = parser.parse_args(["--parent-arg", "value"])
    assert result is not None
    assert result.parent_arg == "value"


def test_pretty_parser_exit_on_error_false():
    """Test PrettyParser with exit_on_error=False."""
    parser = PrettyParser(prog="test", exit_on_error=False)
    assert parser.exit_on_error is False


def test_pretty_parser_allow_abbrev():
    """Test that PrettyParser respects allow_abbrev setting."""
    parser = PrettyParser(prog="test", allow_abbrev=True)
    parser.add_argument("--foobar")
    result = parser.parse_args(["--foo", "value"])
    assert result is not None
    assert result.foobar == "value"


def test_pretty_parser_color_kwarg():
    """Test PrettyParser accepts color kwarg on Python 3.14+."""
    parser = PrettyParser(prog="test", color=True)
    assert parser is not None


def test_pretty_parser_suggest_on_error_kwarg():
    """Test PrettyParser accepts suggest_on_error on Python 3.14+."""
    parser = PrettyParser(prog="test", suggest_on_error=True)
    assert parser is not None


def test_pretty_parser_fromfile_prefix_chars(tmp_path: Path) -> None:
    """Test PrettyParser with fromfile_prefix_chars."""
    args_file = tmp_path / "args.txt"
    args_file.write_text("--foo\nbar\n")
    parser = PrettyParser(prog="test", fromfile_prefix_chars="@")
    parser.add_argument("--foo")
    result = parser.parse_args([f"@{args_file}"])
    assert result is not None
    assert result.foo == "bar"


def test_pretty_parser_subparsers():
    """Test parser with subparsers."""
    parser = PrettyParser(prog="test")
    subparsers = parser.add_subparsers(dest="command")
    subparser_a = subparsers.add_parser("a", help="Command A")
    subparser_a.add_argument("--foo", help="Foo")
    subparser_b = subparsers.add_parser("b", help="Command B")
    subparser_b.add_argument("--bar", help="Bar")
    result = parser.parse_args(["a", "--foo", "value"])
    assert result is not None
    assert result.command == "a"
    assert result.foo == "value"


# =============================================================================
# parse_args calls _autocomplete when enabled
# =============================================================================


def test_pretty_parser_parse_args_calls_autocomplete_when_enabled():
    """Test that parse_args calls _autocomplete when enabled."""
    mock_argcomplete = MagicMock()
    with (
        patch(
            "deluxe.console.argparser.importlib.util.find_spec",
            return_value=True,
        ),
        patch(
            "deluxe.console.argparser.importlib.import_module",
            return_value=mock_argcomplete,
        ),
    ):
        parser = PrettyParser(prog="test", shell_completion=True)
    with patch.object(parser, "_autocomplete") as mock_aut:
        parser.parse_args([])
        mock_aut.assert_called_once()


# =============================================================================
# Shell Completion Tests
# =============================================================================


def test_shell_completion_set_contains_expected_shells():
    """Test that SHELL_COMPLETION contains expected shell names."""
    expected = {"bash", "zsh", "fish", "powershell"}
    assert expected.issubset(SHELL_COMPLETION)


# =============================================================================
# print_usage / print_help output tests
# =============================================================================


def test_print_usage_empty_parser(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that print_usage with no arguments produces usage output."""
    parser = PrettyParser(prog="test")
    parser.print_usage()
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


def test_print_usage_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that print_usage writes to stderr by default."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    parser.print_usage()
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


def test_print_usage_writes_to_file():
    """Test that print_usage writes to specified file."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    output = StringIO()
    parser.print_usage(file=output)
    assert "usage:" in output.getvalue().lower()


def test_pretty_parser_print_help_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that print_help writes to stderr by default."""
    parser = PrettyParser(prog="test")
    parser.print_help()
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()


def test_pretty_parser_print_help_writes_to_file():
    """Test that print_help writes to specified file."""
    parser = PrettyParser(prog="test")
    output = StringIO()
    parser.print_help(file=output)
    assert "usage:" in output.getvalue().lower()


def test_pretty_parser_format_usage_returns_string():
    """Test that format_usage returns a string."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    result = parser.format_usage()
    assert isinstance(result, str)
    assert "usage:" in result.lower()


def test_pretty_parser_format_help_returns_string():
    """Test that format_help returns a string."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    result = parser.format_help()
    assert isinstance(result, str)
    assert "usage:" in result.lower()


# =============================================================================
# Integration Tests
# =============================================================================


def test_integration_full_parser_workflow():
    """Test a complete parser workflow with multiple arguments."""
    parser = PrettyParser(
        prog="myapp",
        version="1.0.0",
        description="A test application",
    )
    parser.add_argument("input", help="Input file")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("--count", type=int, default=1, help="Number of iterations")
    result = parser.parse_args([
        "input.txt",
        "-o",
        "output.txt",
        "--verbose",
        "--count",
        "5",
    ])
    assert result is not None
    assert result.input == "input.txt"
    assert result.output == "output.txt"
    assert result.verbose is True
    assert result.count == 5


def test_integration_mixed_argument_types():
    """Test parser with various argument types."""
    parser = PrettyParser(prog="test")
    parser.add_argument("positional", help="Positional")
    parser.add_argument("-s", "--string", type=str, help="String")
    parser.add_argument("-i", "--integer", type=int, help="Integer")
    parser.add_argument("-f", "--float", type=float, help="Float")
    parser.add_argument("-b", "--boolean", action="store_true", help="Boolean")
    parser.add_argument(
        "-c",
        "--choice",
        choices=["a", "b", "c"],
        help="Choice",
    )
    result = parser.parse_args([
        "pos",
        "-s",
        "hello",
        "-i",
        "42",
        "-f",
        "2.72",
        "-b",
        "-c",
        "b",
    ])
    assert result is not None
    assert result.positional == "pos"
    assert result.string == "hello"
    assert result.integer == 42
    assert result.float == pytest.approx(2.72)
    assert result.boolean is True
    assert result.choice == "b"


def test_integration_error_handling_with_exit_on_error():
    """Test error handling with exit_on_error=True."""
    parser = PrettyParser(prog="test", exit_on_error=True)
    parser.add_argument("--required", required=True)
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args([])


def test_integration_help_output_contains_all_elements():
    """Test that help output contains all expected elements."""
    parser = PrettyParser(
        prog="testapp",
        description="Test description",
        epilog="Test epilog",
    )
    parser.add_argument("positional", help="Positional help")
    parser.add_argument("-f", "--foo", help="Foo help")
    help_text = parser.format_help()
    assert "testapp" in help_text
    assert "Test description" in help_text
    assert "Test epilog" in help_text
    assert "positional" in help_text.lower()
    assert "foo" in help_text.lower()


# =============================================================================
# Edge Cases
# =============================================================================


def test_pretty_parser_with_long_usage_string():
    """Test parser with very long custom usage string."""
    long_usage = "usage: " + " ".join([f"arg{i}" for i in range(50)])
    parser = PrettyParser(prog="test", usage=long_usage)
    result = parser.format_usage()
    assert isinstance(result, str)


def test_pretty_parser_many_arguments():
    """Test parser with many arguments."""
    parser = PrettyParser(prog="test")
    for i in range(20):
        parser.add_argument(f"--arg{i}", help=f"Argument {i}")
    result = parser.parse_args([f"--arg{i}=value{i}" for i in range(20)])
    assert result is not None
    for i in range(20):
        assert getattr(result, f"arg{i}") == f"value{i}"


def test_pretty_parser_mutually_exclusive_groups():
    """Test parser with mutually exclusive groups."""
    parser = PrettyParser(prog="test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--foo", help="Foo")
    group.add_argument("--bar", help="Bar")
    result = parser.parse_args(["--foo", "value"])
    assert result is not None
    assert result.foo == "value"
    assert result.bar is None


def test_pretty_parser_default_values():
    """Test parser with default values."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", default="default_foo")
    parser.add_argument("--bar", default=42)
    result = parser.parse_args([])
    assert result is not None
    assert result.foo == "default_foo"
    assert result.bar == 42


def test_pretty_parser_nargs_none():
    """Test parser with nargs=None (default)."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo")
    result = parser.parse_args(["--foo", "value"])
    assert result is not None
    assert result.foo == "value"


def test_pretty_parser_nargs_optional():
    """Test parser with nargs=argparse.OPTIONAL."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.OPTIONAL)
    result1 = parser.parse_args(["--foo", "value"])
    assert result1 is not None
    assert result1.foo == "value"
    result2 = parser.parse_args(["--foo"])
    assert result2 is not None
    assert result2.foo is None


def test_pretty_parser_nargs_zero_or_more():
    """Test parser with nargs=argparse.ZERO_OR_MORE."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.ZERO_OR_MORE)
    result = parser.parse_args(["--foo", "a", "b", "c"])
    assert result is not None
    assert result.foo == ["a", "b", "c"]


def test_pretty_parser_nargs_one_or_more():
    """Test parser with nargs=argparse.ONE_OR_MORE."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", nargs=argparse.ONE_OR_MORE)
    result = parser.parse_args(["--foo", "a", "b"])
    assert result is not None
    assert result.foo == ["a", "b"]


def test_pretty_parser_nargs_remainder():
    """Test parser with nargs=argparse.REMAINDER."""
    parser = PrettyParser(prog="test")
    parser.add_argument("foo", nargs=argparse.REMAINDER)
    result = parser.parse_args(["--", "a", "b", "c"])
    assert result is not None
    assert result.foo == ["--", "a", "b", "c"]


def test_pretty_parser_nargs_remainder_no_separator():
    """Test parser with nargs=REMAINDER without separator."""
    parser = PrettyParser(prog="test")
    parser.add_argument("foo", nargs=argparse.REMAINDER)
    result = parser.parse_args(["a", "b", "c"])
    assert result is not None
    assert result.foo == ["a", "b", "c"]


def test_pretty_parser_version_action():
    """Test that version action works correctly."""
    parser = PrettyParser(prog="test", version="2.0.0")
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])
    assert exc_info.value.code in {0, None}


def test_pretty_parser_with_empty_description():
    """Test parser with empty description."""
    parser = PrettyParser(prog="test", description="")
    result = parser.format_help()
    assert isinstance(result, str)


def test_pretty_parser_with_none_description():
    """Test parser with None description."""
    parser = PrettyParser(prog="test", description=None)
    result = parser.format_help()
    assert isinstance(result, str)


def test_pretty_parser_with_special_characters_in_description():
    """Test parser with special characters in description."""
    special_desc = "Description with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
    parser = PrettyParser(prog="test", description=special_desc)
    result = parser.format_help()
    assert special_desc in result


def test_pretty_parser_with_unicode_in_description():
    """Test parser with unicode characters in description."""
    unicode_desc = (
        "Description with unicode: "
        "\u4f60\u597d, \u3053\u3093\u306b\u3061\u306f, "
        "\u043f\u0440\u0438\u0432\u0435\u0442"
    )
    parser = PrettyParser(prog="test", description=unicode_desc)
    result = parser.format_help()
    assert unicode_desc in result


def test_pretty_parser_very_long_prog_name():
    """Test parser with very long program name."""
    long_prog = "a" * 100
    parser = PrettyParser(prog=long_prog)
    result = parser.format_usage()
    assert long_prog in result


def test_pretty_parser_argument_defaults_formatter():
    """Test PrettyParser with ArgumentDefaultsAnsiHelpFormatter."""
    parser = PrettyParser(
        prog="test",
        formatter_class=ArgumentDefaultsAnsiHelpFormatter,
    )
    parser.add_argument("--foo", default="bar", help="Foo help")
    result = parser.format_help()
    assert "default" in result.lower()


def test_pretty_parser_raw_description_formatter():
    """Test PrettyParser with RawDescriptionAnsiHelpFormatter."""
    parser = PrettyParser(
        prog="test",
        formatter_class=RawDescriptionAnsiHelpFormatter,
    )
    result = parser.format_help()
    assert isinstance(result, str)


def test_pretty_parser_raw_ansi_formatter():
    """Test PrettyParser with RawAnsiHelpFormatter."""
    parser = PrettyParser(
        prog="test",
        formatter_class=RawAnsiHelpFormatter,
    )
    result = parser.format_help()
    assert isinstance(result, str)


def test_pretty_parser_format_help_with_pretty_formatter():
    """Test format_help with PrettyHelpFormatter (default)."""
    parser = PrettyParser(
        prog="test",
        description="A test",
        epilog="End of test",
    )
    parser.add_argument("--foo", help="Foo help")
    result = parser.format_help()
    assert "A test" in result
    assert "End of test" in result
    assert "foo" in result.lower()


# =============================================================================
# Integration — format_usage with PrettyParser
# =============================================================================


def test_pretty_parser_format_usage_no_actions():
    """Test format_usage on PrettyParser with no added arguments."""
    parser = PrettyParser(prog="test")
    result = parser.format_usage()
    assert isinstance(result, str)
    assert "test" in result


def test_pretty_parser_format_usage_with_actions():
    """Test format_usage on PrettyParser with arguments."""
    parser = PrettyParser(prog="test")
    parser.add_argument("--foo", help="Foo help")
    parser.add_argument("input", help="Input file")
    result = parser.format_usage()
    assert isinstance(result, str)
    assert "test" in result
