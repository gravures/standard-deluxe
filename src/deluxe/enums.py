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
# ruff: noqa: B009, ARG002
from __future__ import annotations

import ast
import inspect
from enum import Enum as _Enum
from enum import EnumMeta, FlagBoundary, _EnumDict  # pyright: ignore[reportPrivateUsage]
from functools import partial
from operator import is_
from typing import TYPE_CHECKING, ClassVar, Generic, Self, TypeVar, cast


# from deluxe.types import Monad


__all__ = ("Enum", "EnumType", "MaybeCallable")


_E = TypeVar("_E", bound="EnumType")


if TYPE_CHECKING:
    from collections.abc import Callable

    # NOTE: At least pyright do not correctly see a valid EnumType,
    #       here hidding our metaclass to typecheker has no downside.
    EnumType = EnumMeta

else:

    class EnumType(EnumMeta):
        """Subclass of python standard EnumType.

        Features:
            - Add support for inlined docstrings on members.
            - Make the __set_name__() method of members to be called if present.
        """

        def __new__(
            cls: type[_E],
            name: str,
            bases: tuple[type, ...],
            classdict: _EnumDict,
            *,
            boundary: FlagBoundary | None = None,
            _simple: bool = False,
            **kwds: object,
        ) -> _E:
            cls_: _E = EnumType.__new__(
                cls, name, bases, classdict, boundary=boundary, _simple=_simple, **kwds
            )
            return EnumType._docstrings(cls_)

        def _add_member_(cls, name: str, member: object) -> None:
            # this method is called by enum._proto_member descriptor class
            value = getattr(member, "_value_")

            # makes __set_name__() working for enum members
            if (set_name := getattr(value, "__set_name__", None)) and callable(set_name):
                set_name(cls, name)

            getattr(EnumType, "_add_member_")(cls, name, member)

        @staticmethod
        def _docstrings(enum: _E) -> _E:
            try:
                mod = ast.parse(inspect.getsource(enum))
            except OSError:  # no source code available
                return enum

            if mod.body and isinstance(class_def := mod.body[0], ast.ClassDef):
                # An enum member docstring is unassigned if it is the exact same object
                # as enum.__doc__.
                unassigned = partial(is_, enum.__doc__)
                names = enum.__members__.keys()
                member: _E | None = None
                for node in class_def.body:
                    match node:
                        case ast.Assign(targets=[ast.Name(id=name)]) if name in names:
                            # Enum member assignment, look for a docstring next
                            member = enum[name]
                            continue

                        case ast.Expr(value=ast.Constant(value=str(docstring))) if (
                            member and unassigned(member.__doc__)
                        ):  # docstring immediately following a member assignment
                            member.__doc__ = docstring
                        case _:
                            pass
                    member = None
            return enum


class Enum(_Enum, metaclass=EnumType):
    """Standard python Enum class with `deluxe.EnumType`."""


_T = TypeVar("_T", covariant=False)


class MaybeCallable(Generic[_T]):
    """Generic Monad wrapping up a type or a callable returning this same type."""

    __slots__: ClassVar[tuple[str, ...]] = ("_callable_", "_value_")

    def __new__(cls, value: _T | Callable[[_T], _T]) -> Self:  # noqa: D102
        self = object.__new__(cls)
        self._value_ = value
        if callable(value):
            self._callable_ = cast("Callable[[_T], _T]", value)
        else:

            def _u(*_: _T) -> _T:
                msg = f"'{type(value).__name__}' object is not callable"
                raise TypeError(msg)

            self._callable_ = _u
        return self

    def __init__(self, value: _T | Callable[[_T], _T]) -> None:
        self._callable_: Callable[[_T], _T]
        self._value_: _T | Callable[[_T], _T]

    @classmethod
    def pure(cls, value: _T | Callable[[_T], _T]) -> Self:
        """Returns a plain value wrapped into the monadic context."""
        return cls(value)

    def map(self, func: Callable[[_T | Callable[[_T], _T]], _T]) -> Self:
        """Returns the result of a functorial map."""
        return self.pure(func(self._value_))

    def bind(self, func: Callable[[_T | Callable[[_T], _T]], Self]) -> Self:
        """Returns the result of a monadic bind."""
        return func(self._value_)

    def unwrap(self) -> _T:
        """Returns the plain wrapped value.

        Raises:
            TypeError: if value is a callable.
        """
        if callable(self._value_):
            msg = "could only unwrap plain value"
            raise TypeError(msg)
        return self._value_

    def __call__(self, *args: _T) -> _T:
        """Returns a call on the wrapped value."""
        return self._callable_(*args)

    def __repr__(self) -> str:
        if not isinstance(self, MaybeCallable) and callable(self):  # pyright: ignore[reportUnnecessaryIsInstance]
            return f"{self.__class__.__name__}"  # Enum's member case
        return f"{self.__class__.__name__}({self})"

    def __str__(self) -> str:
        return str(self._value_) if hasattr(self, "_value_") else self.__repr__()
