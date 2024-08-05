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
from types import ModuleType
from typing import (
    IO,
    Any,
    ClassVar,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    Union,
    cast,
)

from test.support.import_helper import (
    import_fresh_module,  # pyright:ignore[reportUnknownVariableType]
)


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
    _unique: list[object] = []
    _lst = list(iterable)[::-1] if lifo else list(iterable)
    for v in _lst:
        if v not in _unique:
            _unique.append(v)
    return _unique[::-1] if lifo else _unique


EnvValue = Union[None, str, bool, int, list[Union[str, Path]]]
Separator = Literal[";", ":", ",", " "]


class Environment(MutableMapping[str, EnvValue]):  # noqa: PLR0904
    """Class representing an environment mapping.

    This class provides a way to manage and manipulate environment variables.
    """

    __slots__ = ("__dict__", "_kwargs", "_lock", "_protected")
    __list_separator: ClassVar[dict[str, Separator]] = {}

    def __init__(self, **kwargs: Any) -> None:
        self._kwargs = kwargs
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

    def get(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, name: str, default: EnvValue = ""
    ) -> EnvValue:
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

    def pop(self, name: str, default: Any | None = None) -> Any:
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

    def popitem(self) -> tuple[str, Any]:
        """Removes and returns a name-value pair from the mapping.

        Returns:
            tuple[str, Any]: A name-value pair from the mapping.

        Raises:
            KeyError: If the mapping is empty.
        """  # noqa: DOC502
        return self.__dict__.popitem()

    def setdefault(self, name: str, default: Any = None) -> Any:
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

    def __setattr__(self, name: str, value: Any) -> None:
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
            value = cast(list[Any], value)
            self._append_list(name, value)
        else:
            self.__dict__[name] = value

    def _append_list(self, key: str, values_list: list[Any]) -> None:
        if key in self.__dict__:
            self.__dict__[key] = ulist(self.__dict__[key] + values_list)
        else:
            self.__dict__[key] = ulist(values_list)

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
        _env: dict[str, str] = {}
        for k, v in self.env_hook(dict(self.__dict__)).items():
            if isinstance(v, list):
                separator = Environment.__list_separator.get(k, ":")
                _env[k] = separator.join([str(p) for p in v])
            elif isinstance(v, bool):
                _env[k] = str(int(v))
            elif not str(v) or v is None:
                continue
            else:
                _env[k] = str(v)
        return _env

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

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.__setattr__(key, value)

    def __delitem__(self, key: str) -> None:
        if key not in self._protected:
            del self.__dict__[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def __contains__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, key: str
    ) -> bool:
        return key in self.__dict__

    def __bool__(self) -> bool:
        return any(self.__dict__.values())

    def __str__(self) -> str:
        return str(self.__dict__)

    def __or__(self, other: Environment | dict[str, Any]) -> Environment:
        res = self.copy()
        res.update(other)
        return res

    def __ior__(self, other: Environment | dict[str, Any]) -> None:  # noqa: PYI034
        self.update(other)

    def __eq__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ == other

    def __ne__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ != other

    def __hash__(self) -> int:
        # HACK:
        return id(self)


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


class OrderableDict(_OrderedDict, MutableMapping[_KT, _VT]):
    """OrderableDict is a more capable OrderedDict."""

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

    def after(
        self, key: _KT, other: _KT | None = None, value: _VT | None = None
    ) -> None | tuple[_KT, _VT]:
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
            _next: _KT = self.__map[key].next.key
            return (_next, self[_next])

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
    ) -> None | tuple[_KT, _VT]:
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
            _prev: _KT = self.__map[key].prev.key
            return (_prev, self[_prev])
        if value is None:
            if key not in self or other not in self:
                msg = f"{key} or {other} not in OrderedDict"
                raise KeyError(msg)
            self._move_key(key=key, other=other, before=True)
        elif self._insert(key=key, value=value, _from=other):
            self._move_key(key=key, other=other, before=True)
        return None

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


class FilteredView(Mapping[_KT, _VT], Generic[_MT, _KT, _VT]):
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
