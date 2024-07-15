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
"""Mappings module."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator, Mapping, MutableMapping
from copy import deepcopy
from test.support.import_helper import (
    import_fresh_module,  # pyright:ignore[reportUnknownVariableType]
)
from types import ModuleType
from typing import Any, Generic, Protocol, TypeVar, cast


# TODO: make a c implementation of OrderableDict
# TODO: expands docs of after and before method
# TODO: make a generic function for loading a python module instead of its c version

_VT = TypeVar("_VT")
_KT = TypeVar("_KT")
_collections = cast(ModuleType, import_fresh_module("collections", blocked=["_collections"]))
_OrderedDict = cast(type[OrderedDict[Any, Any]], _collections.OrderedDict)


class _Link(Protocol[_KT]):
    __slots__ = "__weakref__", "key", "next", "prev"

    def __init__(self) -> None:
        self.key: _KT
        self.next: _Link[_KT]
        self.prev: _Link[_KT]


# FIXME: OrderableDict.values() iters on undefined type (Any)


class OrderableDict(_OrderedDict, dict[_KT, _VT]):
    """RordeableDict is a more capable OrderedDict."""

    def __init__(self, other: Any = (), /, **kwargs: _VT) -> None:
        super().__init__(other, **kwargs)
        self.__map: dict[_KT, _Link[_KT]] = getattr(self, "_OrderedDict__map")  # noqa: B009
        self.__root: _Link[_KT] = getattr(self, "_OrderedDict__root")  # noqa: B009

    @property
    def first(self) -> _KT:
        """Return the first key."""
        return self.__root.next.key

    @property
    def last(self) -> _KT:
        """Return the first key."""
        return self.__root.prev.key

    def _insert(self, *, key: _KT, value: _VT, _from: _KT) -> bool:
        if _from not in self:
            msg = f"{_from} not in OrderedDict"
            raise KeyError(msg)
        exist: bool = key in self
        super().__setitem__(key, value)
        return not exist

    def _move_key(self, key: _KT, other: _KT, before: bool = False) -> None:
        ref = self.__map[other]
        link = self.__map[key]
        link_prev = link.prev
        link_next = link.next
        soft_link = link_next.prev

        # remove ref
        link_prev.next = link_next
        link_next.prev = link_prev

        # insert ref
        if before:
            ref_prev = ref.prev
            link.prev = ref_prev
            link.next = ref_prev.next
            ref.prev = soft_link
            ref_prev.next = link
        else:
            ref_next = ref.next
            link.prev = ref_next.prev
            link.next = ref_next
            ref.next = link
            ref_next.prev = soft_link

    def _insert_after(self, key: _KT, value: _VT, other: _KT) -> None:
        """Insert a (key, value) after <after>."""
        if self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other)

    def after(self, key: _KT, other: _KT | None = None, value: _VT | None = None) -> None:
        """Inserts, moves or returns value after other key."""
        if other is None:
            raise NotImplementedError
        if value is None:
            if key not in self or other not in self:
                msg = f"{key} or {other} not in OrderedDict"
                raise KeyError(msg)
            self._move_key(key=key, other=other)
        elif self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other)

    def _insert_before(self, key: _KT, value: _VT, other: _KT) -> None:
        """Insert a (key, value) after <after>."""
        if self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other, before=True)

    def before(self, key: _KT, other: _KT | None = None, value: _VT | None = None) -> None:
        """Inserts, moves or returns value before other key."""
        if other is None:
            raise NotImplementedError
        if value is None:
            if key not in self or other not in self:
                msg = f"{key} or {other} not in OrderedDict"
                raise KeyError(msg)
            self._move_key(key=key, other=other, before=True)
        elif self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other, before=True)

    def _debug(self) -> str:
        return "\n".join([
            (
                f"key:{v.key}, prev:{getattr(v.prev, 'key', 'root')}"
                f", next:{getattr(v.next, 'key', 'root')}"
            )
            for v in self.__map.values()
        ])


_MT = TypeVar("_MT", bound=MutableMapping[Any, Any])


class Filter(Generic[_KT, _VT]):
    """Base class for filtering mapping views.

    The filter is a callable that takes a key and a value
    and returns a boolean. The filter is applied to a mapping,
    and the entries that return True are included in the view.

    This default implementation filter out all the mapping's items.
    """

    def __init__(self, mapping: MutableMapping[_KT, _VT]) -> None:
        pass

    def __call__(self, key: _KT, value: _VT) -> bool:  # noqa: D102, ARG002
        return True


class FilteredView(Generic[_MT, _KT, _VT], Mapping[_KT, _VT]):
    """Filtered Mapping View.

    Read-only proxy of a mapping. It provides a dynamically filtered view
    on the mapping's entries, which means that when the mapping changes,
    this view reflects those changes. Implements the collections.abc.Mapping
    protocol.
    """

    __slots__ = ("__source__", "_filter")

    def __init__(self, source: _MT, _filter: Filter[_KT, _VT]) -> None:
        self.__source__: _MT = source
        self._filter: Filter[_KT, _VT] = _filter

    def copy(self) -> _MT:
        """Returns this view as an instance of its source's type.

        The resulting mapping should be seen as a filtered deep copy
        of the FilteredView's source.
        """
        _t = type(self.__source__)()
        for k, v in self.items():
            _t[k] = deepcopy(v)
        return _t

    def __getitem__(self, key: _KT) -> _VT:
        val: _VT = self.__source__[key]
        if self._filter(key, val):
            return val
        raise KeyError(key)

    def __len__(self) -> int:
        return len(list(self.keys()))

    def __iter__(self) -> Iterator[_KT]:
        for key, val in self.__source__.items():
            if self._filter(key, val):
                yield key

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({list(self.items())})"


# d = OrderedDict({"a": 1, "b": 2, "c": 9})
# f = FilteredView(d, _filter=Filter(d))
# t = f["a"]
# s = f.__source__
# m = f.copy()
# _f = f._filter
