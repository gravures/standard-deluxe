# noqa: INP001
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

from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from os import PathLike


def is_binary(path: PathLike[str]) -> bool:
    """Return True if file is binary, False otherwise.

    NOTES: https://gist.github.com/magnetikonline/7a21ec5f5bcdbf7adb92f9d617e6198f
           https://github.com/djmattyg007/python-isbinary
    """
    _path = Path(path)
    if not _path.is_file():
        msg = f"{_path} is not a file."
        raise AttributeError(msg)

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
