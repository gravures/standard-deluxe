# Copyright (c) 2025 - Gilles Coissac
# This file is part of bunu program.
#
# bunu is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# bunu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bunu. If not, see <https://www.gnu.org/licenses/>
#
from collections.abc import Hashable, Iterator
from types import NoneType
from typing import (
    ClassVar,
    Generic,
    Literal,
    Self,
    TypeAlias,
    TypeVar,
    final,
    overload,
)

__all__ = ("Cursor", "Tree")

_VT = TypeVar("_VT", bound=Hashable)
_CT = TypeVar("_CT", bound=Hashable)
Slice: TypeAlias = int | slice | None

@final
class Cursor(Generic[_CT]):
    def __new__(cls, *keys: _CT | Cursor[_CT]) -> Self: ...
    def __getitem__(self, index: int | slice) -> _CT: ...
    def __len__(self) -> int: ...
    def __contains__(self, value: object) -> bool: ...
    def __iter__(self) -> Iterator[_CT]: ...
    def __eq__(self, value: object) -> bool: ...
    def __hash__(self) -> int: ...

class Tree(Generic[_VT]):
    """A General Tree datatype.

    Implements: Container, Iterable, Sized, Collection.
    """

    __hash__: ClassVar[NoneType] = None  # pyright: ignore[reportIncompatibleMethodOverride]
    __reversed__: ClassVar[NoneType] = None

    parent: Tree[_VT]
    """Parent's Node."""

    def __new__(cls) -> Self: ...
    def __init__(self) -> None: ...
    def __matmul__(self, args: _VT | tuple[_VT]) -> Cursor[_VT]:
        """Returns a new `Cursor`."""

    def __invert__(self) -> Cursor[_VT]:
        """Returns this node's `Cursor`.

        Cursor is a tuple like object, values of `Cursor` represents
        a path to the node from the Tree's `root`.
        """

    @property
    def value(self) -> _VT:
        """This node's value.

        Raises:
            AttributeError: if self is the base container.
        """

    @property
    def root(self) -> Tree[_VT] | None:
        """Top `Tree`'s node."""

    @property
    def depth(self) -> int:
        """Number of nodes from `Tree`'s `root` to self."""

    @property
    def height(self) -> int:
        """Number of nodes from self to the deepest contained `leaf` node."""

    @property
    def diameter(self) -> int: ...
    def __len__(self) -> int:
        """Returns the total of self contained nodes."""

    def __contains__(self, value: _VT) -> bool: ...
    @overload
    def add(self, value: _VT) -> None: ...
    @overload
    def add(self, value: _VT, cursor: Cursor[_VT], parent: bool = False) -> None: ...
    def add(self, value: _VT, cursor: Cursor[_VT] | None = None, parent: bool = False) -> None: ...
    def clear(self) -> None:
        """Removes all self contained nodes."""

    def __setitem__(self, key: _VT | Cursor[_VT], value: _VT) -> None: ...
    def __getitem__(self, key: _VT | Cursor[_VT]) -> Tree[_VT]: ...
    def __delitem__(self, key: _VT | Cursor[_VT]) -> None: ...
    def __iter__(self) -> Iterator[_VT]:
        """Returns an `Iterator` over self contained node's value in a bfs traversal oder."""

    def parents(self) -> tuple[_VT, ...]:
        """Returns a `tuple` of node from root to this node."""

    def children(self) -> Iterator[_VT]:
        """Returns an `Iterator` over children node's value."""

    def dfs(
        self, order: Literal["pre", "in", "post"] = "pre", reverse: bool = False
    ) -> Iterator[_VT]:
        """Returns an `Iterator` over self contained node's value in a depth first traversal order."""  # noqa: E501

    def bfs(self) -> Iterator[_VT]:
        """Returns an `Iterator` over self contained node's value in a bfs traversal oder."""

    def leaves(self, depth: Slice = None) -> Iterator[_VT]:
        """Returns an `Iterator` over leaf node's values."""

    def branches(self, depth: Slice = None) -> Iterator[_VT]:
        """Returns an `Iterator` over branche node's values."""

    def siblings(self) -> Iterator[_VT]:
        """Returns an `Iterator` over sibling node's value."""

    def __bool__(self) -> bool: ...
