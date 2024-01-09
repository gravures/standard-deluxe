# Copyright (c) 2024 - Gilles Coissac
# See end of file for extended copyright information
"""Collections module."""

from __future__ import annotations

from typing import Generator, Protocol, Self, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class Nested(Protocol):
    """Nested Protocol."""

    @property
    def parent(self) -> Self | None:
        """Parent property."""
        ...

    @property
    def level(self) -> int:
        """Level property."""
        ...


class Node:
    """Tree Node Class."""

    __slots__ = ("_parent", "_children", "_data")

    def __init__(self, data: object) -> None:
        self._parent: Self | None = None
        self._data = data
        self._children = []

    @property
    def parent(self) -> Self | None:
        """Parent property."""
        return self._parent

    @property
    def children(self) -> Generator:
        """Children property."""
        yield from self._children

    @property
    def ancestors(self) -> Generator:
        """Parent property."""
        ancestor = self.parent
        while ancestor:
            _tmp = ancestor
            ancestor = ancestor.parent
            yield _tmp

    def add(self, *items: Node | object) -> None:
        """Adds item(s) to this Node."""
        for item in items:
            node = item if isinstance(item, Node) else Node(item)
            node._parent = self
            self._children.append(node)


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
# along with Lyndows. If not, see <https://www.gnu.org/licenses/>
