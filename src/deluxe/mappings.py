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

import copy
import sys
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
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    cast,
    final,
    overload,
)


if TYPE_CHECKING:
    from types import ModuleType


EnvValue = str | bool | int | list[str | Path] | None
Separator = Literal[";", ":", ",", " "]


class Environment(MutableMapping[str, EnvValue]):  # noqa: PLR0904
    """Class representing an environment mapping.

    This class provides a way to manage and manipulate environment variables.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("__dict__", "_kwargs", "_lock", "_protected")
    __list_separator: ClassVar[dict[str, Separator]] = {}
    __hash__: ClassVar[None]

    def __init__(self, **kwargs: EnvValue) -> None:
        self._kwargs: Mapping[str, EnvValue] = kwargs
        self._protected: set[str] = set()
        self._lock: bool = True

    @staticmethod
    def add_list_separator(attribute: str, separator: Separator) -> None:
        """Adds a list separator for a specific attribute.

        Args:
            attribute (str): The attribute to add the separator for.
            separator (str): The separator character.
        """
        Environment.__list_separator[attribute] = separator

    def get(self, name: str, default: EnvValue = "") -> EnvValue:
        """Retrieve the value associated with a name.

        Retrieve the value associated with the given name.

        Args:
            name (str): The name to retrieve the value for.
            default (Any, optional): The default value to return
            if name is not found. Defaults to an empty string.

        Returns:
            Any: The value associated with name if found,
            otherwise the default value.
        """
        return self.__dict__.get(name, default)

    def items(self) -> ItemsView[str, EnvValue]:
        """Returns a view of the name-value pairs of this Mapping.

        Returns:
            An ItemsView that provides a dynamic view on this Mapping.
        """
        return self.__dict__.items()

    def keys(self) -> KeysView[str]:
        """Returns a view of the keys this Mapping.

        Returns:
            A KeysView that provides a dynamic view on this Mapping's keys.
        """
        return self.__dict__.keys()

    def values(self) -> ValuesView[EnvValue]:
        """Returns a view of the values in this Mapping.

        Returns:
            A ValuesView that provides a dynamic view on
            this Mapping's values.
        """
        return self.__dict__.values()

    def copy(self) -> Environment:
        """Creates a deep copy of this mapping.

        Returns:
            EnvMapping: A new EnvMapping object that is a deep
            copy of the original.
        """
        duply = self.__class__(**self._kwargs)
        for k, v in self.items():
            duply.__dict__[k] = copy.copy(v)
        return duply

    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, other: Environment | Mapping[str, EnvValue], clear: list[str] | None = None
    ) -> None:
        """Update this Mapping.

        Update this Mapping with the values from another Mapping.

        Parameters:
            other (EnvMapping | dict[str, Any]): The object or mapping
            containing the values to update the EnvMapping with.
            clear (list[str], optional): A list of names to set as empty lists
            in the EnvMapping. Defaults to an empty list.
        """
        clear = clear or []

        if isinstance(other, Environment):
            other = other.__dict__
        for key, value in other.items():
            if key not in self._protected:
                if (key in clear) and (isinstance(self.__dict__[key], list)):
                    self.__dict__[key] = []
                setattr(self, key, value)

    def clear(self) -> None:
        """Clears all attributes."""
        self.__dict__.clear()

    def pop(self, name: str, default: object | None = None) -> EnvValue:
        """Removes and returns the value associated with a name.

        If name is in the mapping, remove it and return its value,
        else return default. If default is not given and name is not
        in the mapping, a KeyError is raised..

        Args:
            name (str): The name of the attribute to remove.
            default (str): A default value to return.

        Returns:
            Any: The value associated with the name.

        Raises:
            KeyError: If the name is not found.
        """  # noqa: DOC502
        return self.__dict__.pop(name, default)

    def popitem(self) -> tuple[str, EnvValue]:
        """Removes and returns a name-value pair from the mapping.

        Returns:
            tuple[str, Any]: A name-value pair from the mapping.

        Raises:
            KeyError: If the mapping is empty.
        """  # noqa: DOC502
        return self.__dict__.popitem()

    def setdefault(self, name: str, default: EnvValue = None) -> EnvValue:
        """Sets the value associated with a name.

        If name is defined in the mapping, return its value.
        If not, defined it with a value of default and return default.
        default defaults to None.

        Args:
            name (str): The name of the attribute to set.
            default (Any, optional): The default value to set if name is not found.

        Returns:
            Any: The value associated with name.
        """
        if name in self.__dict__:
            return self.__dict__[name]
        setattr(self, name, default)
        return default

    def __setattr__(self, name: str, value: object) -> None:
        # __slots__ case
        for _cls in self.__class__.__mro__:
            if _cls is not object and name in _cls.__slots__:  # pyright: ignore[reportUnknownMemberType]
                object.__setattr__(self, name, value)
                return
        # protected attributes
        if name in self._protected and self._lock:
            msg = f"{name} is a protected attribute and can't be set by assignment."
            raise AttributeError(msg)
        # normal attributes
        if isinstance(value, list):
            value = cast("list[object]", value)
            self._append_list(name, value)
        else:
            self.__dict__[name] = value

    def _append_list(self, key: str, values_list: list[object]) -> None:
        if key in self.__dict__:
            self.__dict__[key] = self.ulist(self.__dict__[key] + values_list)
        else:
            self.__dict__[key] = self.ulist(values_list)

    @staticmethod
    def ulist(iterable: Iterable[object], lifo: bool = False) -> list[object]:
        """Returns a list of unique items from seq.

        Generate a list of unique elements from the iterable argument.
        By default first element will be kept at their index removing
        further duplicate occurrences. Setting lifo to True will inverse
        this behavior.

        Args:
            iterable (Iterable[object]): The input Sequence.
            lifo (bool, optional): If True, return the unique elements
            in Last-In-First-Out order. Defaults to False.

        Returns:
            list: A new list containing only unique elements.
        """
        unique_: list[object] = []
        lst_ = list(iterable)[::-1] if lifo else list(iterable)
        for v in lst_:
            if v not in unique_:
                unique_.append(v)
        return unique_[::-1] if lifo else unique_

    @staticmethod
    def env_hook(env: dict[str, EnvValue]) -> dict[str, EnvValue]:
        """Called by the env property getter function.

        Does nothing by default. Subclasses can override this method.
        This method is called by the env property getter function,
        just before beginning to return the environment variables.
        A working dictionary is passed to this method, so subclass
        can manipulate it before returning it.

        Returns:
            dict[str, EnvValue]: the altered mapping.
        """
        return env

    @property
    def env(self) -> dict[str, str]:
        """Returns this EnvMapping as environment variables.

        Returns:
            dict[str, str]: A dictionary containing the environment
            variables.
        """
        env_: dict[str, str] = {}
        for k, v in self.env_hook(dict(self.__dict__)).items():
            if isinstance(v, list):
                separator = Environment.__list_separator.get(k, ":")
                env_[k] = separator.join([str(p) for p in v])
            elif isinstance(v, bool):
                env_[k] = str(int(v))
            elif not str(v) or v is None:
                continue
            else:
                env_[k] = str(v)
        return env_

    def dump(self, file: IO[str] = sys.stdout) -> None:
        """Dump the environment variables to a file.

        Args:
            file (IO[str], optional): The file to write the environment
            variables to. Defaults to sys.stdout.
        """
        dump = "".join(f"{k} = {v}\n" for k, v in self.env.items())
        file.write(dump)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __getitem__(self, key: str) -> EnvValue:
        return self.__dict__[key]

    def __setitem__(self, key: str, value: EnvValue) -> None:
        self.__setattr__(key, value)

    def __delitem__(self, key: str) -> None:
        if key not in self._protected:
            del self.__dict__[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def __contains__(self, key: object) -> bool:
        return key in self.__dict__

    def __bool__(self) -> bool:
        return any(self.__dict__.values())

    def __str__(self) -> str:
        return str(self.__dict__)

    def __or__(self, other: Environment | dict[str, EnvValue]) -> Environment:
        res = self.copy()
        res.update(other)
        return res

    def __ior__(self, other: Environment | dict[str, EnvValue]) -> None:  # noqa: PYI034
        self.update(other)

    def __eq__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ == other

    def __ne__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ != other


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
