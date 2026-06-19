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
"""Tests for split_drive function."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from deluxe.files import split_drive
from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Example-based tests
# ---------------------------------------------------------------------------


def test_split_drive_windows_path_with_forward_slash():
    """Test splitting Windows path with forward slash."""
    assert split_drive("C:/Users/test") == ("C:", "/Users/test")


def test_split_drive_windows_path_with_backslash():
    """Test splitting Windows path with backslash."""
    assert split_drive("C:\\Users\\test") == ("C:", "\\Users\\test")


def test_split_drive_windows_path_mixed_slashes():
    """Test splitting Windows path with mixed slashes."""
    assert split_drive("C:/Users\\test") == ("C:", "/Users\\test")


def test_split_drive_windows_path_drive_only():
    """Test splitting Windows path with only drive and slash."""
    assert split_drive("C:/") == ("C:", "/")
    assert split_drive("C:\\") == ("C:", "\\")


def test_split_drive_posix_absolute_path():
    """Test splitting POSIX absolute path returns empty drive."""
    assert split_drive("/usr/local/bin") == ("", "/usr/local/bin")


def test_split_drive_posix_relative_path():
    """Test splitting POSIX relative path returns empty drive."""
    assert split_drive("relative/path/to/file") == ("", "relative/path/to/file")


def test_split_drive_empty_path():
    """Test splitting empty path returns empty drive and path."""
    assert split_drive("") == ("", "")


def test_split_drive_single_character_path():
    """Test splitting single character path returns empty drive."""
    assert split_drive("a") == ("", "a")


def test_split_drive_path_without_drive_letter():
    """Test splitting path without drive letter returns empty drive."""
    assert split_drive("Users/test") == ("", "Users/test")
    assert split_drive("folder\\file.txt") == ("", "folder\\file.txt")


def test_split_drive_drive_letter_without_slash():
    """Test splitting drive letter without slash returns empty drive."""
    assert split_drive("C:Users") == ("", "C:Users")
    assert split_drive("D:test") == ("", "D:test")


def test_split_drive_multiple_drive_letters():
    """Test splitting path with multiple potential drive letters."""
    # Only the first drive letter at the start should be recognized
    assert split_drive("C:/D:/test") == ("C:", "/D:/test")


def test_split_drive_drive_letter_at_end():
    """Test splitting path with drive-like pattern not at start."""
    assert split_drive("path/C:/test") == ("", "path/C:/test")


def test_split_drive_numeric_drive_letter():
    """Test splitting path with numeric drive letter."""
    assert split_drive("1:/test") == ("1:", "/test")
    assert split_drive("9:\\test") == ("9:", "\\test")


def test_split_drive_underscore_drive_letter():
    """Test splitting path with underscore drive letter."""
    assert split_drive("_:/test") == ("_:", "/test")


def test_split_drive_lowercase_drive_letter():
    """Test splitting path with lowercase drive letter."""
    assert split_drive("c:/Users/test") == ("c:", "/Users/test")
    assert split_drive("d:\\test") == ("d:", "\\test")


def test_split_drive_uppercase_drive_letter():
    """Test splitting path with uppercase drive letter."""
    assert split_drive("Z:/test") == ("Z:", "/test")
    assert split_drive("A:\\test") == ("A:", "\\test")


def test_split_drive_path_object_windows():
    """Test splitting PureWindowsPath object."""
    path = PureWindowsPath("C:/Users/test")
    # PureWindowsPath normalizes to backslashes when converted to string
    assert split_drive(path) == ("C:", "\\Users\\test")


def test_split_drive_path_object_posix():
    """Test splitting PurePosixPath object."""
    path = PurePosixPath("/usr/local/bin")
    assert split_drive(path) == ("", "/usr/local/bin")


def test_split_drive_path_object_relative():
    """Test splitting relative Path object."""
    path = Path("relative/path")
    assert split_drive(path) == ("", "relative/path")


def test_split_drive_complex_windows_path():
    """Test splitting complex Windows path."""
    assert split_drive("C:/Program Files/Application/test.exe") == (
        "C:",
        "/Program Files/Application/test.exe",
    )


def test_split_drive_windows_path_with_spaces():
    """Test splitting Windows path with spaces."""
    assert split_drive("C:/Program Files/test") == ("C:", "/Program Files/test")


def test_split_drive_windows_path_with_special_chars():
    """Test splitting Windows path with special characters."""
    assert split_drive("C:/test-file_123.txt") == ("C:", "/test-file_123.txt")


def test_split_drive_unc_path():
    """Test splitting UNC path returns empty drive."""
    assert split_drive("\\\\server\\share\\folder") == ("", "\\\\server\\share\\folder")


def test_split_drive_network_path():
    """Test splitting network path returns empty drive."""
    assert split_drive("//server/share/folder") == ("", "//server/share/folder")


def test_split_drive_file_protocol_path():
    """Test splitting file protocol path returns empty drive."""
    assert split_drive("file:///C:/test") == ("", "file:///C:/test")


def test_split_drive_path_starting_with_colon():
    """Test splitting path starting with colon returns empty drive."""
    assert split_drive(":/test") == ("", ":/test")


def test_split_drive_path_with_colon_in_middle():
    """Test splitting path with colon in middle returns empty drive."""
    assert split_drive("path:/test") == ("", "path:/test")


def test_split_drive_windows_root_path():
    """Test splitting Windows root path."""
    assert split_drive("C:/") == ("C:", "/")
    assert split_drive("D:\\") == ("D:", "\\")


def test_split_drive_windows_path_with_trailing_slash():
    """Test splitting Windows path with trailing slash."""
    assert split_drive("C:/Users/test/") == ("C:", "/Users/test/")


def test_split_drive_windows_path_with_multiple_slashes():
    """Test splitting Windows path with multiple consecutive slashes."""
    assert split_drive("C://Users//test") == ("C:", "//Users//test")
    assert split_drive("C:\\\\Users\\\\test") == ("C:", "\\\\Users\\\\test")


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


@given(st.text())
def test_split_drive_property_always_returns_tuple(path: str):
    """Property: split_drive always returns a tuple of two strings."""
    result = split_drive(path)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], str)


@given(st.text())
def test_split_drive_property_concatenation_equals_original(path: str):
    """Property: concatenating drive and path parts equals original path."""
    drive, rest = split_drive(path)
    assert drive + rest == path


@given(st.text())
def test_split_drive_property_drive_ends_with_colon(path: str):
    """Property: if drive is non-empty, it ends with a colon."""
    drive, _ = split_drive(path)
    if drive:
        assert drive.endswith(":")


@given(st.text())
def test_split_drive_property_drive_is_single_word_char(path: str):
    """Property: if drive is non-empty, it's a single word character followed by colon."""
    drive, _ = split_drive(path)
    if drive:
        assert len(drive) == 2
        assert drive[0].isalnum() or drive[0] == "_"
        assert drive[1] == ":"


@given(st.text())
def test_split_drive_property_rest_starts_with_slash_when_drive_present(path: str):
    """Property: when drive is present, rest starts with forward or backslash."""
    drive, rest = split_drive(path)
    if drive:
        assert rest.startswith(("/", "\\"))


@given(st.text())
def test_split_drive_property_no_drive_when_path_doesnt_match_pattern(path: str):
    """Property: drive is empty when path doesn't start with word+colon+slash."""
    drive, _ = split_drive(path)
    if drive:
        assert re.match(r"^\w:[/\\]", path)


@settings(max_examples=100)
@given(st.from_regex(r"^\w:[/\\].*"))
def test_split_drive_property_windows_paths_have_drive(path: str):
    """Property: paths matching Windows drive pattern have non-empty drive."""
    drive, rest = split_drive(path)
    assert drive
    assert rest
    assert len(drive) == 2
    assert drive[1] == ":"


@settings(max_examples=100)
@given(st.text().filter(lambda x: not re.match(r"^\w:[/\\]", x)))
def test_split_drive_property_non_windows_paths_have_no_drive(path: str):
    """Property: paths not matching Windows drive pattern have empty drive."""
    drive, rest = split_drive(path)
    assert not drive
    assert rest == path


@given(st.from_regex(r"^[A-Za-z]:[/\\].*"))
def test_split_drive_property_letter_drives_preserve_case(path: str):
    """Property: drive letter case is preserved in the result."""
    drive, _ = split_drive(path)
    if drive:
        original_letter = path[0]
        assert drive[0] == original_letter


@given(st.from_regex(r"^\w:[/\\].*"))
def test_split_drive_property_rest_includes_slash(path: str):
    """Property: the rest part includes the slash after the colon."""
    _, rest = split_drive(path)
    assert rest[0] in {"/", "\\"}


@given(st.text(min_size=0, max_size=10))
def test_split_drive_property_short_paths(path: str):
    """Property: split_drive handles very short paths correctly."""
    drive, rest = split_drive(path)
    assert drive + rest == path
    if len(path) >= 3 and path[1] == ":" and path[2] in {"/", "\\"}:
        assert drive == path[:2]
        assert rest == path[2:]
    else:
        assert not drive
        assert rest == path


@given(st.text())
def test_split_drive_property_unicode_paths(path: str):
    """Property: split_drive handles Unicode characters correctly."""
    drive, rest = split_drive(path)
    assert isinstance(drive, str)
    assert isinstance(rest, str)
    assert drive + rest == path


@given(st.text())
def test_split_drive_property_newline_and_special_chars(path: str):
    """Property: split_drive handles newlines and special characters correctly."""
    drive, rest = split_drive(path)
    assert drive + rest == path
    assert isinstance(drive, str)
    assert isinstance(rest, str)
