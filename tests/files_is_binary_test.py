from __future__ import annotations

# Assume the code under test is in 'deluxe.files'
from deluxe.files import is_binary
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


# The set of character codes the function considers "text".
# This replicates the logic from the function itself for accuracy.
TEXT_CHAR_CODES = list(range(32, 127)) + [ord(c) for c in ["\x08", "\x0c", "\n", "\r", "\t"]]
TEXT_CHARACTERS = [chr(c) for c in TEXT_CHAR_CODES]

# Strategy for generating content that is guaranteed to be considered text.
# The content is encoded to bytes using an encoding that maps one-to-one.
pure_text_strategy = st.text(
    alphabet=TEXT_CHARACTERS,
    min_size=1,
    max_size=1024,  # Test with more than the 512 bytes read limit
).map(lambda s: s.encode("ISO-8859-1"))

# Strategy for generating content that is guaranteed to contain a null byte,
# which is a definitive marker for a binary file in the function's logic.
content_with_null_byte_strategy = st.binary(min_size=0, max_size=511).map(lambda b: b + b"\x00")


def test_property_is_binary_for_non_existent_path(tmp_path: Path):
    """
    Property: is_binary must return False for a path that does not exist.
    """
    non_existent_file = tmp_path / "this_file_does_not_exist.bin"
    assert not is_binary(non_existent_file)


def test_property_is_binary_for_directory(tmp_path: Path):
    """
    Property: is_binary must return False for a path that is a directory.
    """
    assert not is_binary(tmp_path)


def test_property_is_binary_for_empty_file(tmp_path: Path):
    """
    Property: is_binary must return False for an empty file, as it is
    considered text by default.
    """
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    assert not is_binary(empty_file)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(data=content_with_null_byte_strategy)
def test_property_is_binary_true_for_null_bytes(tmp_path: Path, data: bytes):
    """
    Property: Any file containing a null byte within the first 512 bytes
    must be considered binary.
    """
    test_file = tmp_path / "file_with_null.bin"
    test_file.write_bytes(data)
    assert is_binary(test_file)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(data=pure_text_strategy)
def test_property_is_binary_false_for_pure_text(tmp_path: Path, data: bytes):
    """
    Property: A file containing only valid text characters must not be
    considered binary.
    """
    test_file = tmp_path / "pure_text.txt"
    test_file.write_bytes(data)
    assert not is_binary(test_file)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(data=st.binary(min_size=1, max_size=1024))
def test_property_is_binary_evaluates_ratio_correctly(tmp_path: Path, data: bytes):
    """
    Property: For files without null bytes, the binary status is determined
    by the ratio of non-text characters, which should match the function's logic.
    """
    # Isolate this test from the null-byte rule, which takes precedence.
    assume(b"\x00" not in data)  # noqa: PLR2004

    # Re-implement the function's ratio logic to derive the expected result.
    char_threshold = 0.3
    text_characters_map = dict.fromkeys(TEXT_CHAR_CODES)

    # The function reads up to 512 bytes and decodes with ISO-8859-1.
    file_data_str = data[:512].decode("ISO-8859-1")
    data_length = len(file_data_str)

    # str.translate() removes all characters whose ordinals are in the map's keys.
    # The length of the remaining string is the count of "binary" characters.
    binary_length = len(file_data_str.translate(text_characters_map))

    expected_is_binary = (float(binary_length) / data_length) >= char_threshold

    # Perform the actual test against the function.
    test_file = tmp_path / "test.data"
    test_file.write_bytes(data)

    assert is_binary(test_file) == expected_is_binary
