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
# ruff: noqa: PYI025, PYI019, PLW1641, ARG002
"""Sequences module."""

from __future__ import annotations

from abc import ABC
from collections.abc import Hashable, Iterator, MutableSet, Sequence, Set
from copy import copy
from functools import reduce
from operator import and_, or_, sub, xor
from typing import TYPE_CHECKING, ClassVar, Generic, Literal, TypeVar, cast


if TYPE_CHECKING:
    from collections.abc import Iterable


_V = TypeVar("_V")
_OST = TypeVar("_OST")


class _AbstractOrderedSet(ABC, Set[_V], Generic[_V]):
    __slots__: ClassVar[tuple[str, ...]] = ("_map",)

    def __new__(cls: type[_OST], iterable: Iterable[_V] | None = None) -> _OST:
        instance = super().__new__(cls)  # pyright: ignore[reportArgumentType]
        instance._map = {k: i for i, k in enumerate(iterable)} if iterable else {}
        return instance

    def __init__(self, iterable: Iterable[_V] | None = None) -> None:
        self._map: dict[_V, int]

    def __len__(self) -> int:
        return len(self._map)

    def __contains__(self, value: object) -> bool:
        return value in self._map

    def __iter__(self) -> Iterator[_V]:
        yield from self._map

    # XXX: result of operators are typed AbstractSet[_V]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _AbstractOrderedSet):
            other = cast("_AbstractOrderedSet[_V]", other)
            return len(self) == len(other) and tuple(self._map.keys()) == tuple(other._map.keys())
        if isinstance(other, Set):
            other = cast("Set[_V]", other)
            return super().__eq__(set[_V](other))
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({'{'}{', '.join(repr(e) for e in self._map)}{'}'})"

    def copy(self: _OST) -> _OST:
        return copy(self)

    def issubset(self, other: Iterable[_V]) -> bool:
        """Returns whether every element in the set is in other."""
        return self <= OrderedSet(other)

    def issuperset(self, other: Iterable[_V]) -> bool:
        """Returns whether every element in other is in the set."""
        return self >= OrderedSet(other)

    def union(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements from the set and all others."""
        return reduce(or_, (self, *others)) if others else copy(self)

    def intersection(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements common to the set and all others."""
        return reduce(and_, (self, *others)) if others else copy(self)

    def difference(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements in the set that are not in the others."""
        return reduce(sub, (self, *others)) if others else copy(self)

    def symmetric_difference(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements in either the set or other but not both."""
        return reduce(xor, (self, *others)) if others else copy(self)

    # Sequence protocol:
    # NOTE: uses a linear search through the keys,
    #       which is inefficient (O(n) complexity).
    def __getitem__(self, index: int) -> _V:
        index = index if index >= 0 else index + len(self)
        if index > 0:
            for i, elmnt in enumerate(self._map):
                if i == index:
                    return elmnt
        msg = "index out of range"
        raise IndexError(msg)

    def __reversed__(self) -> Iterator[_V]:
        # XXX: reversed(ordered_set) is typed reversed[Any]
        yield from self._map.__reversed__()

    def index(self, item: _V) -> int:
        if item not in self._map:
            raise ValueError
        for i, elmnt in enumerate(self._map.keys()):
            if elmnt == item:
                return i
        raise ValueError

    def count(self, item: _V) -> Literal[0, 1]:
        return 1 if item in self._map else 0


class OrderedFrozenSet(_AbstractOrderedSet[_V], Hashable):
    """A FrozenSet implementation retaining addition order."""

    __slots__: ClassVar[tuple[str, ...]] = ()

    def __hash__(self) -> int:
        return hash(tuple(self._map.keys()))


class OrderedSet(_AbstractOrderedSet[_V], MutableSet[_V]):
    """A mutable set implementation retaining addition order."""

    __slots__: ClassVar[tuple[str, ...]] = ()

    def add(self, value: _V) -> None:
        """Add element elem to the set."""
        # XXX: maybe this should be different, if val already in set just return
        #      this would be more consistent until a implementing MutableSequence
        self._map.pop(value, None)
        self._map[value] = len(self)

    def discard(self, value: _V) -> None:
        """Remove element elem from the set if it is present."""
        # XXX: default pop the first item, seems more natural to pop out the last
        if value in self._map:
            self._map.pop(value)

    def pop(self) -> _V:
        """Returns and removes the first element from the set.

        Raises:
            KeyError: if the set is empty.
        """  # noqa: DOC502
        return super().pop()

    def clear(self) -> None:
        """Remove all elements from the set."""
        self._map.clear()

    def update(self, *others: Iterable[_V]) -> None:
        """Update the set, adding elements from all others."""
        if others:
            reduce(or_, (self, *others))

    def intersection_update(self, *others: Iterable[_V]) -> None:
        """Update the set, keeping only elements found in it and all others."""
        if others:
            reduce(and_, (self, *others))

    def difference_update(self, *others: Iterable[_V]) -> None:
        """Update the set, removing elements found in others."""
        if others:
            reduce(sub, (self, *others))

    def symmetric_difference_update(self, *others: Iterable[_V]) -> None:
        """Update the set, keeping only elements found in either set, but not in both."""
        if others:
            reduce(xor, (self, *others))


Set.register(OrderedFrozenSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
Set.register(OrderedSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
Sequence.register(OrderedFrozenSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
Sequence.register(OrderedSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
