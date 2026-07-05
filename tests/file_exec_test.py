from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

# Assume the code under test is in 'deluxe.files'
from deluxe.file import is_exec, is_winexec
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

if TYPE_CHECKING:
    from pathlib import Path


# On Windows, is_exec delegates to is_winexec (extension-based detection).
# On POSIX, is_exec checks the execute permission bit.
# Tests use filenames that are executable on both platforms.
_EXEC_NAME = "executable_script.exe" if os.name == "nt" else "executable_script"
_EXEC_EXT = ".exe" if os.name == "nt" else ".sh"


# --- Tests for is_exec() ---


def test_property_is_exec_for_non_existent_path(tmp_path: Path):
    """
    Property: is_exec must return False for a path that does not exist.
    """
    non_existent_file = tmp_path / "this_file_does_not_exist"
    assert not is_exec(non_existent_file)


def test_property_is_exec_for_directory(tmp_path: Path):
    """
    Property: is_exec must return False for a path that is a directory.
    """
    assert not is_exec(tmp_path)


def test_property_is_exec_for_file_with_permission(tmp_path: Path):
    """
    Property: is_exec must return True for a file with execute permissions.
    """
    executable_file = tmp_path / _EXEC_NAME
    executable_file.touch()
    # Add execute permission for the owner (relevant on POSIX)
    current_mode = executable_file.stat().st_mode
    executable_file.chmod(current_mode | stat.S_IXUSR)
    assert is_exec(executable_file)


def test_property_is_exec_for_file_without_permission(tmp_path: Path):
    """
    Property: is_exec must return False for a file without execute permission
    or without a recognized executable extension.
    """
    non_executable_file = tmp_path / "non_executable.txt"
    non_executable_file.touch()
    # Remove all execute bits on POSIX (no-op on Windows, but harmless)
    current_mode = non_executable_file.stat().st_mode
    non_executable_file.chmod(current_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
    assert not is_exec(non_executable_file)


def test_is_exec_with_string_path(tmp_path: Path):
    """
    Property: is_exec must accept a string path and return True for executable file.
    """
    executable_file = tmp_path / f"script{_EXEC_EXT}"
    executable_file.touch()
    executable_file.chmod(executable_file.stat().st_mode | stat.S_IXUSR)
    # Pass as string, not Path object
    assert is_exec(str(executable_file))


def test_is_exec_with_symlink_to_executable(tmp_path: Path):
    """
    Property: is_exec must return True for a symlink pointing to an executable file.
    """
    executable_file = tmp_path / f"original{_EXEC_EXT}"
    executable_file.touch()
    executable_file.chmod(executable_file.stat().st_mode | stat.S_IXUSR)
    symlink = tmp_path / f"link{_EXEC_EXT}"
    symlink.symlink_to(executable_file)
    assert is_exec(symlink)


def test_is_exec_with_symlink_to_non_executable(tmp_path: Path):
    """
    Property: is_exec must return False for a symlink pointing to a non-executable file.
    """
    non_executable_file = tmp_path / "data.txt"
    non_executable_file.touch()
    current_mode = non_executable_file.stat().st_mode
    non_executable_file.chmod(current_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
    symlink = tmp_path / "link.txt"
    symlink.symlink_to(non_executable_file)
    assert not is_exec(symlink)


def test_is_exec_with_broken_symlink(tmp_path: Path):
    """
    Property: is_exec must return False for a broken symlink (target does not exist).
    """
    broken_symlink = tmp_path / "broken_link"
    broken_symlink.symlink_to(tmp_path / "non_existent_target")
    assert not is_exec(broken_symlink)


def test_is_exec_with_empty_file(tmp_path: Path):
    """
    Property: is_exec must return False for an empty file without execute permission.
    """
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    current_mode = empty_file.stat().st_mode
    empty_file.chmod(current_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
    assert not is_exec(empty_file)


def test_is_exec_resolves_path(tmp_path: Path):
    """
    Property: is_exec must resolve the path before checking (e.g., handle .. in path).
    """
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    executable_file = subdir / f"script{_EXEC_EXT}"
    executable_file.touch()
    executable_file.chmod(executable_file.stat().st_mode | stat.S_IXUSR)
    # Use path with ".." component
    path_with_dotdot = tmp_path / "subdir" / ".." / "subdir" / f"script{_EXEC_EXT}"
    assert is_exec(path_with_dotdot)


# --- Tests for is_winexec() ---

VALID_WIN_EXTENSIONS = [
    ".COM",
    ".EXE",
    ".BAT",
    ".CMD",
    ".VBS",
    ".VBE",
    ".JS",
    ".JSE",
    ".WSF",
    ".WSH",
    ".MSC",
]

# Strategy for valid Windows executable extensions
valid_extensions_strategy = st.sampled_from(VALID_WIN_EXTENSIONS)

# Strategy for file extensions that are not considered Windows executables
invalid_extensions_strategy = (
    st
    .text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=5)
    .map(lambda s: f".{s}")
    .filter(lambda ext: ext.upper() not in VALID_WIN_EXTENSIONS)
)

# Strategy for a valid filename part
filename_strategy = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10
)


def test_property_is_winexec_for_non_existent_path(tmp_path: Path):
    """
    Property: is_winexec must return False for a path that does not exist.
    """
    non_existent_file = tmp_path / "non_existent.exe"
    assert not is_winexec(non_existent_file)


def test_property_is_winexec_for_directory(tmp_path: Path):
    """
    Property: is_winexec must return False for a path that is a directory.
    """
    assert not is_winexec(tmp_path)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=filename_strategy, ext=valid_extensions_strategy)
def test_property_is_winexec_true_for_valid_extensions(tmp_path: Path, name: str, ext: str):
    """
    Property: is_winexec must return True for any file ending in a valid
    Windows executable extension, regardless of case.
    """
    test_file = tmp_path / f"{name}{ext}"
    test_file.touch()
    assert is_winexec(test_file)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=filename_strategy, ext=invalid_extensions_strategy)
def test_property_is_winexec_false_for_invalid_extensions(tmp_path: Path, name: str, ext: str):
    """
    Property: is_winexec must return False for files with extensions not in
    the recognized list.
    """
    test_file = tmp_path / f"{name}{ext}"
    test_file.touch()
    assert not is_winexec(test_file)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=filename_strategy)
def test_property_is_winexec_false_for_file_with_no_extension(tmp_path: Path, name: str):
    """
    Property: is_winexec must return False for a file that has no extension.
    """
    test_file = tmp_path / name
    test_file.touch()
    assert not is_winexec(test_file)
