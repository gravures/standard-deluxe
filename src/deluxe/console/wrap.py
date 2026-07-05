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
"""Text wrapping utilities with ANSI escape code awareness.

This module provides :class:`AnsiTextWrapper`, a subclass of
:class:`textwrap.TextWrapper` that correctly calculates string
lengths by ignoring ANSI escape sequences during wrapping.
"""

from __future__ import annotations

from textwrap import TextWrapper

from deluxe.console.ansi import length, strip_esc


__all__ = ("AnsiTextWrapper",)


class AnsiTextWrapper(TextWrapper):
    """A :class:`~textwrap.TextWrapper` subclass aware of ANSI escape codes.

    This wrapper correctly measures string widths by stripping ANSI escape
    sequences before computing lengths, ensuring that colored or styled text
    wraps at the correct positions.
    """

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

    @staticmethod
    def _visible_break_pos(text: str, max_visible: int) -> int:
        """Return the character index where visible length reaches *max_visible*.

        ANSI escape sequences are treated as zero-width: the index returned
        always falls *outside* any escape sequence so that slicing never
        splits one in the middle.
        """
        visible = 0
        i = 0
        n = len(text)
        while i < n and visible < max_visible:
            if text[i] == "\x1b" and i + 1 < n:
                next_ch = text[i + 1]
                if next_ch == "[":
                    # CSI: ESC [ <params> <command>
                    i += 2
                    while i < n and text[i] not in {"J", "K", "m"}:
                        i += 1
                    i += 1  # skip command character
                elif next_ch == "]":
                    # OSC: ESC ] <content> BEL
                    i += 2
                    while i < n and text[i] != "\a":
                        i += 1
                    i += 1  # skip BEL
                else:
                    # Unknown escape: count as visible characters
                    visible += 2
                    i += 2
            else:
                visible += 1
                i += 1
        return i

    def _handle_long_word(
        self, reversed_chunks: list[str], cur_line: list[str], cur_len: int, width: int
    ) -> None:
        """Break a long word respecting ANSI escape sequence boundaries.

        Overrides the inherited :meth:`TextWrapper._handle_long_word` to
        measure visible width via :func:`length` instead of :func:`len`,
        preventing escape sequences from being split across lines.
        """
        space_left = width - cur_len

        if self.break_long_words and space_left > 0:
            chunk = reversed_chunks[-1]
            end = self._visible_break_pos(chunk, space_left)

            # Respect hyphen-breaking if the visible prefix contains a
            # suitable hyphen position.
            if self.break_on_hyphens and length(chunk) > space_left:
                visible_prefix = strip_esc(chunk[:end])
                hyphen = visible_prefix.rfind("-", 0, len(visible_prefix))
                if hyphen > 0 and any(c != "-" for c in visible_prefix[:hyphen]):
                    end = self._visible_break_pos(chunk, hyphen + 1)

            cur_line.append(chunk[:end])
            reversed_chunks[-1] = chunk[end:]

        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

    def _wrap_chunks(self, chunks: list[str]) -> list[str]:
        """Wrap a sequence of text chunks into lines of limited width.

        Processes a list of text chunks and returns a list of lines, each at
        most ``self.width`` characters wide. Chunks correspond roughly to words
        and the whitespace between them: each chunk is indivisible (unless
        :attr:`break_long_words` is ``False``), but a line break can occur
        between any two chunks. Chunks should not contain internal whitespace;
        each chunk is either all whitespace or a "word". Whitespace chunks are
        removed from line beginnings and endings, but otherwise whitespace is
        preserved.

        Args:
            chunks (:obj:`list` [:class:`str`]): A list of text chunks to be
                wrapped.

        Returns:
            :obj:`list` [:class:`str`]: A list of wrapped lines.

        Raises:
            ValueError: If ``self.width`` is less than or equal to zero,
                or if the placeholder is too large for the maximum width.
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
            if length(prev_line) + len(self.placeholder) <= self.width:  # pragma: no cover
                lines[-1] = prev_line + self.placeholder
                return
        lines.append(indent + self.placeholder.lstrip())
        return
