from __future__ import annotations

import importlib.util
import sys
import time
from unittest.mock import patch

import pytest
from deluxe.console.ansi import (
    BELL,
    BG,
    FG,
    MOD,
    Background,
    Foreground,
    Mode,
    SGR_Params,
    clear_line,
    clear_line_after,
    clear_line_before,
    clear_screen,
    length,
    set_title,
    strip_esc,
    style,
)
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import sampled_from, text


def test_bell_returns_correct_sequence():
    bell = BELL()
    assert bell() == "\a"


@given(
    foreground=sampled_from([
        Foreground.RED,
        Foreground.GREEN,
        Foreground.BLUE,
        Foreground.YELLOW,
        Foreground.CYAN,
        Foreground.MAGENTA,
        Foreground.BLACK,
        Foreground.WHITE,
        Foreground.LIGHT_RED,
        Foreground.LIGHT_GREEN,
        Foreground.LIGHT_BLUE,
        Foreground.LIGHT_YELLOW,
        Foreground.LIGHT_CYAN,
        Foreground.LIGHT_MAGENTA,
        Foreground.LIGHT_BLACK,
        Foreground.LIGHT_WHITE,
        Foreground.RESET,
    ]),
    background=sampled_from([
        Background.RED,
        Background.GREEN,
        Background.BLUE,
        Background.YELLOW,
        Background.CYAN,
        Background.MAGENTA,
        Background.BLACK,
        Background.WHITE,
        Background.LIGHT_RED,
        Background.LIGHT_GREEN,
        Background.LIGHT_BLUE,
        Background.LIGHT_YELLOW,
        Background.LIGHT_CYAN,
        Background.LIGHT_MAGENTA,
        Background.LIGHT_BLACK,
        Background.LIGHT_WHITE,
        Background.RESET,
    ]),
    mode=sampled_from([
        Mode.BRIGHT,
        Mode.DIM,
        Mode.ITALIC,
        Mode.UNDERLINE,
        Mode.BLINK,
        Mode.NORMAL,
    ]),
)
def test_style_with_random_parameters(
    foreground: SGR_Params, background: SGR_Params, mode: SGR_Params
):
    """Test style function with randomly selected parameters."""
    result = style(mode, background, foreground)
    # Verify the result is a valid ANSI sequence
    assert result.startswith("\x1b[")
    assert result.endswith("m")
    # Verify the parameters are included in the result
    assert str(foreground) in result
    assert str(background) in result
    assert str(mode) in result


def test_style_handles_multiple_sgr_parameters_correctly():
    result = style(Mode.BRIGHT, Background.YELLOW, Foreground.RED)
    expected = "\x1b[1;43;31m"
    assert result == expected


def test_style_handles_empty_input_gracefully():
    result = style()
    expected = "\x1b[m"
    assert result == expected


def test_style_handles_duplicate_sgr_parameters_correctly():
    result = style(Foreground.RED, Background.YELLOW, Mode.BRIGHT, Foreground.RED)
    expected = "\x1b[1;43;31m"
    assert result == expected


def test_handles_maximum_number_of_sgr_parameters():
    result = style(
        Foreground.LIGHT_YELLOW,
        Foreground.LIGHT_WHITE,
        Foreground.LIGHT_CYAN,
        Foreground.LIGHT_GREEN,
        Foreground.LIGHT_MAGENTA,
        Foreground.LIGHT_RED,
        Foreground.LIGHT_BLACK,
        Foreground.YELLOW,
        Foreground.WHITE,
        Foreground.CYAN,
        Foreground.GREEN,
        Foreground.MAGENTA,
        Foreground.RED,
        Foreground.BLACK,
        Foreground.RESET,
        Background.LIGHT_YELLOW,
        Background.LIGHT_WHITE,
        Background.LIGHT_CYAN,
        Background.LIGHT_GREEN,
        Background.LIGHT_MAGENTA,
        Background.LIGHT_RED,
        Background.LIGHT_BLACK,
        Background.YELLOW,
        Background.WHITE,
        Background.CYAN,
        Background.GREEN,
        Background.MAGENTA,
        Background.RED,
        Background.BLACK,
        Background.RESET,
    )
    expected = "\x1b[49;39m"
    assert result == expected


def test_style_performance_with_large_parameter_count():
    # Create a large list of parameters
    params: list[SGR_Params] = []
    for _ in range(100):
        params.extend([
            Foreground.RED,
            Foreground.GREEN,
            Foreground.BLUE,
            Background.RED,
            Background.GREEN,
            Background.BLUE,
            Mode.BRIGHT,
            Mode.DIM,
            Mode.UNDERLINE,
            Mode.ITALIC,
        ])

    # Measure the time it takes to process this large number of parameters
    start_time = time.time()
    result = style(*params)
    end_time = time.time()

    # Verify the function completes in a reasonable time (adjust threshold as needed)
    assert end_time - start_time < 1.0, (
        "Style function took too long to process large parameter count"
    )

    # Verify the result is a valid ANSI sequence
    assert result.startswith("\x1b[")
    assert result.endswith("m")

    # Verify the function didn't crash and returned a string
    assert isinstance(result, str)


def test_style_with_conflicting_parameters():
    # Test with conflicting style parameters (BRIGHT and DIM)
    result = style(Mode.BRIGHT, Mode.DIM)
    # The last parameter should take precedence
    expected = "\x1b[1;2m"
    assert result == expected

    # Test with NORMAL which should override both BRIGHT and DIM
    result = style(Mode.BRIGHT, Mode.DIM, Mode.NORMAL)
    expected = "\x1b[1;2;22m"
    assert result == expected

    # Test with multiple conflicting parameters in different order
    result = style(Mode.DIM, Mode.BRIGHT)
    expected = "\x1b[2;1m"
    assert result == expected


@given(
    content=text(min_size=1, max_size=100),
    fg=sampled_from([f for f in dir(Foreground) if not f.startswith("_")]),
    bg=sampled_from([b for b in dir(Background) if not b.startswith("_")]),
)
def test_style_application_to_text(content: str, fg: str, bg: str):
    """Test applying style to random text content."""
    # Get the actual color values
    fg_color = getattr(Foreground, fg)
    bg_color = getattr(Background, bg)

    # Create the styled text
    ansi_sequence = style(fg_color, bg_color)
    styled_text = f"{ansi_sequence}{content}\x1b[0m"

    # Verify the styled text contains the ANSI sequence and the content
    assert ansi_sequence in styled_text
    assert content in styled_text
    assert styled_text.endswith("\x1b[0m")  # Reset at the end


@given(
    text=st.text(min_size=1, max_size=100),
    ansi_sequences=st.lists(
        st.sampled_from([
            style(FG.RED),
            style(BG.BLUE),
            style(MOD.BRIGHT),
            style(FG.GREEN, BG.YELLOW),
            style(MOD.UNDERLINE, FG.CYAN),
            clear_line(),
            clear_screen(),
            clear_line_after(),
            clear_line_before(),
        ]),
        min_size=1,
        max_size=5,
    ),
)
def test_strip_esc_removes_ansi_sequences(text: str, ansi_sequences: list[str]):
    """Test that strip_esc correctly removes all ANSI escape sequences."""
    # Create a string with ANSI sequences interspersed
    parts: list[str] = []
    for i, seq in enumerate(ansi_sequences):
        parts.append(seq)
        if i < len(text):
            parts.append(text[i])

    # Add any remaining text
    if len(ansi_sequences) < len(text):
        parts.append(text[len(ansi_sequences) :])

    # Join all parts to create the test string
    test_string: str = "".join(parts)

    # Strip ANSI sequences
    stripped = strip_esc(test_string)

    # Verify that the result contains only the original text
    # and all ANSI sequences have been removed
    assert "\033[" not in stripped
    assert "\033]" not in stripped

    # Check that the text content is preserved
    for char in text:
        if char in test_string:
            assert char in stripped


@given(
    text=st.text(min_size=1, max_size=100),
    ansi_sequences=st.lists(
        st.sampled_from([
            style(FG.RED),
            style(BG.BLUE),
            style(MOD.BRIGHT),
            style(FG.GREEN, BG.YELLOW),
            style(MOD.UNDERLINE, FG.CYAN),
            style(MOD.RESET_ALL),
        ]),
        min_size=0,
        max_size=10,
    ),
)
def test_length_calculates_visible_string_length(text: str, ansi_sequences: list[str]):
    """Test that length function correctly calculates visible string length."""
    # Create a string with ANSI sequences interspersed
    parts: list[str] = []
    for i, seq in enumerate(ansi_sequences):
        parts.append(seq)
        if i < len(text):
            parts.append(text[i : i + 1])

    # Add any remaining text
    if len(ansi_sequences) < len(text):
        parts.append(text[len(ansi_sequences) :])

    # Join all parts to create the test string
    test_string = "".join(parts)

    # Calculate the length using the length function
    calculated_length = length(test_string)

    # Calculate the expected length by stripping ANSI sequences
    expected_length = len(strip_esc(test_string))

    # Verify that the calculated length matches the expected length
    assert calculated_length == expected_length

    # Also verify that the calculated length matches the original text length
    assert calculated_length == len(text)


def test_strip_esc_with_plain_text():
    """Test that strip_esc correctly handles strings without ANSI escape sequences."""
    # Test with various plain text strings
    plain_texts = [
        "Hello, world!",
        "This is a test string with no ANSI escape sequences.",
        "Special characters: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        "Numbers: 0123456789",
        "",  # Empty string
        " ",  # Space
        "\t\n\r",  # Whitespace characters
        "Unicode characters: 你好, こんにちは, привет, مرحبا, 안녕하세요",
    ]

    for text_ in plain_texts:
        # The function should return the original string unchanged
        assert strip_esc(text_) == text_

    # Use hypothesis to test with random strings
    @given(st.text())
    def test_random_plain_text(text: str):
        assert strip_esc(text) == text

    test_random_plain_text()


def test_set_title_generates_correct_sequence():
    """Test that set_title function correctly generates the OSC sequence
    for setting the terminal title."""
    # Test with a simple title
    title = "Test Title"
    result = set_title(title)
    expected = f"\033]2;{title}\a"
    assert result == expected

    # Test with an empty title
    empty_title = ""
    result = set_title(empty_title)
    expected = f"\033]2;{empty_title}\a"
    assert result == expected

    # Test with special characters
    special_title = "Special Characters: !@#$%^&*()_+-=[]{}|;':\",./<>?"
    result = set_title(special_title)
    expected = f"\033]2;{special_title}\a"
    assert result == expected

    # Test with Unicode characters
    unicode_title = "Unicode: 你好, こんにちは, привет"
    result = set_title(unicode_title)
    expected = f"\033]2;{unicode_title}\a"
    assert result == expected


@given(title=st.text(min_size=0, max_size=100))
def test_set_title_with_random_strings(title: str):
    """Test set_title function with randomly generated strings."""
    result = set_title(title)

    # Verify the result is a valid OSC sequence
    assert result.startswith("\033]2;")
    assert result.endswith("\a")

    # Verify the title is included in the result
    assert title in result

    # Verify the complete structure
    expected = f"\033]2;{title}\a"
    assert result == expected


def test_strip_esc_with_complex_nested_sequences():
    """Test that strip_esc correctly handles complex nested escape sequences."""
    # Create a complex string with multiple nested and overlapping escape sequences
    complex_string = (
        f"{style(FG.RED)}Red text "
        f"{style(BG.BLUE)}Red on blue "
        f"{style(MOD.BRIGHT)}Bright red on blue "
        f"{style(FG.GREEN)}Bright green on blue "
        f"{style(MOD.UNDERLINE)}Underlined bright green on blue "
        f"{style(BG.YELLOW, FG.BLACK)}Underlined black on yellow "
        f"{style(MOD.RESET_ALL, FG.CYAN, BG.MAGENTA)}Cyan on magenta "
        f"{style(MOD.ITALIC, FG.WHITE)}Italic white on magenta "
        f"Normal text"
    )

    # The expected result after stripping should be just the text content
    expected = (
        "Red text "
        "Red on blue "
        "Bright red on blue "
        "Bright green on blue "
        "Underlined bright green on blue "
        "Underlined black on yellow "
        "Cyan on magenta "
        "Italic white on magenta "
        "Normal text"
    )

    # Strip the ANSI escape sequences
    stripped = strip_esc(complex_string)

    # Verify the result matches the expected text
    for a, b in zip(stripped.split(), expected.split(), strict=False):
        assert a == b
    assert stripped == expected

    # Verify no ANSI escape sequences remain
    assert "\033[" not in stripped
    assert "\033]" not in stripped

    # Test with deeply nested sequences
    deeply_nested = (
        f"{style(FG.RED)}{style(BG.GREEN)}{style(MOD.BRIGHT)}{style(MOD.UNDERLINE)}"
        f"Deeply nested text"
        f"{style(MOD.RESET_ALL)}"
    )

    assert strip_esc(deeply_nested) == "Deeply nested text"

    # Test with escape sequences at the beginning, middle, and end
    mixed_placement = f"{style(FG.BLUE)}Start Middle{style(BG.RED)} End{style(MOD.RESET_ALL)}"

    assert strip_esc(mixed_placement) == "Start Middle End"

    # Test with consecutive escape sequences without text in between
    consecutive_sequences = (
        f"{style(FG.RED)}{style(BG.GREEN)}{style(MOD.BRIGHT)}Text with consecutive sequences"
    )

    assert strip_esc(consecutive_sequences) == "Text with consecutive sequences"


def test_strip_esc_handles_osc_sequences():
    """Test that strip_esc correctly removes OSC escape sequences.

    OSC (Operating System Command) sequences use ESC ] as prefix
    and BEL (\\a) as terminator, e.g. for setting terminal titles.
    strip_esc should remove the entire sequence including its content.
    """
    # OSC sequence from set_title
    title_seq = set_title("Test Title")
    assert title_seq == "\033]2;Test Title\a"
    assert not strip_esc(title_seq)

    # OSC embedded in text — title content is metadata, not visible text
    text_with_osc = f"Before {set_title('My Title')} After"
    assert strip_esc(text_with_osc) == "Before  After"

    # OSC with empty title
    assert not strip_esc(set_title(""))

    # OSC with special characters
    assert not strip_esc(set_title("Hello World!"))


def test_strip_esc_does_not_leak_non_ansi_control_chars():
    """Test that strip_esc only removes ANSI escape sequences.

    C0/C1 control characters that are not part of ANSI escape sequences
    should NOT be stripped. They are not ANSI escapes — they are
    separate characters with their own meaning.
    """
    # \x1f (Unit Separator) is not an ANSI escape — should be preserved
    assert strip_esc("\x1b[31m\x1f") == "\x1f"
    assert strip_esc(f"{style(FG.RED)}text\x1ftext{style(MOD.RESET_ALL)}") == "text\x1ftext"

    # \x00 (NULL) is not an ANSI escape — should be preserved
    assert strip_esc("before\x00after") == "before\x00after"

    # \x7f (DEL) is not an ANSI escape — should be preserved
    assert strip_esc("before\x7f\u007f after") == "before\x7f\u007f after"


@pytest.mark.skipif(
    sys.platform not in {"win32", "cygwin"}, reason="Test only applicable on Windows platforms"
)
def test_colorama_integration_on_windows():
    """Test that colorama is correctly integrated on Windows platforms."""
    # Skip if colorama is not installed
    if not importlib.util.find_spec("colorama"):
        pytest.skip("colorama not installed")

    # Test that colorama was imported and initialized
    assert colorama is not None  # pyright: ignore[reportUndefinedVariable]  # noqa: F821

    # We can't easily test the actual initialization without mocking,
    # but we can verify that the module was imported correctly
    assert hasattr(colorama, "just_fix_windows_console")  # noqa: F821  # pyright: ignore[reportUndefinedVariable, reportUnknownArgumentType]

    # Reimport the module to verify the initialization happens
    with patch("importlib.util.find_spec", return_value=True):  # noqa: SIM117
        with patch("importlib.import_module") as mock_import:
            mock_colorama = mock_import.return_value

            # Force reimport by reloading the module
            import deluxe.console.ansi  # noqa: PLC0415

            importlib.reload(deluxe.console.ansi)

            # Verify colorama was imported and initialized
            mock_import.assert_called_with("colorama")
            mock_colorama.just_fix_windows_console.assert_called_once()
