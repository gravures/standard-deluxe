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
"""Wrap module."""

from __future__ import annotations

from textwrap import TextWrapper

from deluxe.console.ansi import strip_esc


class AnsiTextWrapper(TextWrapper):
    """TextWrapper SubClass aware of ansi escape codes."""

    def _wrap_chunks(self, chunks: list[str]) -> list[str]:  # noqa: C901, PLR0912
        # sourcery skip: low-code-quality
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

        while chunks:  # noqa: PLR1702
            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line: list[str] = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            indent = self.subsequent_indent if lines else self.initial_indent

            # Maximum width for this line.
            width = self.width - len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and not strip_esc(chunks[-1]).strip() and lines:
                del chunks[-1]

            while chunks:
                # modified upstream code, not going to refactor for ambiguous variable name.
                _len = len(strip_esc(chunks[-1]))
                if cur_len + _len > width:
                    # Nope, this line is full
                    break
                cur_line.append(chunks.pop())
                cur_len += _len

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and len(strip_esc(chunks[-1])) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(len, cur_line))

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and not strip_esc(cur_line[-1]).strip():
                cur_len -= len(strip_esc(cur_line[-1]))
                del cur_line[-1]

            if cur_line:
                if (
                    self.max_lines is None  # noqa: PLR0916
                    or len(lines) + 1 < self.max_lines
                    or (
                        (
                            not chunks
                            or (
                                self.drop_whitespace and len(chunks) == 1 and not chunks[0].strip()
                            )
                        )
                        and cur_len <= width
                    )
                ):
                    # Convert current line back to a string and store it in
                    # list of all lines (return value).
                    lines.append(indent + "".join(cur_line))
                else:
                    while cur_line:
                        if (
                            strip_esc(cur_line[-1]).strip()
                            and cur_len + len(self.placeholder) <= width
                        ):
                            cur_line.append(self.placeholder)
                            lines.append(indent + "".join(cur_line))
                            break
                        cur_len -= len(strip_esc(cur_line[-1]))
                        del cur_line[-1]
                    else:
                        if lines:
                            prev_line = lines[-1].rstrip()
                            if len(strip_esc(prev_line)) + len(self.placeholder) <= self.width:
                                lines[-1] = prev_line + self.placeholder
                                break
                        lines.append(indent + self.placeholder.lstrip())
                    break
        return lines
