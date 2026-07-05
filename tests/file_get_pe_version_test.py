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
"""Tests for get_pe_version function."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from deluxe.file import get_pe_version

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _create_pe_signature(version_info: bytes | None = None) -> bytes:
    """Create a binary blob containing the VS_VERSION_INFO signature.

    Args:
        version_info: Optional version info bytes to append after signature.

    Returns:
        bytes: Binary data containing the PE signature.
    """
    sig = struct.pack("32s", "VS_VERSION_INFO".encode("utf-16-le"))
    if version_info is not None:
        return sig + version_info
    return sig


def _create_version_info(
    major_ms: int = 0,
    minor_ms: int = 1,
    major_ls: int = 0,
    minor_ls: int = 2,
) -> bytes:
    """Create a valid VS_VERSION_INFO structure.

    The version is extracted from ver_ms (index 4) and ver_ls (index 5):
    - ver_ls & 0x0000FFFF           → field 0 of version string
    - (ver_ms & 0xFFFF0000) >> 16   → field 1 of version string
    - ver_ms & 0x0000FFFF           → field 2 of version string
    - (ver_ls & 0xFFFF0000) >> 16   → field 3 of version string

    Args:
        major_ms: Major component of ver_ms (high word).
        minor_ms: Minor component of ver_ms (low word).
        major_ls: Major component of ver_ls (high word).
        minor_ls: Minor component of ver_ls (low word).

    Returns:
        bytes: 52 bytes (13 unsigned ints) representing the version structure.
    """
    ver_ms = (major_ms << 16) | minor_ms
    ver_ls = (major_ls << 16) | minor_ls
    # Pad with zeros for the 13 unsigned ints (indices 0-3 and 6-12 are zero)
    return struct.pack("13I", 0, 0, 0, 0, ver_ms, ver_ls, 0, 0, 0, 0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Example-based tests
# ---------------------------------------------------------------------------


def test_get_pe_version_non_existent_file(tmp_path: Path):
    """Test get_pe_version returns None for a non-existent file."""
    non_existent_file = tmp_path / "non_existent.exe"
    assert get_pe_version(non_existent_file) is None


def test_get_pe_version_directory(tmp_path: Path):
    """Test get_pe_version returns None for a directory path."""
    assert get_pe_version(tmp_path) is None


def test_get_pe_version_empty_file(tmp_path: Path):
    """Test get_pe_version returns None for an empty file."""
    empty_file = tmp_path / "empty.exe"
    empty_file.touch()
    assert get_pe_version(empty_file) is None


def test_get_pe_version_file_without_signature(tmp_path: Path):
    """Test get_pe_version returns None for a file without VS_VERSION_INFO."""
    file_without_sig = tmp_path / "no_sig.exe"
    file_without_sig.write_bytes(b"This file has no PE signature.")
    assert get_pe_version(file_without_sig) is None


def test_get_pe_version_valid_version(tmp_path: Path):
    """Test get_pe_version extracts correct version from valid PE data."""
    # ver_ms = (1 << 16) | 2 = 0x00010002
    # ver_ls = (0 << 16) | 3 = 0x00000003
    # Expected: "3.1.2.0"
    #   - ver_ls & 0x0000FFFF = 3
    #   - (ver_ms & 0xFFFF0000) >> 16 = 1
    #   - ver_ms & 0x0000FFFF = 2
    #   - (ver_ls & 0xFFFF0000) >> 16 = 0
    version_info = _create_version_info(major_ms=1, minor_ms=2, major_ls=0, minor_ls=3)
    data = _create_pe_signature(version_info)

    pe_file = tmp_path / "valid.exe"
    pe_file.write_bytes(data)

    assert get_pe_version(pe_file) == "3.1.2.0"


def test_get_pe_version_all_zeros(tmp_path: Path):
    """Test get_pe_version with all-zero version fields."""
    version_info = _create_version_info(major_ms=0, minor_ms=0, major_ls=0, minor_ls=0)
    data = _create_pe_signature(version_info)

    pe_file = tmp_path / "zero.exe"
    pe_file.write_bytes(data)

    assert get_pe_version(pe_file) == "0.0.0.0"  # noqa: S104


def test_get_pe_version_large_version_numbers(tmp_path: Path):
    """Test get_pe_version with large version numbers."""
    # ver_ms = (65535 << 16) | 65535 = 0xFFFFFFFF
    # ver_ls = (65535 << 16) | 65535 = 0xFFFFFFFF
    # Expected: "65535.65535.65535.65535"
    version_info = _create_version_info(
        major_ms=65535, minor_ms=65535, major_ls=65535, minor_ls=65535
    )
    data = _create_pe_signature(version_info)

    pe_file = tmp_path / "large.exe"
    pe_file.write_bytes(data)

    assert get_pe_version(pe_file) == "65535.65535.65535.65535"


def test_get_pe_version_signature_at_offset(tmp_path: Path):
    """Test get_pe_version when signature is not at the beginning of file."""
    # Add some padding before the signature
    padding = b"\x00" * 100
    version_info = _create_version_info(major_ms=5, minor_ms=10, major_ls=20, minor_ls=30)
    data = padding + _create_pe_signature(version_info)

    pe_file = tmp_path / "offset.exe"
    pe_file.write_bytes(data)

    # Expected: "30.5.10.20"
    assert get_pe_version(pe_file) == "30.5.10.20"


def test_get_pe_version_string_path(tmp_path: Path):
    """Test get_pe_version accepts a string path."""
    version_info = _create_version_info(major_ms=1, minor_ms=0, major_ls=0, minor_ls=1)
    data = _create_pe_signature(version_info)

    pe_file = tmp_path / "string_path.exe"
    pe_file.write_bytes(data)

    assert get_pe_version(str(pe_file)) == "1.1.0.0"


def test_get_pe_version_path_object(tmp_path: Path):
    """Test get_pe_version accepts a Path object."""
    version_info = _create_version_info(major_ms=2, minor_ms=3, major_ls=4, minor_ls=5)
    data = _create_pe_signature(version_info)

    pe_file = tmp_path / "path_obj.exe"
    pe_file.write_bytes(data)

    assert get_pe_version(pe_file) == "5.2.3.4"


def test_get_pe_version_truncated_data_raises(tmp_path: Path):
    """Test get_pe_version raises struct.error when data after signature is too short."""
    sig = struct.pack("32s", "VS_VERSION_INFO".encode("utf-16-le"))
    # Only add a few bytes after signature, not enough for 13 unsigned ints (52 bytes)
    truncated = sig + b"\x00" * 10

    pe_file = tmp_path / "truncated.exe"
    pe_file.write_bytes(truncated)
    assert get_pe_version(pe_file) is None
