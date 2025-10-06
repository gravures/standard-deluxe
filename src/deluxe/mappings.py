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
from collections.abc import (
    Callable,
    ItemsView,
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
    Generic,
    Protocol,
    TypeVar,
    cast,
    final,
    overload,
)

from deluxe.environ import Environment, EnvValue, Separator


if TYPE_CHECKING:
    from types import ModuleType


__all__ = (
    "EnvValue",
    "Environment",
    "FilteredView",
    "FrozenMap",
    "OrderableDict",
    "Separator",
)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


@final
class _Link(Protocol[_KT]):
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
        from test.support.import_helper import (  # noqa: PLC0415
            import_fresh_module,  # pyright:ignore[reportUnknownVariableType]
        )

        collections_ = cast(
            "ModuleType",
            import_fresh_module("collections", blocked=["_collections"]),
        )
        bases = (collections_.OrderedDict,)
        return super().__new__(cls, name, bases, namespace, **kwds)


@final
class OrderableDict(OrderedDict[_KT, _VT], metaclass=_OrderableDictMeta):
    """OrderableDict is a more capable OrderedDict."""

    def __init__(self, other: Any = (), /, **kwargs: Mapping[str, _VT]) -> None:
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

    def after(
        self, key: _KT, other: _KT | None = None, value: _VT | None = None
    ) -> tuple[_KT, _VT] | None:
        """Inserts, moves or returns (key, value) after other.

        if other is not provided, returns the (key, value) pair found after key,
        or raises a KeyError if key doesn't exist.

        If value is None, move the key after other (key) in the dict.

        If value is provided, insert the (key, value) pair after other (key)
        or if key already exists in the dict, value is updated but no move occurs.

        Returns:
            a tuple (key, value) pair if other is not provided, None otherwise.

        Raises:
            KeyError: if value is None and key or other doesn't exist.
        """
        if other is None:
            if key not in self:
                msg = f"{key} not in OrderedableDict"
                raise KeyError(msg)
            next_: _KT = self.__map[key].next.key
            return (next_, self[next_])

        if value is None:
            if key not in self or other not in self:
                msg = f"{key} or {other} not in OrderedableDict"
                raise KeyError(msg)
            self._move_key(key=key, other=other)
        elif self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other)
        return None

    def before(
        self, key: _KT, other: _KT | None = None, value: _VT | None = None
    ) -> tuple[_KT, _VT] | None:
        """Inserts, moves or returns (key, value) before other.

        if other is not provided, returns the (key, value) pair found before key,
        or raises a KeyError if key doesn't exist.

        If value is None, move the key before other (key) in the dict.

        If value is provided, insert the (key, value) pair before other (key)
        or if key already exists in the dict, value is updated but no move occurs.

        Returns:
            a tuple (key, value) pair if other is not provided, None otherwise.

        Raises:
            KeyError: if value is None and key or other doesn't exist.
        """
        if other is None:
            if key not in self:
                msg = f"{key} not in OrderedableDict"
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


@final
class _FrozenDecoratorMeta(type, Generic[_KT, _VT]):
    __required_keys__: frozenset[str] = frozenset()
    __optional_keys__: frozenset[str] = frozenset()
    __total__: bool = True

    def __new__(
        cls: type[_FrozenDecoratorMeta[_KT, _VT]],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwds: object,
    ) -> _FrozenDecoratorMeta[_KT, _VT]:
        if not any(issubclass(Mapping, base) for base in bases):
            raise TypeError
        return super().__new__(cls, name, bases, namespace, **kwds)

    def __call__(self, *args: object, **kwds: object) -> FrozenMap[_KT, _VT]:  # noqa: N804
        mapping = cast(
            "Mapping[_KT, _VT]",
            cast("object", super().__call__(*args, **kwds)),
        )
        return FrozenMap(mapping)


class FrozenMap(Generic[_KT, _VT]):  # noqa: PLW1641
    """A read-only mapping that is immutable.

    An immutable mapping that cannot be modified after its creation.
    Items should be provided at object instantiation. FrozenMap does
    not enforce immutability of values assigned to keys. For such
    a behaviour fill it with immutable container.

    Args:
        other (Mapping): The mapping to be frozen.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_items", "_keys", "_source", "_values")

    @overload
    def __init__(self, other: None = None, /, **kwds: _VT) -> None: ...

    @overload
    def __init__(self, other: Mapping[_KT, _VT], /, **kwds: _VT) -> None: ...

    def __init__(self, other: Mapping[_KT, _VT] | None = None, /, **kwds: _VT) -> None:
        self._source: Mapping[_KT, _VT] = other or kwds  # pyright: ignore[reportAttributeAccessIssue]

        self_ = cast("Mapping[_KT, _VT]", cast("object", self))
        self._keys: KeysView[_KT] = KeysView[_KT](self_)
        self._values: ValuesView[_VT] = ValuesView(self_)
        self._items: ItemsView[_KT, _VT] = ItemsView(self_)

    def keys(self) -> KeysView[_KT]:
        """Returns a view of the keys in the mapping.

        This method returns a view object that displays
        a list of all the keys in the mapping.

        Returns:
            KeysView: A view of the keys in the mapping.
        """
        return self._keys

    def values(self) -> ValuesView[_VT]:
        """Returns a view of the values in the mapping.

        This method returns a view object that displays
        a list of all the values in the mapping.

        Returns:
            ValuesView: A view of the values in the mapping.
        """
        return self._values

    def items(self) -> ItemsView[_KT, _VT]:
        """Returns a view of the (key, value) pairs in the mapping.

        This method returns a view object that displays a list
        of all the (key, value) pairs in the mapping.

        Returns:
            ItemsView: A view of the (key, value) pairs in the mapping.
        """
        return self._items

    def get(self, key: _KT, default: _VT | None = None) -> _VT | None:
        """Return the value associated with the specified key.

        If the key is not found in the mapping, the default value is returned.

        Args:
            key: The key to look up in the mapping.
            default (Any | None): The value to return if the key is not found.
            Defaults to None.

        Returns:
            Any | None: The value associated with the key if found,
            otherwise the default value.
        """
        return self._source.get(key, default)

    def __contains__(self, key: _KT) -> bool:
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


Mapping.register(FrozenMap)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

f = FrozenMap[str, int]({"a": 12, "b": 3, "c": 5})
f = FrozenMap[int, int](a=12, b=3, c=5)
f = FrozenMap[str, int](a=12, b=3, c=5)

# def frozenmap(class_: type[Mapping[_KT, _VT]]):
#     # bases = class_.__dict__.get("__orig_bases__", ())

#     def decorator(**anno: Any) -> FrozenMap[_KT, _VT]:
# # pyright: _ignore[reportUnknownParameterType]
#         print("_DEBUG:", anno)
#         if is_typeddict(class_):
#             an = class_.__dict__.get("__annotations__", {})
#             rk = class_.__dict__.get("__required_keys__", frozenset())
#             ok = class_.__dict__.get("__optional_keys__", set())
#             to = class_.__dict__.get("__total__", True)
#             ns = {
#                 "__annotations__": an,
#                 "__required_keys__": rk,
#                 "__optional_keys__": ok,
#                 "__total__": to,
#                 "__module__": class_.__dict__.get("__module__"),
#             }
#         else:
#             an = get_type_hints(class_)
#             ns = dict(class_.__dict__)
#         _@functools.wraps(class_)
#         def implemented(*args, **kwds) -> FrozenMap[_KT, _VT]:
# # _pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
#             return type.__new__(_FrozenDecoratorMeta, class_.__name__, class_.__bases__, ns)(
#                 *args, **kwds
#             )  # _pyright: ignore[reportUnknownVariableType]
#         # own_annotation: dict[str, Any] = {}
#         # own_annotation |= anno
#         # decorator.__annotations__ = anno
#         return implemented(**anno)  # _pyright: ignore[reportUnknownVariableType]
#     return decorator


# @frozenmap
# class TD(dict[str, int]): ...
# td = TD(name=2, age="18")
# td["truc"] = 19

# def test_frozen() -> None:
#     d: OrderableDict[int, str] = OrderableDict({1: "1", 2: "2"})
#     _f = FrozenMap(d)
#     _k = _f.keys()
#     _i = _f.items()


view_filter = Callable[[Any, Any], bool]


class FilteredView(FrozenMap[_KT, _VT]):
    """Filtered Mapping View.

    Read-only proxy view on a Mapping. It provides a dynamically filtered view
    on the Mapping's entries, which means that when the Mapping changes,
    this view reflects those changes.

    Implements the collections.abc.Mapping protocol.

    >>> d = {'a': 1, 'b': 2, 'c': 3}
        FilteredView(d, lambda k, v: v > 1)
        "FilteredView({'b': 2, 'c': 3})"

    Args:
        Mapping[Any, Any]: The source Mapping for this FilteredView.

        Callable[[Any, Any], bool]: The filter is a Callable taking
            a key, value pair as arguments and should returns True
            for an item to be included in this View. If set to None,
            this View will not be filtered at all.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_filter",)

    def __init__(self, source: Mapping[_KT, _VT], filter_: view_filter) -> None:
        super().__init__(source)
        self._filter: view_filter = filter_

    def get(self, key: _KT, default: _VT | None = None) -> _VT | None:  # noqa: D102
        if key in self._source and self._filter(key, val := self._source[key]):
            return val
        return default

    def __contains__(self, key: _KT) -> bool:
        return key in self._source and self._filter(key, self._source[key])

    def copy(self):  # -> Mapping[_KT, _VT] | FrozenMap[_KT, _VT]:
        """Copy this view as an instance of its source's type.

        The resulting mapping should be seen as a filtered deep copy
        of the FilteredView's source.

        Returns:
            A Mapping of the same type as the FilteredView's source.
        """
        type_ = type(self._source)
        if issubclass(MutableMapping, type_):
            mut = type_()
            for k, v in self.items():
                mut[k] = deepcopy(v)  # pyright: ignore[reportIndexIssue]
            return mut

        tmp: dict[_KT, _VT] = {k: deepcopy(v) for k, v in self.items()}
        try:
            imu = type_(tmp)  # pyright: ignore[reportCallIssue]
        except Exception:  # noqa: BLE001
            imu = FrozenMap(tmp)
        return imu

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


# def test_fv() -> None:
#     # d = {1: "1", 2: "2"}
#     d: OrderableDict[int, str] = OrderableDict({1: "1", 2: "2"})
#     v = FilteredView(d, lambda x, y: True)
#     k = v.keys()
#     s = v._source
#     c = v.copy()
