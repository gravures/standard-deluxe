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


##
# Multiton Type
_Multiton = TypeVar("_Multiton")


class IDError(TypeError): ...


@final
class MultitonType(type):
    """Multiton metaclass.

    The `Multiton` is an extension of the singleton design pattern.
    It ensures that a limited number of instances of a class can exist
    by associating a value with each instance and allowing only a single
    object to be created for each of those values.

    For the sake of avoiding memory leak, the default behavior of a `Multiton`
    class is to store weak references of the created instances. This way,
    as soon as the reference count of an instance falls to zero, this reference
    is discarded from its internal hash table.

    So, it's up to the user to store instance's reference to keep them alive.
    Alternatively to disable this behaviour, ones could pass the weakref=False
    parameter at class definition this way :

        class M(metaclass=MultitonType, weakref=False):
            ...

    The __init__ method of a `Multiton` is ensure to be called only once
    by instance (except in the case of being explicitly called).
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
            # sourcery skip: instance-method-first-arg-name
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
            del instances[uid]

        if instance := instances.get(uid):
            instance = instance() if use_weakref else cast("_Multiton", instance)

        if not instance:
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
        """Returns a tuple of values for an incoming Multiton instance.

        This class method is called before actual instance creation
        (before the __new__ method was called). Arguments are the same
        as those that will be passed to the __new__ and __init__ methods.

        This method should return a tuple of hashable value that will uniquely
        identify the future instance. How to build this tuple, based or not
        on the passed arguments is in charge of the implementation.

        For example: returning (cls,) will make this class a singleton.
        """  # noqa: DOC501
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
        """Return an instance of this class by its stored id value.

        This method is intended to be called in a Multiton implementation


        by a public get() method with a more useful signature than requiring
        the internal and usually opaque id value.
        """
        use_weakref: bool = getattr(cls, MultitonType.WEAKREF_FLAG_NAME)
        instances: dict[int, weakref.ReferenceType[_Multiton]] = getattr(
            cls, MultitonType.INSTANCES_MAP_NAME
        )
        if instance := instances.get(value):
            instance = instance() if use_weakref else cast("_Multiton", instance)
        return instance or default


class Multiton(metaclass=MultitonType): ...
