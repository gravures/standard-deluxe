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
# ruff: noqa: A002
"""A collection of Mapping types.

This module provides specialized mapping classes built on top of Python's
:class:`collections.abc.Mapping` and :class:`collections.OrderedDict`.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import (
    Callable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MutableMapping,
    ValuesView,
)
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    Protocol,
    Self,
    TypeVar,
    cast,
    final,
    overload,
)

from deluxe.importers import import_fresh_module


if TYPE_CHECKING:
    from types import ModuleType


__all__ = (
    "FilteredView",
    "FrozenMap",
    "OrderableDict",
    "view_filter",
)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_VT_co = TypeVar("_VT_co", covariant=True)


@final
class _Link(Protocol[_KT]):  # pragma: no cover
    __slots__: tuple[str, ...] = ("__weakref__", "key", "next", "prev")

    def __init__(self) -> None:
        self.key: _KT
        self.next: _Link[_KT]
        self.prev: _Link[_KT]


class _OrderableDictMeta(type):
    def __new__(
        cls: type[_OrderableDictMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwds: object,
    ) -> _OrderableDictMeta:
        collections_ = cast(
            "ModuleType",
            import_fresh_module("collections", blocked=["_collections"]),
        )
        bases = (collections_.OrderedDict,)
        return super().__new__(cls, name, bases, namespace, **kwds)


class _SupportsKeysAndGetItem(Protocol[_KT, _VT_co]):
    def keys(self) -> Iterable[_KT]: ...
    def __getitem__(self, key: _KT, /) -> _VT_co: ...


@final
class OrderableDict(OrderedDict[_KT, _VT], metaclass=_OrderableDictMeta):  # pyright: ignore[reportUninitializedInstanceVariable]
    """A :class:`~collections.OrderedDict` subclass with positional key manipulation.

    Extends :class:`~collections.OrderedDict` with :meth:`~OrderableDict.after`
    and :meth:`~OrderableDict.before` methods for inserting, moving, or
    querying entries relative to other keys and :attr:`~OrderableDict.first` /
    :attr:`~OrderableDict.last` properties for O(1) access to boundary keys.
    """

    def __init__(
        self,
        other: _SupportsKeysAndGetItem[_KT, _VT] | Iterable[tuple[_KT, _VT]] = (),
        /,
        **kwds: _VT,
    ) -> None:
        super().__init__(other, **kwds)
        self.__map: dict[_KT, _Link[_KT]] = getattr(self, "_OrderedDict__map")  # noqa: B009
        self.__root: _Link[_KT] = getattr(self, "_OrderedDict__root")  # noqa: B009

    @property
    def first(self) -> _KT:
        """Return the first key."""
        return self.__root.next.key

    @property
    def last(self) -> _KT:
        """Return the last key."""
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

    def after(
        self, key: _KT, other: _KT | None = None, value: _VT | None = None
    ) -> tuple[_KT, _VT] | None:
        """Insert, move, or return a (key, value) pair after another key.

        If ``other`` is not provided, returns the ``(key, value)`` pair found
        after ``key`` in the ordering.

        If ``value`` is ``None``, move ``key`` after ``other`` in the dict
        (the entry must already exist).

        If ``value`` is provided, insert the ``(key, value)`` pair after
        ``other``. If the key already exists in the dict, the value is updated
        but no move occurs.

        Args:
            key: The key to look up, move, or insert.
            other (``None``, optional): Reference key. If ``None``, the method
                returns the pair after ``key``. Defaults to ``None``.
            value (``None``, optional): If provided, insert this value for
                ``key``; if ``None``, move the existing entry.
                Defaults to ``None``.

        Returns:
            ``tuple`` | ``None``: A ``(key, value)`` pair if ``other`` is
            ``None``, otherwise ``None``.

        Raises:
            KeyError: If ``key`` or ``other`` does not exist in the dict.
        """
        if other is None:
            if key not in self:
                msg = f"{key} not in OrderableDict"
                raise KeyError(msg)
            next_: _KT = self.__map[key].next.key
            return (next_, self[next_])

        if value is None:
            if key not in self or other not in self:
                msg = f"{key} or {other} not in OrderableDict"
                raise KeyError(msg)
            self._move_key(key=key, other=other)
        elif self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other)
        return None

    def before(
        self, key: _KT, other: _KT | None = None, value: _VT | None = None
    ) -> tuple[_KT, _VT] | None:
        """Insert, move, or return a (key, value) pair before another key.

        If ``other`` is not provided, returns the ``(key, value)`` pair found
        before ``key`` in the ordering.

        If ``value`` is ``None``, move ``key`` before ``other`` in the dict
        (the entry must already exist).

        If ``value`` is provided, insert the ``(key, value)`` pair before
        ``other``. If the key already exists in the dict, the value is updated
        but no move occurs.

        Args:
            key: The key to look up, move, or insert.
            other (``None``, optional): Reference key. If ``None``, the method
                returns the pair before ``key``. Defaults to ``None``.
            value (``None``, optional): If provided, insert this value for
                ``key``; if ``None``, move the existing entry.
                Defaults to ``None``.

        Returns:
            ``tuple`` | ``None``: A ``(key, value)`` pair if ``other`` is
            ``None``, otherwise ``None``.

        Raises:
            KeyError: If ``key`` or ``other`` does not exist in the dict.
        """
        if other is None:
            if key not in self:
                msg = f"{key} not in OrderableDict"
                raise KeyError(msg)
            prev_: _KT = self.__map[key].prev.key
            return (prev_, self[prev_])
        if value is None:
            if key not in self or other not in self:
                msg = f"{key} or {other} not in OrderedDict"
                raise KeyError(msg)
            self._move_key(key=key, other=other, before=True)
        elif self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other, before=True)
        return None


# @final
# class _FrozenDecoratorMeta(type, Generic[_KT, _VT]):
#     __required_keys__: frozenset[str] = frozenset()
#     __optional_keys__: frozenset[str] = frozenset()
#     __total__: bool = True

#     def __new__(
#         cls: type[_FrozenDecoratorMeta[_KT, _VT]],
#         name: str,
#         bases: tuple[type, ...],
#         namespace: dict[str, object],
#         **kwds: object,
#     ) -> _FrozenDecoratorMeta[_KT, _VT]:
#         if not any(issubclass(Mapping, base) for base in bases):
#             raise TypeError
#         return super().__new__(cls, name, bases, namespace, **kwds)

#     def __call__(self, *args: object, **kwds: object) -> FrozenMap[_KT, _VT]:
#         mapping = cast(
#             "Mapping[_KT, _VT]",
#             cast("object", super().__call__(*args, **kwds)),
#         )
#         return FrozenMap(mapping)


class FrozenMap(Mapping[_KT, _VT]):  # noqa: PLW1641
    """A read-only :class:`~collections.abc.Mapping` that cannot be modified.

    Items are provided at instantiation and cannot be added, changed, or
    removed afterward. Note that :class:`FrozenMap` does **not** enforce
    the immutability of the values themselves; use immutable containers
    as values if that is required.

    .. note::

       This class exists primarily because :class:`types.MappingProxyType`,
       which offers similar behavior cannot be subclassed.

    The following dunder methods are implemented to satisfy the
    :class:`~collections.abc.Mapping` protocol:

    * :meth:`~object.__contains__`, :meth:`~object.__getitem__`,
      :meth:`~object.__len__`, :meth:`~object.__iter__`
    * :meth:`~object.__eq__` / :meth:`~object.__ne__` compare by items.
    * :meth:`~object.__repr__` produces a ``FrozenMap({...})`` string.

    Args:
        other (:obj:`~collections.abc.Mapping`, optional):
            The source mapping to freeze. If ``None``, keyword arguments
            are used instead. Defaults to ``None``.
        **kwds: Additional key-value pairs merged into the mapping.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_items", "_keys", "_source", "_values")

    @overload
    def __new__(cls, other: Literal[None] = None, /, **kwds: _VT) -> FrozenMap[str, _VT]: ...  # noqa: PYI061
    @overload
    def __new__(cls, other: Mapping[_KT, _VT], /, **kwds: _VT) -> FrozenMap[_KT, _VT]: ...
    def __new__(  # noqa: D102
        cls, other: Mapping[_KT, _VT] | None = None, /, **kwds: _VT
    ) -> FrozenMap[_KT, _VT] | FrozenMap[str, _VT]:
        if other is None:
            return cls(kwds)  # pyright: ignore[reportCallIssue, reportArgumentType]

        self = object.__new__(cls)
        self._source = other
        self_ = cast("Mapping[_KT, _VT]", cast("object", self))
        self._keys = KeysView[_KT](self_)
        self._values = ValuesView(self_)
        self._items = ItemsView(self_)
        return self

    if TYPE_CHECKING:

        def __init__(self, other: Mapping[_KT, _VT] | None = None, /, **kwds: _VT) -> None:  # noqa: ARG002
            self._source: Mapping[_KT, _VT]
            self._keys: KeysView[_KT]
            self._values: ValuesView[_VT]
            self._items: ItemsView[_KT, _VT]

    def keys(self) -> KeysView[_KT]:
        """Return a view of the keys in the mapping.

        Returns:
            :obj:`KeysView`: A view of the keys in the mapping.
        """
        return self._keys

    def values(self) -> ValuesView[_VT]:
        """Return a view of the values in the mapping.

        Returns:
            :obj:`ValuesView`: A view of the values in the mapping.
        """
        return self._values

    def items(self) -> ItemsView[_KT, _VT]:
        """Return a view of the (key, value) pairs in the mapping.

        Returns:
            :obj:`ItemsView`: A view of the (key, value) pairs in the mapping.
        """
        return self._items

    def get(self, key: _KT, default: _VT | None = None) -> _VT | None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the value associated with the specified key.

        If the key is not found in the mapping, the default value is returned.

        Args:
            key: The key to look up in the mapping.
            default (:obj:`~typing.Any` | ``None``, optional):
                The value to return if the key is not found.
                Defaults to ``None``.

        Returns:
            :obj:`~typing.Any` | ``None``: The value associated with the key
            if found, otherwise the default value.
        """
        return self._source.get(key, default)

    def __contains__(self, key: _KT) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        return key in self._source

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, Mapping):
            return self.items() == other.items()
        return NotImplemented

    def __ne__(self, other: object, /) -> bool:
        return not self.__eq__(other)

    def __getitem__(self, key: _KT) -> _VT:
        return self._source[key]

    def __len__(self) -> int:
        return len(self._source)

    def __iter__(self) -> Iterator[_KT]:
        for item in self._source.items():
            yield item[0]

    def __repr__(self) -> str:
        repr_ = ", ".join(f"{i[0]!r}: {i[1]!r}" for i in iter(self.items()))
        return f"{self.__class__.__name__}({'{'}{repr_}{'}'})"


view_filter = Callable[[Any, Any], bool]


class FilteredView(FrozenMap[_KT, _VT]):
    """Dynamically filtered read-only view on a :class:`~collections.abc.Mapping`.

    Provides a live, filtered view of a source mapping: when the source
    mapping is modified, this view reflects those changes automatically.

    Dunder methods :meth:`~object.__contains__`, :meth:`~object.__getitem__`,
    :meth:`~object.__len__`, and :meth:`~object.__iter__` all respect the
    filter predicate, only entries for which the filter returns ``True``
    are visible.

    Examples::

        >>> d = {'a': 1, 'b': 2, 'c': 3}
        >>> FilteredView(d, lambda k, v: v > 1)
        FilteredView({'b': 2, 'c': 3})

    Args:
        source (:obj:`~collections.abc.Mapping`):
            The source mapping for this view.

        filter (callable, optional):
            A callable ``(key, value) -> bool`` that determines whether an
            entry is included. If ``None``, an identity-like filter is used:
            entries whose value evaluates to ``False`` are excluded.
            Defaults to ``None``.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_filter",)

    def __new__(cls, source: Mapping[_KT, _VT], filter: view_filter | None = None) -> Self:  # noqa: D102
        self = cast("Self", super().__new__(cls, source))
        self._filter = filter or (lambda _, v: bool(v))
        return self

    if TYPE_CHECKING:

        def __init__(self, source: Mapping[_KT, _VT], filter: view_filter | None = None) -> None:  # noqa: ARG002
            self._filter: view_filter

    def get(self, key: _KT, default: _VT | None = None) -> _VT | None:
        """Return the value associated with the specified key.

        If the key is not found in the source mapping, or if it is present
        but excluded by the view's filter, the default value is returned.

        Args:
            key: The key to look up in the mapping.
            default (:obj:`~typing.Any` | ``None``, optional):
                The value to return if the key is not found or filtered out.
                Defaults to ``None``.

        Returns:
            :obj:`~typing.Any` | ``None``: The value associated with the key
            if found and not filtered, otherwise the default value.
        """
        if key in self._source and self._filter(key, val := self._source[key]):
            return val
        return default

    def __contains__(self, key: _KT) -> bool:
        return key in self._source and self._filter(key, self._source[key])

    def _copy(self, deep: bool, memo: dict[int, Any] | None):
        type_ = type(self._source)
        if issubclass(type_, MutableMapping):
            mut = type_()
            for k, v in self.items():
                mut[k] = deepcopy(v, memo) if deep else v
            return mut

        tmp: dict[_KT, _VT] = {k: deepcopy(v, memo) if deep else v for k, v in self.items()}
        try:
            frozen = type_(tmp)  # pyright: ignore[reportCallIssue]
        except Exception:  # noqa: BLE001 # pragma: no cover
            frozen = FrozenMap(tmp)
        return frozen

    def __copy__(self):
        """Return a filtered shallow copy of the source mapping.

        Returns:
            :obj:`~collections.abc.Mapping`: A filtered shallow copy of the
            same type as the source mapping.
        """
        return self._copy(deep=False, memo=None)

    def __deepcopy__(self, memo: dict[int, Any] | None = None):
        """Return a filtered deep copy of the source mapping.

        Args:
            memo (:obj:`dict` [ :obj:`int`, :obj:`~typing.Any` ], optional):
                The memoisation dictionary used by :func:`~copy.deepcopy`.
                Defaults to ``None``.

        Returns:
            :obj:`~collections.abc.Mapping`: A filtered deep copy of the
            same type as the source mapping.
        """
        return self._copy(deep=True, memo=memo)

    def __getitem__(self, key: _KT) -> _VT:
        if self._filter(key, val := self._source[key]):
            return val
        raise KeyError(key)

    def __len__(self) -> int:
        return len(self._source) - sum(not (self._filter(*i)) for i in self._source.items())

    def __iter__(self) -> Iterator[_KT]:
        for item in self._source.items():
            if self._filter(*item):
                yield item[0]


Mapping.register(FilteredView)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
