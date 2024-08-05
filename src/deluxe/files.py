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
"""File module."""

from __future__ import annotations

import os
import struct
from os import PathLike
from pathlib import Path, PureWindowsPath
from typing import Any, Union


POSIX: bool = os.name == "posix"

FilePath = Union[str, PathLike[Any]]


def is_winpath(path: FilePath) -> bool:
    """Tests if path is a windows path.

    Returns:
        bool: True if path is a windows file system path, False otherwise.
    """
    return bool(Path(path).drive) or issubclass(path.__class__, PureWindowsPath)


def is_binary(path: FilePath) -> bool:
    """Test if path point to a binary file.

    Returns:
        bool: True if file is binary, False otherwise.
    """
    # NOTES: https://gist.github.com/magnetikonline/7a21ec5f5bcdbf7adb92f9d617e6198f
    #        https://github.com/djmattyg007/python-isbinary
    _path = Path(path)
    if not _path.is_file():
        return False

    read_bytes = 512
    char_threshold = 0.3
    text_characters = dict.fromkeys(
        list(range(32, 127)) + [ord(c) for c in ["\x08", "\x0c", "\n", "\r", "\t"]]
    )
    with _path.open("r", encoding="ISO-8859-1") as fh:
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


def is_exec(path: FilePath) -> bool:
    """Check if a file has the executable permission set.

    Checks if the path corresponds to an existing file
    and if this file has the executable permission set.

    Args:
        path: The file path to check
        for executable permission.

    Returns:
        bool: True if the file has the executable permission, False otherwise.
              If the file does not exist or is not a regular file, the function
              returns False.
    """
    path = Path(path).resolve()
    return path.is_file() and os.access(path, os.X_OK)


def is_winexec(path: FilePath) -> bool:
    """Check if a file has an extension associated with executable files on Windows.

    The function checks if the file has a suffix (extension) that matches any of the
    Windows executable extensions commonly found on Windows platforms. The extensions
    considered as Windows executable files are: 'COM', 'EXE', 'BAT', 'CMD', 'VBS',
    'VBE', 'JS', 'JSE', 'WSF', 'WSH', 'MSC'. The comparison of the suffix is
    case-insensitive (capitalized) to handle different cases.

    Args:
        path: The file path to check for the Windows
        executable extension.

    Returns:
        bool: True if the file has a Windows executable extension, False otherwise.
              If the file does not exist or is not a regular file, the function
              returns False
    """
    path = Path(path).resolve()
    return bool(
        path.is_file()
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


def get_pe_version(file: FilePath) -> str | None:
    r"""Extract the version information from a Portable Executable (PE) file.

    Reads the specified Portable Executable (PE) file and extracts its version
    information using the Windows-specific 'VS_VERSION_INFO' structure.
    The function returns the version information as a string in the format
    'Major.Minor.Patch.Build' if available.

    Args:
        file: The path to the Portable Executable (PE) file.

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
    if not Path(file).is_file():
        return None

    # http://windowssdk.msdn.microsoft.com/en-us/library/ms646997.aspx
    sig = struct.pack("32s", "VS_VERSION_INFO".encode("utf-16-le"))
    version = None

    # NOTE: there is a pefile module available on pypi
    #       https://github.com/erocarrera/pefile

    # NOTE: This pulls the whole file into memory,
    #       so not very feasible for large binaries.
    with Path(file).open("rb") as f:
        data = f.read()
        offset = data.find(sig)
        if offset != -1:
            data = data[offset + 32 : offset + 32 + (13 * 4)]
            version_struct = struct.unpack("13I", data)
            ver_ms, ver_ls = version_struct[4], version_struct[5]
            version = "%d.%d.%d.%d" % (
                ver_ls & 0x0000FFFF,
                (ver_ms & 0xFFFF0000) >> 16,
                ver_ms & 0x0000FFFF,
                (ver_ls & 0xFFFF0000) >> 16,
            )
    return version


def mount_point(path: FilePath) -> Path:
    r"""Finds the mount point (root) of the filesystem containing the given path.

    Takes a file path and traverses up the directory tree until it finds
    the mount point (root) of the filesystem containing the path.

    Args:
        path: The file path for which to find the mount point.

    Returns:
        Path: The mount point (root) of the filesystem containing the given path.

    Raises:
        NotImplementedError: If called from Winodws platform or If the input
        path is a Windows filesystem path (for Windows-specific paths).

    Examples:
        >>> mount_point("/home/user/documents/file.txt")
        PosixPath('/')

        >>> mount_point("/mnt/data/photos/image.jpg")
        PosixPath('/mnt')

        >>> mount_point("C:\\projects\\code\\script.py")
        WindowsPath('C:/')
    """
    path = Path(path).expanduser().absolute()
    if not POSIX or is_winpath(path):
        msg = "path should not be a Windows filesystem path"
        raise NotImplementedError(msg)
    while not path.is_mount():
        path = path.parent
    return path
