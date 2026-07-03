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
# ruff: noqa: PYI025, PYI019, PLW1641, ARG002, PLR1711, FURB180
"""Ordered set data structures and sequence utilities.

This module provides ordered set implementations that preserve insertion
order while supporting the full :class:`~collections.abc.Set` protocol.
Two variants are provided:

* :class:`OrderedFrozenSet` — an immutable, hashable ordered set.
* :class:`OrderedSet` — a mutable ordered set supporting in-place updates.

The :func:`dedup_list` helper deduplicates a sequence while preserving
element order.
"""

from __future__ import annotations

from abc import ABCMeta
from collections.abc import Hashable, Iterator, MutableSet, Sequence, Set
from copy import copy
from functools import reduce
from operator import (
    and_,  # pyright: ignore[reportUnknownVariableType]
    ior,  # pyright: ignore[reportUnknownVariableType]
    isub,  # pyright: ignore[reportUnknownVariableType]
    ixor,  # pyright: ignore[reportUnknownVariableType]
    or_,  # pyright: ignore[reportUnknownVariableType]
    sub,
    xor,  # pyright: ignore[reportUnknownVariableType]
)
from typing import TYPE_CHECKING, ClassVar, Generic, Literal, TypeVar, cast


if TYPE_CHECKING:
    from collections.abc import Iterable

# NOTE: python operator module is poorly typed, this will cause
#       a lot of type casting and type ignore comment.
#       See: https://github.com/python/typeshed/issues/15611
#
# TODO: Implements sequence module in C

__ALL__ = ("OrderedFrozenSet", "OrderedSet", "dedup_list")  # pragma: no cover


_V = TypeVar("_V")
_OST = TypeVar("_OST")


def dedup_list(iterable: Iterable[object], lifo: bool = False) -> list[object]:
    """Return a list of distinct items from iterable.

    By default first element will be kept at their index removing
    further duplicate occurrences. Setting lifo to True will inverse
    this behavior.

    Args:
        iterable (:class:`Iterable[object]`): The input Sequence.
        lifo (bool, optional): If True, return the distinct elements
            in Last-In-First-Out order. Defaults to False.

    Returns:
        list: A new list containing only distinct items.
    """
    unique_: list[object] = []
    list_ = list(iterable)[::-1] if lifo else list(iterable)
    for v in list_:
        if v not in unique_:
            unique_.append(v)
    return unique_[::-1] if lifo else unique_


class _AbstractOrderedSet(Set[_V], Generic[_V], metaclass=ABCMeta):  # pragma: no cover
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
        """Return a shallow copy of the set."""
        return copy(self)

    def issubset(self, other: Iterable[_V]) -> bool:
        """Return whether every element in the set is in other."""
        return self <= OrderedSet(other)

    def issuperset(self, other: Iterable[_V]) -> bool:
        """Return whether every element in other is in the set."""
        return self >= OrderedSet(other)

    def union(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements from the set and all others."""
        return cast("_OST", reduce(or_, (self, *others)) if others else copy(self))  # pyright: ignore[reportUnknownArgumentType]

    def intersection(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements common to the set and all others."""
        return cast("_OST", reduce(and_, (self, *others)) if others else copy(self))  # pyright: ignore[reportUnknownArgumentType]

    def difference(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements in the set that are not in the others."""
        return cast("_OST", reduce(sub, (self, *others)) if others else copy(self))  # pyright: ignore[reportArgumentType]

    def symmetric_difference(self: _OST, *others: Iterable[_V]) -> _OST:
        """Return a new set with elements in either the set or other but not both."""
        return cast("_OST", reduce(xor, (self, *others)) if others else copy(self))  # pyright: ignore[reportUnknownArgumentType]

    # Sequence protocol:
    # NOTE: uses a linear search through the keys,
    #       which is inefficient (O(n) complexity).
    def __getitem__(self, index: int) -> _V:
        index = index if index >= 0 else index + len(self)
        if index >= 0:
            for i, elmnt in enumerate(self._map):
                if i == index:
                    return elmnt
        msg = "index out of range"
        raise IndexError(msg)

    def __reversed__(self) -> Iterator[_V]:
        # XXX: reversed(ordered_set) is typed reversed[Any]
        yield from self._map.__reversed__()

    def index(self, item: _V) -> int:
        """Return the position of *item* in the set.

        Args:
            item: The element to locate.

        Returns:
            :obj:`int`: The index of *item* in insertion order.

        Raises:
            ValueError: If *item* is not in the set.
        """
        if item not in self._map:
            raise ValueError
        for i, elmnt in enumerate(self._map.keys()):
            if elmnt == item:
                return i
        raise ValueError

    def count(self, item: _V) -> Literal[0, 1]:
        """Return ``1`` if *item* is in the set, ``0`` otherwise."""
        return 1 if item in self._map else 0


class OrderedFrozenSet(_AbstractOrderedSet[_V], Hashable):
    """An immutable ordered set that preserves insertion order.

    :class:`OrderedFrozenSet` supports the full :class:`~collections.abc.Set`
    protocol plus the :class:`~collections.abc.Sequence` protocol
    (indexing, ``reversed()``, :meth:`index`, :meth:`count`).
    Because it is :class:`~collections.abc.Hashable` it can be used as a
    dictionary key or as a member of another set.

    For a mutable variant see :class:`OrderedSet`.

    .. note::
        __getitem__ method uses a linear search through the keys,
        which is inefficient (O(n) complexity) compared to a :class:`frozenset`.
    """

    __slots__: ClassVar[tuple[str, ...]] = ()

    def __hash__(self) -> int:
        return hash(tuple(self._map.keys()))


class OrderedSet(_AbstractOrderedSet[_V], MutableSet[_V]):
    """A mutable ordered set that preserves insertion order.

    :class:`OrderedSet` extends :class:`~collections.abc.MutableSet` with
    insertion-order memory and supports the :class:`~collections.abc.Sequence`
    protocol (indexing, ``reversed()``, :meth:`index`, :meth:`count`).

    .. note::
        The :meth:`pop` method removes and returns the **most recently**
        added element (LIFO order).

    .. note::
        __getitem__ method uses a linear search through the keys,
        which is inefficient (O(n) complexity) compared to a :class:`set`.
    """

    __slots__: ClassVar[tuple[str, ...]] = ()

    def add(self, value: _V) -> None:
        """Add *value* to the set if it is not already present."""
        if value not in self._map:
            self._map[value] = len(self._map) + 1

    def discard(self, value: _V) -> None:
        """Remove *value* from the set if it is present; otherwise do nothing."""
        if value in self._map:
            self._map.pop(value)

    def pop(self) -> _V:
        """Return and remove the most recently added element (LIFO order).

        Raises:
            KeyError: If the set is empty.
        """
        try:
            tmp = self[-1]
            del self._map[tmp]
        except IndexError:
            raise KeyError from None
        else:
            return tmp

    def clear(self) -> None:
        """Remove all elements from the set."""
        self._map.clear()

    def update(self, *others: Iterable[_V]) -> None:
        """Update the set, adding the union of all iterables."""
        if others:
            reduce(ior, (self, *others))  # pyright: ignore[reportUnknownArgumentType]
        return  # pragma: no cover

    def intersection_update(self, *others: Iterable[_V]) -> None:
        """Update the set, keeping only elements found in it and all others."""
        if others:
            # reduce(iand, (self, *others))
            tmp: OrderedSet[_V] = OrderedSet[_V](self)
            for o in others:
                tmp = cast("OrderedSet[_V]", and_(tmp, OrderedSet(o)))
            self._map = tmp._map  # pyright: ignore[reportUnannotatedClassAttribute]
        return  # pragma: no cover

    def difference_update(self, *others: Iterable[_V]) -> None:
        """Update the set, removing elements found in others."""
        if others:
            reduce(isub, (self, *others))  # pyright: ignore[reportUnknownArgumentType]
        return  # pragma: no cover

    def symmetric_difference_update(self, *others: Iterable[_V]) -> None:
        """Update the set, keeping only elements found in either set, but not in both."""
        if others:
            reduce(ixor, (self, *others))  # pyright: ignore[reportUnknownArgumentType]
        return  # pragma: no cover


Set.register(OrderedFrozenSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
Set.register(OrderedSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
Sequence.register(OrderedFrozenSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
Sequence.register(OrderedSet)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
