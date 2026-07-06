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
from __future__ import annotations

import os
from abc import ABCMeta
from enum import Enum, EnumMeta, StrEnum
from typing import TYPE_CHECKING, ClassVar, Self


if TYPE_CHECKING:
    from collections.abc import Callable


class _Meta(ABCMeta, EnumMeta): ...


class BaseEnum(os.PathLike[str], StrEnum, metaclass=_Meta):
    def __fspath__(self) -> str:
        return self.value


class ProjectPath(os.PathLike[str]):
    __slots__: ClassVar[tuple[str, ...]] = ("_name_", "_project_name", "_value_")  # pyright: ignore[reportIncompatibleUnannotatedOverride]

    def __init__(self, _func: Callable[[str], Self]) -> None:
        self._project_name: str = ""
        self._name_: str
        self._value_: Callable[[str], Self] = _func

    def __call__(self, name: str) -> Self:
        variant = ProjectPath(self._value_)
        variant._project_name = name
        variant._name_ = self._name_
        return variant  # pyright: ignore[reportReturnType]

    def __fspath__(self) -> str:
        return getattr(self, "_value_")(self, self._project_name)  # noqa: B009

    def __str__(self) -> str:
        return self.__fspath__()

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}.{self._name_}: ProjectPath('{self!s}')>"
            if isinstance(self, Enum)
            else f"{self.__class__.__name__}[{self._name_}]('{self!s}')"
        )

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, value: object, /) -> bool:
        return str(self) == str(value)


class ProjectEnum(ProjectPath, Enum, metaclass=_Meta): ...
