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
# ruff: noqa: B032, B009, B010, N807, C901, PYI024
from __future__ import annotations

import weakref
from collections import namedtuple
from typing import TYPE_CHECKING, Any, TypeVar, cast, final


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


_Multiton = TypeVar("_Multiton")


class IDError(TypeError):
    """Exception for Multiton identity errors.

    Raised during Multiton instance creation when ``__id__`` arguments
    do not match ``__match_args__``.

    See :class:`Multiton` for details.
    """


@final
class MultitonType(type):
    """Metaclass for the Multiton pattern.

    Implements the Multiton pattern where each unique combination of constructor
    arguments maps to a single instance. Full documentation and usage details
    are provided in the :class:`Multiton` base class.

    Example::

        class Point(metaclass=MultitonType):
            __match_args__ = ('x', 'y')

            def __init__(self, x, y):
                self.x = x
                self.y = y
    """

    ID_METH_NAME = "__id__"
    INSTANCES_MAP_NAME = "__instances__"
    WEAKREF_FLAG_NAME = "__multiton_weakref__"

    # NOTE: could a Multiton be subclassed ?
    # NOTE: should we offer a __getstate__, __setstate__ implementation ?
    def __new__(
        cls: type[type[_Multiton]],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwds: Any,
    ) -> type[_Multiton]:
        """Type creation."""
        use_weakref = bool(kwds.pop("weakref", True))

        bases = tuple(
            base
            for base in bases
            if (base.__qualname__, base.__module__) != ("Multiton", __name__)
        )

        statics = cast("tuple[str, ...]", namespace.get("__static_attributes__", ()))
        namespace.setdefault("__match_args__", statics)

        namespace[MultitonType.INSTANCES_MAP_NAME] = {}
        namespace[MultitonType.WEAKREF_FLAG_NAME] = use_weakref

        # __slots__ case
        slots = namespace.get("__slots__")
        if slots is not None and use_weakref and "__weakref__" not in slots:
            namespace["__slots__"] = ("__weakref__", "_values_", *slots)

        def __setattr__(self: _Multiton, name: str, value: object, /) -> None:
            if name in {"_values_", *getattr(self, "__match_args__")} and hasattr(self, name):
                msg = f"{name} attribute is immutable"
                raise AttributeError(msg)
            object.__setattr__(self, name, value)

        def __hash__(self: _Multiton) -> int:
            return hash(getattr(self, "_values_"))

        def __eq__(self: _Multiton, value: object, /) -> bool:
            try:
                return hash(self) == hash(value)
            except TypeError:
                return False

        def __len__(self: _Multiton) -> int:
            return len(getattr(self, "_values_"))

        def __iter__(self: _Multiton) -> Iterator[object]:
            yield from getattr(self, "_values_")

        def __contains__(self: _Multiton, value: object, /) -> bool:
            return value in getattr(self, "_values_")

        def __getitem__(self: _Multiton, key: slice, /) -> object:
            return getattr(self, "_values_")[key]

        def _asdict(self: _Multiton) -> dict[str, object]:
            return cast(
                "dict[str, object]",
                cast("object", (zip(getattr(self, "__match_args__"), self, strict=False))),  # pyright: ignore[reportArgumentType]
            )

        def __copy__(self: _Multiton) -> _Multiton:
            return self

        def __deepcopy__(self: _Multiton, _memo: Any) -> _Multiton:
            return self

        # def __replace__(self: _Multiton, /, **changes: object) -> _Multiton:
        #     ic(self, changes)
        #     return self.__new__(self.__class__, **changes)

        namespace["__setattr__"] = __setattr__
        namespace["__hash__"] = __hash__
        namespace["__eq__"] = __eq__
        namespace["__len__"] = __len__
        namespace["__iter__"] = __iter__
        namespace["__contains__"] = __contains__
        namespace["__getitem__"] = __getitem__
        namespace["_asdict"] = _asdict
        namespace["__copy__"] = __copy__
        namespace["__deepcopy__"] = __deepcopy__
        # namespace["__replace__"] = __replace__

        return type.__new__(cls, name, bases, namespace, **kwds)

    if TYPE_CHECKING:

        def __init__(cls: type[_Multiton], *_args: Any, **_kwds: Any) -> None:
            # type annotations for class attributes
            # cls.__match_args__: tuple[str, ...]  # disable static hint attribute matching
            cls.__instances__: dict[int, type]
            cls.__len__: Callable[[], int]
            cls.__iter__: Callable[[], Iterator[object]]
            cls.__contains__: Callable[[object], bool]
            cls.__getitem__: Callable[[slice | int], object]
            cls._asdict: Callable[[], dict[str, object]]
            cls.__copy__: Callable[[], Multiton]
            cls.__deepcopy__: Callable[..., Multiton]
            # cls.__replace__: Callable[..., Multiton]

    def __call__(cls: type[_Multiton], *args: Any, **kwds: Any) -> _Multiton:
        # Returns a Multiton instance
        use_weakref: bool = getattr(cls, MultitonType.WEAKREF_FLAG_NAME)
        instances: dict[int, weakref.ReferenceType[_Multiton]] = getattr(
            cls, MultitonType.INSTANCES_MAP_NAME
        )

        tmp: tuple[object, ...] = getattr(cls, "__id__")(*args, **kwds)
        try:
            uid = hash((*tmp,))
        except TypeError as e:
            msg = f"{cls.__name__}.__id__ class method should return a tuple of hashables, {e}"
            raise TypeError(msg) from e

        def finalize(_cls: type[_Multiton], uid: int) -> None:
            instances.pop(uid, None)

        if instance := instances.get(uid):
            instance = instance() if use_weakref else cast("_Multiton", instance)

        if instance is None:
            instance = cast("_Multiton", type.__call__(cls, *args, **kwds))
            setattr(instance, "_values_", tuple(tmp))

            try:  # sanity check
                test = hash(instance)
            except TypeError as e:
                msg = (
                    f"{cls.__name__}.__match_args__ should refer to hashable attributes, found {e}"
                )
                raise TypeError(msg) from e
            else:
                if uid != test:
                    msg = (
                        f"{cls.__name__}.__id__ class method is incompatible"
                        " with instance __hash__ method"
                    )
                    raise TypeError(msg)

            instances[uid] = weakref.ref(instance) if use_weakref else instance  # pyright: ignore[reportArgumentType]
            if use_weakref:
                weakref.finalize(instance, finalize, cls, uid)

        return instance

    def __instancecheck__(cls, instance: object, /) -> bool:
        return (
            (cls.__qualname__, cls.__module__) == ("Multiton", __name__)
        ) or super().__instancecheck__(instance)

    def __id__(cls: type[_Multiton], *args: object, **kwds: object) -> tuple[object, ...]:
        tmp = namedtuple("tmp", getattr(cls, "__match_args__"))  # pyright: ignore[reportUntypedNamedTuple]
        try:
            return tmp(*args, **kwds)
        except TypeError as err:
            msg = (
                f"either defined {cls.__name__}.__match_args__ class attribute or override"
                f" {cls.__name__}.__id__ class method"
            )
            raise IDError(msg) from err

    def __get_instance__(
        cls: type[_Multiton], value: int, default: _Multiton | None = None
    ) -> _Multiton | None:
        use_weakref: bool = getattr(cls, MultitonType.WEAKREF_FLAG_NAME)
        instances: dict[int, weakref.ReferenceType[_Multiton]] = getattr(
            cls, MultitonType.INSTANCES_MAP_NAME
        )
        if instance := instances.get(value):
            instance = instance() if use_weakref else cast("_Multiton", instance)
        return instance or default


class Multiton(metaclass=MultitonType):
    """Multiton.

    Implements the Multiton pattern, which extends the Singleton pattern
    to allow a limited number of instances based on identifying values.

    Each unique combination of constructor arguments maps to a single instance.
    Subsequent calls with the same arguments return the same instance, while
    different argument combinations create new instances (up to the limit of
    unique argument combinations).

    By default, instances are stored using weak references to prevent memory
    leaks. When no strong references to an instance remain, it is automatically
    removed from the internal cache. To disable weak reference behavior and
    maintain strong references to all instances, set ``weakref=False`` when
    defining the class:

        class MyClass(Multiton, weakref=False):
            ...

    The `__init__` method of each instance is guaranteed to be called exactly
    once per unique instance, unless explicitly invoked by user code.

    To use this class, subclasses must either:

    1. Define a `__match_args__` class attribute listing the attribute names
       used for instance identification, or
    2. Override the `__id__` class method to return a tuple of hashable values
       that uniquely identify instances based on constructor arguments.

    .. note::
        The default weak reference behavior means instances will be garbage
        collected when no longer referenced elsewhere in the program. To keep
        instances alive, maintain a strong reference to them.

    .. warning::
        Overriding ``__id__`` or ``__match_args__`` incorrectly can lead to
        unexpected behavior where different constructor arguments might
        return the same instance or identical arguments might create
        different instances.

    Examples::

        >>> class Point(Multiton):
        ...     __match_args__ = ('x', 'y')
        ...
        ...     def __init__(self, x, y):
        ...         self.x = x
        ...         self.y = y
        ...
        >>> p1 = Point(1, 2)
        >>> p2 = Point(1, 2)
        >>> p1 is p2
        True
        >>> p3 = Point(3, 4)
        >>> p1 is p3
        False

    Subclassing Interface
    ----------------------

    Multiton provides two overridable methods to customize instance identification
    and retrieval:

    ``__id__(cls, *args, **kwds) -> tuple[object, ...]``
        Generates a unique instance identifier from constructor arguments.

        The default implementation uses :attr:`__match_args__` to construct a
        namedtuple from the constructor's positional and keyword arguments.
        Override this method to provide custom identification logic when
        :attr:`__match_args__` alone is insufficient.

        This method accepts any positional (``*args``) and keyword (``**kwds``)
        arguments passed to the class constructor and returns a tuple of
        hashable values that uniquely identify the instance. Raises
        :exc:`IDError` if the provided arguments do not match the attributes
        defined in :attr:`__match_args__` and ``__id__`` has not been overridden.

        Examples::

            >>> class Point(Multiton):
            ...     __match_args__ = ('x', 'y')
            ...     def __init__(self, x, y):
            ...         self.x = x
            ...         self.y = y
            ...
            >>> Point.__id__(1, 2)
            tmp(x=1, y=2)
            >>> Point.__id__(x=3, y=4)
            tmp(x=3, y=4)

    ``__get_instance__(cls, value: int, default: T | None = None) -> T | None``
        Retrieve an existing instance by its identifier hash.

        This method looks up a previously created Multiton instance using
        the hash value computed from the identifier tuple returned by
        ``__id__``. It is intended to be called by a public ``get()`` class
        method that provides a more user-friendly interface.

        The ``value`` parameter should be the integer hash of the instance
        identifier tuple. The ``default`` parameter specifies the value to
        return if no instance with the given identifier hash exists (defaults
        to ``None``).

        Examples::

            >>> class Point(Multiton):
            ...     __match_args__ = ('x', 'y')
            ...     def __init__(self, x, y):
            ...         self.x = x
            ...         self.y = y
            ...
            >>> p1 = Point(1, 2)
            >>> Point.__get_instance__(hash(Point.__id__(1, 2))) is p1
            True
            >>> Point.__get_instance__(9999) is None
            True
    """
