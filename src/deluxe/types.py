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
from __future__ import annotations

# import inspect
# import re
# from collections.abc import Collection, Mapping
from os import PathLike

# from sys import getsizeof
from typing import TypeAlias, TypeVar

from deluxe._cctypes import Frozen, Unset, UnsetType
from deluxe._multiton import Multiton, MultitonType
from deluxe._static import FrozenType, StaticType


__all__ = (
    "AnyFilePath",
    "FilePath",
    "Frozen",
    "FrozenType",
    "Multiton",
    "MultitonType",
    "StaticType",
    "Unset",
    "UnsetType",
    # "get_static_attributes",
    # "sizeof",
)


AnyStr = TypeVar("AnyStr", str, bytes)
FilePath: TypeAlias = AnyStr | PathLike[AnyStr]
AnyFilePath: TypeAlias = FilePath[str] | FilePath[bytes]


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
