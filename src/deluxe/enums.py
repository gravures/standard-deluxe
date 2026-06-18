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
# ruff: noqa: B009
'''
Provides an extended `EnumMeta` type.

Allows usage of inlined docstrings on `Enum`'s members::

    from deluxe.enums import Enum

    class Colors(Enum):
        black = "#00000"
        """Pure black color."""

        red = "#FF000"
        """Pure red color."""


Make the __set_name__() method of members to be called if present::

    from deluxe.enums import Enum

    class Named:
        def __init__(self, value: object) -> None:
            self.my_value: object = value
            self.my_name: str
            self.__objclass__: type

        def __set_name__(self, owner: type, name: str) -> None:
            self.my_name = name
            self.__objclass__ = owner

        def __str__(self) -> str:
            return f"member {self.my_name} of {self.__objclass__} with value {self.my_value}"

    class MyEnum(Enum):
        ONE = Named(value = 1)
        TWO = Named(value = "2")

    >>> print(MyEnum.ONE.value)
    member ONE of <enum 'MyEnum'> with value 1

'''

from __future__ import annotations

import ast
import inspect
from enum import (
    Enum as _Enum,
    EnumMeta,
    FlagBoundary,
    _EnumDict,  # pyright: ignore[reportPrivateUsage]
)
from functools import partial
from operator import is_
from typing import TYPE_CHECKING, TypeVar


__all__ = ("Enum", "EnumType")


_E = TypeVar("_E", bound="EnumType")


if TYPE_CHECKING:
    # NOTE: At least pyright do not correctly see a valid EnumType,
    #       here hiding our metaclass to type checker has no downside.
    EnumType = EnumMeta
    """Subclass of python standard :class:`enum.EnumType` metaclass.

    Features:
        - Add support for inlined docstrings on members.
        - Make the __set_name__() method of members to be called if present.
    """

else:

    class EnumType(EnumMeta):
        """Subclass of python standard :class:`enum.EnumType` metaclass.

        Features:
            - Add support for inlined docstrings on members.
            - Make the __set_name__() method of members to be called if present.
        """

        def __new__(  # noqa: D102
            cls: type[_E],
            name: str,
            bases: tuple[type, ...],
            classdict: _EnumDict,
            *,
            boundary: FlagBoundary | None = None,
            _simple: bool = False,
            **kwds: object,
        ) -> _E:
            cls_: _E = EnumMeta.__new__(
                cls, name, bases, classdict, boundary=boundary, _simple=_simple, **kwds
            )
            return EnumType._docstrings(cls_)

        def _add_member_(cls, name: str, member: object) -> None:
            # this method is called by enum._proto_member descriptor class
            value = getattr(member, "_value_")

            # makes __set_name__() working for enum members
            if (set_name := getattr(value, "__set_name__", None)) and callable(set_name):
                set_name(cls, name)

            getattr(EnumMeta, "_add_member_")(cls, name, member)

        @staticmethod
        def _docstrings(enum: _E) -> _E:
            try:
                mod = ast.parse(inspect.getsource(enum))
            except OSError:  # pragma: no cover
                # no source code available
                return enum

            if mod.body and isinstance(class_def := mod.body[0], ast.ClassDef):  # pragma: no cover
                # NOTE: coverage say this scope is untested but obviously it is!
                #       so mark it `pragma: no cover`

                # An enum member docstring is unassigned if it is the exact
                # same object as enum.__doc__.
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
    """Standard python :class:`enum.Enum` class with `deluxe` :class:`EnumType` as metaclass."""
