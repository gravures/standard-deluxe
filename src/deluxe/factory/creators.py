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
"""Creators module.

Collections of basse classes implementing some creational design patterns.
"""

from __future__ import annotations

import weakref
from abc import ABCMeta, abstractmethod
from typing import Any, ClassVar, TypeVar


TSingleton = TypeVar("TSingleton", bound="Singleton")


class _SingletonMeta(type):
    """Singleton metaclass."""

    INSTANCE_REF_NAME = "__instance__"

    def __new__(
        cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any
    ) -> _SingletonMeta:
        """Type creation."""
        namespace[_SingletonMeta.INSTANCE_REF_NAME] = None
        return type.__new__(cls, name, bases, namespace, **kwargs)

    def __call__(cls: type[TSingleton], *args: Any, **kwargs: Any) -> TSingleton:
        """Called when instancing a type."""
        if (instance := getattr(cls, _SingletonMeta.INSTANCE_REF_NAME)) is None:
            instance = super().__call__(*args, **kwargs)
            setattr(cls, _SingletonMeta.INSTANCE_REF_NAME, instance)
        return instance


class Singleton(metaclass=_SingletonMeta):
    """Singleton base class.

    This Singleton implementation holds a strong reference to its
    unique instance. That is, it's not necesseray to externally
    maintain a reference to the instance to keep it alive.

    This way this maintains a global state during the life of the
    program (which could be seen as a major drawback).

    The Singleton class ensure that the __init__ method is called only
    once on its instance (except if being explicitly called again).

    Major drawbacks:
        - The Singleton class is not thread-safe.
        - Subclassing a Singleton allows creating multiple instances of
          the same base class.
        - When creating a new instance you don't know if it's a fresh one.
        - Testing a Singleton class is not trivial because of the former.

    A simple python module could be a better candidate to manage a global state.
    """

    __slots__ = ()


class _MultitonMeta(ABCMeta):
    """Multiton metaclass."""

    ID_METH_NAME = "__id__"
    INSTANCES_MAP_NAME = "__instances__"
    WEAKREF_FLAG_NAME = "__multiton_weakref__"

    def __new__(
        cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any
    ) -> _MultitonMeta:
        """Type creation."""
        namespace[_MultitonMeta.INSTANCES_MAP_NAME] = {}
        namespace[_MultitonMeta.WEAKREF_FLAG_NAME] = bool(kwargs.pop("weakref", True))

        return type.__new__(cls, name, bases, namespace, **kwargs)

    def __call__(cls: type[TMultiton], *args: Any, **kwargs: Any) -> TMultiton:
        """Called when instancing a type."""
        _id = getattr(cls, _MultitonMeta.ID_METH_NAME)(*args, **kwargs)
        _is = getattr(cls, _MultitonMeta.INSTANCES_MAP_NAME)
        _wr = getattr(cls, _MultitonMeta.WEAKREF_FLAG_NAME)

        def finalize(ocls: type, uid: int) -> None:
            del getattr(ocls, _MultitonMeta.INSTANCES_MAP_NAME)[uid]

        if not (instance := _is.get(_id)):
            instance = super().__call__(*args, **kwargs)
            _is[_id] = weakref.ref(instance) if _wr else instance
            if _wr:
                weakref.finalize(instance, finalize, cls, _id)
            return instance
        return instance() if _wr else instance


TMultiton = TypeVar("TMultiton", bound="Multiton")


class Multiton(metaclass=_MultitonMeta):
    """Multiton abstract base class.

    The Multiton is an extension of the singleton. It ensures that
    a limited number of instances of a class can exist by associating
    a value with each instance and allowing only a single object to be
    created for each of those values.

    For the sake of avoiding memory leak, the default behavior of a Multiton
    class is to store weak references of the created instances. This way,
    as soon as the reference count of an instance falls to zero, this reference
    is discarded from the internal hash table.

    So, it's up to the user to store instance's reference to keep them alive.
    Alternatively to disable this behaviour, ones could pass the weakref=False
    parameter at class definition this way :

        class M(Multiton, weakref=False):
            ...

    Like with the Singleton of this module, the __init__ method is ensure to
    be called only once by instance (except in the case of being explicitly called).
    """

    # TODO: - Studies relationship with immutability
    #       - do values that id are built on should be immutable
    #       - does __id__ could return an hashable/immutable value intsead int?
    #       - what about copy(instance)?
    #       - what about peekable?
    #       - does multiton implementation should be final?

    # Here __slots__ avoids creating a __dict__ for subclass defining __slots__.
    # When __slots__ are defined for a given type, weak reference
    # support is disabled unless a '__weakref__' string is also
    # present in the sequence of strings in the __slots__ declaration

    __instances__: ClassVar[dict[int, Multiton]]

    __slots__ = ("__weakref__",)

    @classmethod
    @abstractmethod
    def __id__(cls, *args: Any, **kwargs: Any) -> int:
        """Returns an id for an incoming Multiton instance.

        This class method is called before actual instance creation
        (before the __new__ method was called). Arguments are the same
        as those that will be passed to the __new__ and __init__ methods.

        This method should return an integer that will uniquly identify the
        future instance. How to build this integer value, based or not on the
        passed arguments is the resposaility of the implementation.

        For example: returning id(cls) will make this class a singleton.
        """
        ...

    @classmethod
    def _get(cls: type[TMultiton], value: int, default: Any = None) -> TMultiton | None:
        """Return an instance of this class by its stored id value.

        This method is intended to be called in a Multiton implementation
        by a public get() method with a more useful signature than requiring
        the internal and usually opaque id value.
        """
        _i = getattr(cls, _MultitonMeta.INSTANCES_MAP_NAME).get(value)
        return _i() or default
