# Copyright (c) 2025 - Gilles Coissac
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
# ruff: noqa: E501
"""
Base types collections.
"""

from __future__ import annotations

# from sys import getsizeof
import sys

# import inspect
# import re
# from collections.abc import Collection, Mapping
from os import PathLike
from types import ModuleType
from typing import (
    Any,
    ClassVar,
    Protocol,
    TypeAlias,
    TypeVar,
    _ProtocolMeta,  # pyright: ignore[reportPrivateUsage]
    no_type_check,
)

from deluxe._multiton import IDError, Multiton, MultitonType
from deluxe._static import FrozenType, StaticType
from deluxe._types import Unset, UnsetType, _Frozen  # pyright: ignore[reportPrivateUsage]


__all__ = (
    "AnyFilePath",
    "AnyStr",
    "FilePath",
    "Frozen",
    "FrozenProtocol",
    "FrozenType",
    "IDError",
    "Multiton",
    "MultitonType",
    "StaticType",
    "Unset",
    "UnsetType",
    # "get_static_attributes",
    # "sizeof",
)


AnyStr = TypeVar("AnyStr", str, bytes)
"""A constrained type variable.

AnyStr is meant to be used for functions that may accept str or bytes arguments
but cannot allow the two to mix.

Note:
    despite its name, AnyStr has nothing to do with the Any type, nor does it mean
    “any string”. In particular, AnyStr and str | bytes are different from each other
    and have different use cases.
"""

FilePath: TypeAlias = AnyStr | PathLike[AnyStr]
"""Type alias for a filepath.

Represents a path that can be either a string/bytes or an :class:`os.PathLike`
object. The type is parameterized by ``AnyStr``, so a filepath can be either
a ``str`` or ``bytes`` backed path, but not a mix of the two.

Example:
    >>> def load_config(path: FilePath[str]) -> dict[str, Any]:
    ...     ...
"""

AnyFilePath: TypeAlias = FilePath[str] | FilePath[bytes]
"""Type alias for a file path of any string type.

Represents a path that can be either a ``str``-backed or ``bytes``-backed
file path. Unlike :data:`FilePath`, this type explicitly allows mixing
string and bytes paths at the cost of losing the constraint that paths
must be of a consistent type.

Example:
    >>> def find_resource(path: AnyFilePath) -> str:
    ...     ...
"""

Unset: UnsetType
"""Sentinel value indicating an attribute has not been set.

This singleton serves as a type-safe alternative to `None` for indicating
the absence of a value. It can be assigned to any type annotation without
causing static type checker warnings.
"""


class _FrozenSlotedMeta(_ProtocolMeta):
    @no_type_check
    def __new__(cls, name, bases, namespace, **kwds):
        if "__slots__" not in namespace:
            namespace["__slots__"] = ()

        if name == "FrozenProtocol":
            return _ProtocolMeta.__new__(cls, name, bases, namespace, **kwds)

        cls_ = type.__new__(cls, name, bases, namespace, **kwds)
        _Frozen.__cinit_subclass__(cls_)
        return cls_


class FrozenProtocol(Protocol, metaclass=_FrozenSlotedMeta):
    """Protocol defining the interface for frozen data objects.

    This protocol specifies the minimal interface that :class:`Frozen`
    and similar frozen data classes must implement.

    Example:
        >>> def process_frozen(obj: FrozenProtocol) -> None:
        ...    for value in obj:
        ...        print(value)
    """

    __frozen__: ClassVar[tuple[str, ...]]


class Frozen(FrozenProtocol, _Frozen, metaclass=_FrozenSlotedMeta):
    """A frozen data class with immutable attributes.

    Frozen provides a declarative way to create immutable objects with named
    attributes. Attributes are specified via the `__frozen__` class variable
    and become read-only after initial assignment.

    Performance
    -----------

    Object instantiation is moderately slower than Nameduple but significantly
    faster than `@dataclass` or hand-rolled pure python implementations.

    Benchmarks (creation time for 3-field objects):

    - mutable dict or slotted classes are almost equivalent
    - Named tuple: 1.4x slower
    - Frozen: 1.6x slower
    - dataclasses: 2.5x slower
    - Hand-rolled frozen: 2,5x slower

    Use Cases
    ---------

    - Need **Inheritance**: Supports inheritances of frozen attributes
    - Need **ABC Mixin**: Can combine with `ABC` for interface design
    - Allow **Gradual Initialization**: Frozen attributes can be set after instantiation
    - Need **Mutable Attribute**: defining __slots__ allow additional mutable attributes
      (eg., need a private attribute for internal state)

    Prefer `NamedTuple` for defining simpler immutable type:

    - faster instantiation
    - less verbose declaration
    - simpler type hinting
    - better support with static type checker


    Attributes:
        __frozen__ (ClassVar[tuple[str, ...]]): Tuple of attribute names
            that define the frozen structure. Must be set in subclasses.

    Iteration Protocol:
        The class supports iteration over its values. Unset attributes are
        yielded as `Unset` sentinel values.

        Example:
            >>> class Point(Frozen):
            ...     __frozen__ = ("x", "y")
            >>> p = Point()
            >>> p.x = 1
            >>> p.y = 2
            >>> list(p)
            [1, 2]

    Sequence Protocol:
        Implements sequence-like access via `__getitem__` using positional
        indices (0 to len-1) and supports `in`, `len()`, `count()`,
        and `index()` operations.

    Comparison Protocol:
        Implements `__eq__` for value-based equality comparison with other
        iterables. Implements `__hash__` only when all attributes are set.

    Pickling Support:
        Supports serialization via `__reduce__` and reconstruction via
        `__setstate__`. Frozen instances can be pickled and unpickled
        while preserving their attribute values.

    Raises:
        TypeError: If an attribute is set twice (immutability violation).
        TypeError: If `__hash__` is called when any attribute is still Unset.
        AttributeError: If attempting to delete an attribute.
        IndexError: If `__getitem__` receives an out-of-range index.

    Example:
        >>> class User(Frozen):
        ...     __frozen__ = ("name", "email", "age")
        >>> user = User()
        >>> user.name = "Alice"
        >>> user.email = "alice@example.com"
        >>> user.age = 30
        >>> user.name
        'Alice'
        >>> hash(user)  # doctest: +SKIP
        -1234567890
        >>> user == User(name="Alice", email="alice@example.com", age=30)
        True

    See Also:
        :class:`FrozenProtocol`: Protocol interface for frozen objects.
        :class:`Unset`: Sentinel value for unset attributes.
    """

    __frozen__: ClassVar[tuple[str, ...]]

    # def __init_subclass__(cls, **kwds: Any) -> None:
    #     _Frozen.__cinit_subclass__(cls)

    def __hash__(self) -> int:
        return _Frozen.__hash__(self)

    def __eq__(self, value: object, /) -> bool:
        return _Frozen.__eq__(self, value)


# _self_re = re.compile(r"\bself\.(?P<attr>\w*)\s?=\s?")


# def get_static_attributes(obj: object) -> set[str]:
#     """Returns static attributes of an object.

#     Differences from __static_attributes__ (python 3.12):
#         * return all __slots__ names, even if never assigned
#         * dive into class inheritance to look up attributes,
#           so get_static_attributes(A) >= A.__static_attributes__
#         * get_static_attributes(A()) and get_static_attributes(A)
#           could be different
#     """
#     attrs = set[str]()
#     type_ = obj if isinstance(obj, type) else type(obj)
#     for base in type_.__mro__:
#         attrs.update(getattr(base, "__slots__", ()))

#     if obj is not type_:
#         attrs.update(getattr(obj, "__dict__", {}).keys())
#     else:
#         for base in type_.__mro__:
#             for _name, func in inspect.getmembers_static(base, inspect.isfunction):
#                 attrs.update(_self_re.findall(inspect.getsource(func)))
#     return attrs


# ##
# #
# def sizeof(obj: object) -> int:
#     """Returns an approximate size in bytes of object and all of its contents."""
#     seen = set[int]()
#     default_size = getsizeof(object())

#     def attr_size() -> int:
#         return sum(
#             map(
#                 sizeof,
#                 iter(getattr(obj, key) for key in get_static_attributes(obj) if hasattr(obj, key)),
#             )
#         )

#     def sizeof(obj: object) -> int:
#         if id(obj) in seen:
#             return 0

#         seen.add(id(obj))
#         size = getsizeof(obj, default_size)

#         try:
#             mv = memoryview(obj)  # _pyright: ignore[reportArgumentType]
#         except TypeError:
#             size += attr_size()
#         else:
#             buffer_size = mv.nbytes
#             size = size if size > buffer_size else buffer_size + size
#             return size + attr_size()

#         if isinstance(obj, Collection) and not isinstance(obj, (str,)):
#             if isinstance(obj, Mapping):
#                 size += sum(map(sizeof, iter(obj.values())))  # _pyright: ignore[reportUnknownArgumentType]
#             else:
#                 size += sum(map(sizeof, iter(obj)))
#         return size

#     return sizeof(obj)


##
#
class _FrozenModule(ModuleType):  # pragma: no cover
    def __delattr__(self, name: str, /) -> None:
        msg = f"cannot delete '{name}'"
        raise SyntaxError(msg)

    def __setattr__(self, name: str, value: Any, /) -> None:
        msg = f"cannot assign to '{name}'"
        raise SyntaxError(msg)


sys.modules[__name__].__class__ = _FrozenModule
