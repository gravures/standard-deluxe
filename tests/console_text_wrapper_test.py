from __future__ import annotations

import string
from textwrap import TextWrapper

import pytest
from deluxe.console.ansi import Foreground, Mode, SGR_Params, strip_esc, style
from deluxe.console.wrap import AnsiTextWrapper
from hypothesis import given
from hypothesis import strategies as st


def test_bad_width_error():
    ctw = AnsiTextWrapper(width=-1)
    with pytest.raises(ValueError):  # noqa: PT011
        ctw.wrap("This is some text to wrap.")


def test_starting_whitespace():
    ctw = AnsiTextWrapper(width=20)
    test = ctw.wrap("   01234 56789 01234 56789 01234 56789 01234 56789")
    expected = ["   01234 56789 01234", "56789 01234 56789", "01234 56789"]
    assert test == expected


def test_max_lines_and_placeholder():
    ctw = AnsiTextWrapper(width=10, max_lines=2, placeholder="**" * 10)
    with pytest.raises(ValueError):  # noqa: PT011
        ctw.wrap("01234 56789 01234 56789 01234 56789 01234 56789")


def test_max_lines_and_indent():
    ctw = AnsiTextWrapper(width=20, max_lines=2, initial_indent="  ")
    test = ctw.wrap("01234 56789 01234 56789 01234 56789 01234 56789")
    expected = ["  01234 56789 01234", "56789 01234 [...]"]
    assert test == expected


def test_max_lines_and_subsequence_indent():
    ctw = AnsiTextWrapper(width=20, max_lines=0, initial_indent="   ", subsequent_indent=" ")
    test = ctw.wrap("01234 56789 01234 56789 01234 56789 01234 56789")
    expected = ["   01234 56789 [...]"]
    assert test == expected


def test_too_big():
    ctw = AnsiTextWrapper(width=10)
    test = ctw.wrap("0123456789 0123456789 01234567890123456789")
    expected = [string.digits, string.digits, string.digits, string.digits]
    assert test == expected


def test_placeholder_edge_case():
    ctw = AnsiTextWrapper(width=4, max_lines=1, placeholder="***")
    assert ctw.wrap(string.digits) == ["***"]


def test_placeholder_edge_case_2():
    ctw = AnsiTextWrapper(width=5, max_lines=2, placeholder="****")
    assert ctw.wrap("0123456789 " * 2) == ["01234", "****"]


def test_multiple_spaces_handling():
    """Test that the wrapper correctly handles text with multiple spaces between words."""
    ctw = AnsiTextWrapper(width=20)

    # Text with multiple spaces between words
    text = "This  is    some     text with   multiple    spaces"

    wrapped_text = ctw.wrap(text)

    # Expected result should preserve the multiple spaces between words
    expected = ["This  is    some", "text with   multiple", "spaces"]

    assert wrapped_text == expected


def test_exact_width_wrapping():
    """Test that the wrapper correctly wraps text at exactly the specified width."""
    # Create a wrapper with a specific width
    width = 20
    wrapper = AnsiTextWrapper(width=width)

    # Create a text that should wrap exactly at the width boundary
    # Each segment is exactly 20 characters
    text = "12345678901234567890 12345678901234567890 12345678901234567890"

    wrapped_text = wrapper.wrap(text)

    # Each line should be exactly the width specified (except possibly the last line)
    expected = ["12345678901234567890", "12345678901234567890", "12345678901234567890"]

    assert wrapped_text == expected

    # Verify each line is exactly at the width boundary
    for line in wrapped_text:
        assert len(line) == width


def test_empty_string_input():
    """Test that the wrapper correctly processes empty strings."""
    # Create a wrapper with default settings
    wrapper = AnsiTextWrapper(width=80)

    # Test with an empty string
    result = wrapper.wrap("")

    # Empty string should result in an empty list
    assert result == []

    # Test with only whitespace
    result = wrapper.wrap("   ")

    # With drop_whitespace=True (default), this should also result in an empty list
    assert result == []

    # Test with drop_whitespace=False
    wrapper = AnsiTextWrapper(width=80, drop_whitespace=False)
    result = wrapper.wrap("   ")

    # With drop_whitespace=False, whitespace should be preserved
    assert result == ["   "]


def test_whitespace_only_input():
    """Test that the wrapper correctly processes text containing only whitespace."""
    # Create a wrapper with default settings
    wrapper = AnsiTextWrapper(width=80)

    # Test with various whitespace inputs
    whitespace_inputs = [" ", "  ", "\t", "\n", "\t \n", "   \t   ", "\r\n\t "]

    # With drop_whitespace=True (default), this should result in an empty list
    for whitespace in whitespace_inputs:
        assert wrapper.wrap(whitespace) == []

    # Test with drop_whitespace=False
    custom_wrapper = AnsiTextWrapper(width=80, drop_whitespace=False)
    standard_wrapper = TextWrapper(width=80, drop_whitespace=False)
    for whitespace in whitespace_inputs:
        result = custom_wrapper.wrap(whitespace)
        expected = standard_wrapper.wrap(whitespace)
        # With drop_whitespace=False, whitespace should be preserved
        assert result == expected

    # Test with indentation
    indented_wrapper = AnsiTextWrapper(width=10, initial_indent=">>", drop_whitespace=False)
    result = indented_wrapper.wrap("  ")
    assert result == [">>  "]


def test_zero_width():
    """Test that the wrapper correctly raises ValueError when width is set to zero."""
    # Create a wrapper with width set to zero
    ctw = AnsiTextWrapper(width=0)

    # Attempt to wrap text with zero width should raise ValueError
    with pytest.raises(ValueError) as excinfo:  # noqa: PT011
        ctw.wrap("This is some text to wrap.")

    # Verify the error message
    assert "invalid width 0 (must be > 0)" in str(excinfo.value)


def test_ansi_escape_sequence_handling():
    """Test that the wrapper correctly handles text with ANSI escape sequences."""
    # Create a wrapper with a specific width
    width = 20
    wrapper = AnsiTextWrapper(width=width)

    # Create text with ANSI escape sequences
    colored_text = (
        f"{style(Foreground.RED)}Red text{style(Mode.RESET_ALL)} "
        f"{style(Foreground.BLUE)}Blue text{style(Mode.RESET_ALL)} "
        f"{style(Foreground.GREEN)}Green text{style(Mode.RESET_ALL)}"
    )

    # Wrap the colored text
    wrapped_text = wrapper.wrap(colored_text)

    # The ANSI sequences should not count towards the width
    # So the text should wrap based on the visible characters only

    # Check that each line's visible content (without ANSI codes) is within the width limit
    for line in wrapped_text:
        assert len(strip_esc(line)) <= width

    # Verify that the ANSI sequences are preserved in the output
    full_text = "\n".join(wrapped_text)
    assert style(Foreground.RED) in full_text
    assert style(Foreground.BLUE) in full_text
    assert style(Foreground.GREEN) in full_text

    # Verify that the original text content is preserved (without ANSI codes)
    original_content = strip_esc(colored_text)
    wrapped_content = strip_esc("".join(wrapped_text))
    assert original_content.replace(" ", "") == wrapped_content.replace(" ", "")


@given(
    text=st.text(min_size=3, max_size=100),
    width=st.integers(min_value=10, max_value=80),
    colors=st.lists(
        st.sampled_from([
            Foreground.RED,
            Foreground.GREEN,
            Foreground.BLUE,
            Foreground.YELLOW,
            Foreground.CYAN,
            Foreground.MAGENTA,
        ]),
        min_size=1,
        max_size=5,
    ),
)
def test_ansi_escape_sequence_handling_property(text: str, width: int, colors: list[SGR_Params]):
    """Property-based test for ANSI escape sequence handling."""
    wrapper = AnsiTextWrapper(width=width)
    standard_wrapper = TextWrapper(width=width)

    # Apply random colors to random parts of the text
    colored_text = text
    for color in colors:
        if len(text) > 2:  # Ensure there's enough text to split
            split_point = len(text) // 2
            colored_text = (
                colored_text[:split_point]
                + style(color)
                + colored_text[split_point:]
                + style(Mode.RESET_ALL)
            )

    # Wrap the colored text
    wrapped_text = wrapper.wrap(colored_text)

    # Skip empty results (can happen with whitespace-only inputs)
    if not wrapped_text:
        return

    # Check that each line's visible content is within the width limit
    for line in wrapped_text:
        assert len(strip_esc(line)) <= width

    # Verify that the original text content is preserved (ignoring whitespace differences)
    original_content = strip_esc(colored_text).replace(" ", "")
    wrapped_content = strip_esc("".join(wrapped_text)).replace(" ", "")
    expected = "".join(standard_wrapper.wrap(original_content)).replace(" ", "")
    assert wrapped_content == expected
