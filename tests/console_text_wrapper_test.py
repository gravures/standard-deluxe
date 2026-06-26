from __future__ import annotations

import string
from textwrap import TextWrapper

import pytest
from deluxe.console.ansi import Foreground, Mode, SGR_PARAMS, length, strip_esc, style
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
def test_ansi_escape_sequence_handling_property(text: str, width: int, colors: list[SGR_PARAMS]):
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


def test_ansi_wrapper_handle_long_word_uses_visible_length():
    """Regression test: _handle_long_word must use visible length, not len().

    When AnsiTextWrapper encounters a word longer than the width, it calls
    _handle_long_word (inherited from TextWrapper) which uses len() to break
    the word. This splits ANSI escape sequences at wrong positions, causing
    control characters like \\x1f to leak into the output.

    TextWrapper treats \\x1f as whitespace (str.isspace() returns True) and
    drops it from line ends. AnsiTextWrapper should produce equivalent visible
    content.
    """
    width = 13
    wrapper = AnsiTextWrapper(width=width)
    standard_wrapper = TextWrapper(width=width)

    # \x1f (Unit Separator) is whitespace by str.isspace() but not split by
    # TextWrapper._split. It gets isolated by _handle_long_word and dropped.
    text = "0000000000000\x1f"
    colored = text[:7] + style(Foreground.RED) + text[7:] + style(Mode.RESET_ALL)

    wrapped_text = wrapper.wrap(colored)
    assert wrapped_text  # Not empty

    # Each line must be within width
    for line in wrapped_text:
        assert length(line) <= width

    # Visible content should match standard TextWrapper behavior
    original_content = strip_esc(colored).replace(" ", "")
    wrapped_content = strip_esc("".join(wrapped_text)).replace(" ", "")
    expected = "".join(standard_wrapper.wrap(original_content)).replace(" ", "")
    assert wrapped_content == expected


def test_ansi_wrapper_long_word_preserves_ansi_integrity():
    """Regression test: _handle_long_word must not break ANSI escape sequences.

    When _handle_long_word uses len() instead of length(), it can split
    an ANSI escape sequence in the middle, producing corrupted output like
    incomplete escape codes that strip_esc cannot remove.
    """
    width = 15
    wrapper = AnsiTextWrapper(width=width)

    # Place text so that the ANSI sequence boundary falls inside _handle_long_word's
    # len()-based break point. 'x'*14 fills 14 visible chars, then \x1b[31m is a
    # 5-char escape sequence. _handle_long_word with len()=15 breaks mid-sequence.
    text = "x" * 14 + style(Foreground.RED) + "y" * 14 + style(Mode.RESET_ALL)
    wrapped_text = wrapper.wrap(text)

    assert wrapped_text  # Not empty

    # Every line's visible content must be within width
    for line in wrapped_text:
        visible = strip_esc(line)
        assert len(visible) <= width, (
            f"Line visible content exceeds width: {visible!r} ({len(visible)} > {width})"
        )

    # No line should contain leaked escape code characters in visible text
    for line in wrapped_text:
        visible = strip_esc(line)
        assert "\x1b" not in visible, f"Leaked escape character in visible text: {visible!r}"

    # The full visible text should be preserved
    full_visible = strip_esc("".join(wrapped_text))
    original_visible = strip_esc(text)
    assert full_visible == original_visible


def test_ansi_wrapper_with_osc_sequences():
    """Test wrapping text that contains OSC escape sequences."""
    wrapper = AnsiTextWrapper(width=20)
    # OSC sequence for setting terminal title, followed by long text
    osc = "\x1b]2;My Title\x07"
    text = osc + "a" * 30
    wrapped = wrapper.wrap(text)

    for line in wrapped:
        assert length(line) <= 20

    # OSC must not leak into visible text
    full_visible = strip_esc("".join(wrapped))
    assert "\x1b" not in full_visible
    assert "\a" not in full_visible


def test_ansi_wrapper_with_unknown_escape():
    """Test wrapping text that contains unknown ESC sequences."""
    wrapper = AnsiTextWrapper(width=15)
    # ESC F is not a standard sequence — not stripped by strip_esc, counted
    # as 2 visible characters by both length() and _visible_break_pos().
    text = "\x1bF" + "b" * 30
    wrapped = wrapper.wrap(text)

    for line in wrapped:
        assert length(line) <= 15

    # strip_esc does not remove unknown escapes, so \x1bF remains
    full_visible = strip_esc("".join(wrapped))
    assert full_visible == "\x1bF" + "b" * 30


def test_ansi_wrapper_with_multi_param_csi():
    """Test wrapping text with multi-parameter CSI sequences (e.g. 256-color)."""
    wrapper = AnsiTextWrapper(width=10)
    text = "\x1b[38;5;196m" + "z" * 20 + "\x1b[0m"
    wrapped = wrapper.wrap(text)

    for line in wrapped:
        assert length(line) <= 10

    full_visible = strip_esc("".join(wrapped))
    assert full_visible == "z" * 20


def test_ansi_wrapper_no_break_long_words():
    """Test _handle_long_word 'elif not cur_line' branch.

    When break_long_words is False and the chunk doesn't fit,
    the whole chunk goes on one line even if wider than width.
    """
    wrapper = AnsiTextWrapper(width=5, break_long_words=False)
    wrapped = wrapper.wrap("verylongword")
    assert wrapped == ["verylongword"]


def test_ansi_wrapper_no_break_long_words_existing_line():
    """Test _handle_long_word when cur_line is already non-empty.

    When break_long_words is False and a word doesn't fit on a line that
    already has content, the word is left for the next line.
    """
    wrapper = AnsiTextWrapper(width=8, break_long_words=False)
    wrapped = wrapper.wrap("ab verylongword")
    assert wrapped == ["ab", "verylongword"]


def test_ansi_wrapper_mixed_escapes_in_long_word():
    """Test wrapping a long word containing multiple escape types."""
    wrapper = AnsiTextWrapper(width=12)
    # Mix of CSI, OSC, and unknown escapes inside a long word
    text = (
        "\x1b[31m"  # CSI
        "abcdefgh"
        "\x1b]0;title\x07"  # OSC
        "ijklmnop"
        "\x1bF"  # unknown — 2 visible chars, not stripped
        "qrstuvwxyz"
        "\x1b[0m"
    )
    wrapped = wrapper.wrap(text)

    for line in wrapped:
        assert length(line) <= 12

    # CSI/OSC sequences are stripped; \x1bF is not
    full_visible = strip_esc("".join(wrapped))
    original_visible = strip_esc(text)
    assert full_visible == original_visible


def test_ansi_wrapper_hyphen_break_in_ansi_word():
    """Test hyphen-breaking inside a long ANSI-colored word.

    _split_chunks splits on hyphens, so we must construct chunks manually
    via _handle_long_word to exercise the hyphen fallback branch.
    """
    wrapper = AnsiTextWrapper(width=10, break_long_words=True, break_on_hyphens=True)
    # A single ANSI-wrapped chunk containing a hyphen
    chunk = "\x1b[31mabc-def-ghi-jkl\x1b[0m"
    reversed_chunks = [chunk]
    cur_line: list[str] = []
    wrapper._handle_long_word(reversed_chunks, cur_line, 0, 10)  # type: ignore[reportPrivateUsage]  # pyright: ignore[reportPrivateUsage]

    # Should break at the hyphen, not mid-word
    assert cur_line[0] == "\x1b[31mabc-def-"
    assert reversed_chunks[0] == "ghi-jkl\x1b[0m"


def test_ansi_wrapper_no_hyphen_break_in_long_word():
    """Test _handle_long_word when break_on_hyphens is False.

    Exercises the branch where break_on_hyphens=False inside _handle_long_word,
    so the hyphen fallback is skipped and the word breaks at max_visible.
    """
    wrapper = AnsiTextWrapper(width=10, break_long_words=True, break_on_hyphens=True)
    # Manually call _handle_long_word with a chunk that has no hyphens
    # to hit the break_on_hyphens path without actually splitting on hyphens
    chunk = "\x1b[31mabcdefghijklmnop\x1b[0m"
    reversed_chunks = [chunk]
    cur_line: list[str] = []

    wrapper.break_on_hyphens = False
    wrapper._handle_long_word(reversed_chunks, cur_line, 0, 10)  # type: ignore[reportPrivateUsage]  # pyright: ignore[reportPrivateUsage]

    # Should break at 10 visible chars, not at a hyphen
    assert length(cur_line[0]) == 10
