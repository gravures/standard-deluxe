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
#
#
# The AnsiTextWrapper class in this module is based on code
# from argparse-color-formatter project hosted here:
# https://github.com/arrai-innovations/argparse-color-formatter
#
# This code was adapted to use our library plus some refactoring were done.
# Copyright (c) 2017, Emergence by Design Inc.
# Copyright (c) 2024, Arrai Innovations Inc.
"""Wrap module."""

from __future__ import annotations

from textwrap import TextWrapper

from deluxe.console.ansi import length, strip_esc


class AnsiTextWrapper(TextWrapper):
    """TextWrapper SubClass aware of ansi escape codes."""

    def _should_add_line(
        self, lines: list[str], chunks: list[str], cur_len: int, width: int
    ) -> bool:
        return (
            self.max_lines is None
            or len(lines) + 1 < self.max_lines
            or (
                (
                    not chunks
                    or (self.drop_whitespace and len(chunks) == 1 and not chunks[0].strip())
                )
                and cur_len <= width
            )
        )

    def _wrap_chunks(self, chunks: list[str]) -> list[str]:
        """Wrap a sequence of text chunks.

        Wrap a sequence of text chunks and return a list of lines of
        length 'self.width' or less.  (If 'break_long_words' is false,
        some lines may be longer than this.)  Chunks correspond roughly
        to words and the whitespace between them: each chunk is
        indivisible (modulo 'break_long_words'), but a line break can
        come between any two chunks.  Chunks should not have internal
        whitespace; ie. a chunk is either all whitespace or a "word".
        Whitespace chunks will be removed from the beginning and end of
        lines, but apart from that whitespace is preserved.

        Args:
            chunks: A list of text chunks to be wrapped.

        Returns:
            A list of wrapped lines.

        Raises:
            ValueError: If the width is invalid.
        """
        lines: list[str] = []
        if self.width <= 0:
            msg = f"invalid width {self.width!r} (must be > 0)"
            raise ValueError(msg)

        if self.max_lines is not None:
            indent = self.subsequent_indent if self.max_lines > 1 else self.initial_indent
            if len(indent) + len(self.placeholder.lstrip()) > self.width:
                msg = "placeholder too large for max width"
                raise ValueError(msg)

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:
            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line: list[str] = []
            cur_len = 0
            indent = self.subsequent_indent if lines else self.initial_indent
            width = self.width - len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and not strip_esc(chunks[-1]).strip() and lines:
                del chunks[-1]

            while chunks:
                len_ = length(chunks[-1])
                if cur_len + len_ > width:
                    break
                cur_line.append(chunks.pop())
                cur_len += len_

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and length(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(length, cur_line))

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and not strip_esc(cur_line[-1]).strip():
                cur_len -= len(strip_esc(cur_line[-1]))
                del cur_line[-1]

            if cur_line:
                if self._should_add_line(lines, chunks, cur_len, width):
                    # Convert current line back to a string and store it in
                    # list of all lines (return value).
                    lines.append(indent + "".join(cur_line))
                else:
                    self._add_placeholder_line(lines, cur_line, cur_len, width, indent)
                    break
        return lines

    def _add_placeholder_line(
        self, lines: list[str], cur_line: list[str], cur_len: int, width: int, indent: str
    ) -> None:
        while cur_line:
            if strip_esc(cur_line[-1]).strip() and cur_len + len(self.placeholder) <= width:
                cur_line.append(self.placeholder)
                lines.append(indent + "".join(cur_line))
                return
            cur_len -= length(cur_line[-1])
            del cur_line[-1]
        if lines:
            prev_line = lines[-1].rstrip()
            if length(prev_line) + len(self.placeholder) <= self.width:
                lines[-1] = prev_line + self.placeholder
                return
        lines.append(indent + self.placeholder.lstrip())
        return
