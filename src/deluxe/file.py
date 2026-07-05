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
# ruff: noqa: UP031
"""File operations and utilities module.

This module provides a collection of functions for working with files and paths
across different operating systems. It includes utilities for path manipulation,
file type detection, and system-specific operations.
"""

from __future__ import annotations

import os
import re
import struct
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from deluxe.types import FilePath


__all__ = (
    "get_pe_version",
    "is_binary",
    "is_exec",
    "is_winexec",
    "is_winpath",
    "split_drive",
)


_POSIX: bool = os.name == "posix"


def split_drive(path: FilePath[str]) -> tuple[str, str]:
    """Split a filepath into its drive part and the rest of the path.

    Args:
        path (:class:`FilePath`): The filepath to split.

    Returns:
        tuple[str, str]: A tuple containing the drive and the rest of the path.
    """
    path = str(path)
    if match := re.search(r"^\w:[/\\]", path):
        return (path[: match.end() - 1], path[match.end() - 1 :])
    return ("", path)


def is_winpath(path: FilePath[str]) -> bool:
    """Check if the given path is a Windows path.

    Args:
        path (:class:`FilePath`): The path to check.

    Returns:
        bool: on windows if the path is not a PurePosixPath always return True.
        On POSIX return True if the path is an instance of PureWindowsPath,
        otherwise test the presence of a drive letter, UNC path double back slash
        and forward slash as guessing.
    """
    if not _POSIX:  # pragma: posix no cover
        return not isinstance(path, PurePosixPath)

    if isinstance(path, PureWindowsPath):
        return True

    drv, pth = split_drive(path)

    return True if bool(drv) and drv != "file" else bool(pth.startswith("\\\\"))


def is_binary(path: FilePath[str]) -> bool:
    """Test if path point to a binary file.

    Args:
        path (:class:`FilePath`): The path to check.

    Returns:
        bool: True if file is binary, False otherwise.
    """
    # NOTE: https://gist.github.com/magnetikonline/7a21ec5f5bcdbf7adb92f9d617e6198f
    #        https://github.com/djmattyg007/python-isbinary
    if not (path_ := Path(path)).is_file():
        return False

    read_bytes = 512
    char_threshold = 0.3
    text_characters = dict.fromkeys(
        list(range(32, 127)) + [ord(c) for c in ["\x08", "\x0c", "\n", "\r", "\t"]]
    )
    with path_.open("r", encoding="ISO-8859-1") as fh:
        file_data = fh.read(read_bytes)

    # store chunk length read
    data_length = len(file_data)
    if not data_length:  # empty files considered text
        return False

    if "\x00" in file_data:  # file containing null bytes is binary
        return True

    # remove all text characters from file chunk, get remaining length
    binary_length = len(file_data.translate(text_characters))

    # if percentage of binary characters above threshold, binary file
    return (float(binary_length) / data_length) >= char_threshold


def is_exec(path: FilePath[str]) -> bool:
    """Check if a file has the executable permission set.

    Checks if the path corresponds to an existing file
    and if this file has the executable permission set.

    Args:
        path (:class:`FilePath`): The path to check for executable permission.

    Returns:
        bool: True if the file has the executable permission, False otherwise.
              If the file does not exist or is not a regular file, the function
              returns False.
    """
    return (path := Path(path).resolve()).is_file() and os.access(path, os.X_OK)


def is_winexec(path: FilePath[str]) -> bool:
    """Check if a file has an extension associated with executable files on Windows.

    The function checks if the file has a suffix (extension) that matches any of the
    Windows executable extensions commonly found on Windows platforms. The extensions
    considered as Windows executable files are: 'COM', 'EXE', 'BAT', 'CMD', 'VBS',
    'VBE', 'JS', 'JSE', 'WSF', 'WSH', 'MSC'. The comparison of the suffix is
    case-insensitive (capitalized) to handle different cases.

    Args:
        path (:class:`FilePath`): The path to check for the Windows
        executable extension.

    Returns:
        bool: True if the file has a Windows executable extension, False otherwise.
              If the file does not exist or is not a regular file, the function
              returns False
    """
    return bool(
        (path := Path(path).resolve()).is_file()
        and path.suffix.upper()
        in {
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
        }
    )


def get_pe_version(path: FilePath[str]) -> str | None:
    r"""Extract the version information from a Portable Executable (PE) file.

    Reads the specified Portable Executable (PE) file and extracts its version
    information using the Windows-specific 'VS_VERSION_INFO' structure.
    The function returns the version information as a string in the format
    'Major.Minor.Patch.Build' if available.

    Args:
        path (:class:`FilePath`): The path to the Portable Executable (PE) file.

    Returns:
        str or None: The version information of the PE file if available,
        None otherwise.

    Example:
        >>> pe_file_path = "C:\\path\\to\\app.exe"
        >>> get_pe_version(pe_file_path)
        '1.2.3.4'

    Note:
        - The function reads the entire file into memory, so it may not be suitable
          for large binaries.
        - The function returns None if the 'VS_VERSION_INFO' structure is not found
          or if an error occurs.
    """
    if not Path(path).is_file():
        return None

    # http://windowssdk.msdn.microsoft.com/en-us/library/ms646997.aspx
    sig = struct.pack("32s", "VS_VERSION_INFO".encode("utf-16-le"))

    # NOTE: there is a pe file module available on pypi
    #       https://github.com/erocarrera/pefile

    # NOTE: This pulls the whole file into memory,
    #       so not very feasible for large binaries.
    data = Path(path).read_bytes()
    offset = data.find(sig)
    if offset == -1:
        return None

    try:
        data = data[offset + 32 : offset + 32 + (13 * 4)]
        version_struct = struct.unpack("13I", data)
    except struct.error:
        return None

    ver_ms, ver_ls = version_struct[4], version_struct[5]
    return "%d.%d.%d.%d" % (
        ver_ls & 0x0000FFFF,
        (ver_ms & 0xFFFF0000) >> 16,
        ver_ms & 0x0000FFFF,
        (ver_ls & 0xFFFF0000) >> 16,
    )
