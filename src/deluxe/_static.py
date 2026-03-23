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
# ruff: noqa: B032, B010, C901, PLR0915
from __future__ import annotations

from abc import ABC, ABCMeta, update_abstractmethods
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    _no_init_or_replace_init,  # pyright: ignore[reportUnknownVariableType, reportAttributeAccessIssue]
    _ProtocolMeta,  # pyright: ignore[reportPrivateUsage]
    cast,
    no_type_check,
)

from deluxe._cctypes import Unset


if TYPE_CHECKING:
    from collections.abc import Iterable


##
# FrozenType
class FrozenType(type):
    def __delattr__(cls, name: str, /) -> None:
        msg = f"cannot delete '{name}' attribute of immutable type '{cls.__name__}'"
        raise TypeError(msg)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in {"__abstractmethods__", "__protocol_attrs__"} or getattr(cls, name) is Unset:
            type.__setattr__(cls, name, value)
        else:
            msg = f"cannot set '{name}' attribute of immutable type '{cls.__name__}'"
            raise TypeError(msg)


##
# StaticType
class StaticType(FrozenType, _ProtocolMeta):
    if TYPE_CHECKING:

        def __init__(cls, *_args: Any, **_kwds: Any) -> None:
            # type annotations for class attributes
            cls.__orig_bases__: tuple[type, ...]

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwds: Any,
    ) -> StaticType:
        def borrow_func(func: FunctionType, cls_name: str, module: str) -> FunctionType:
            qualname = f"{cls_name}.{func.__name__}"
            is_abstract: bool = getattr(func, "__isabstractmethod__", False)
            func = FunctionType(
                code=func.__code__.replace(
                    co_qualname=qualname,
                ),
                globals=func.__globals__,
            )
            func.__module__ = module
            if is_abstract:
                setattr(func, "__isabstractmethod__", True)
            return func

        @no_type_check
        def borrow_attr(
            attr: object, cls_name: str, module: str
        ) -> classmethod | staticmethod | FunctionType:
            if isinstance(attr, (classmethod, staticmethod)):
                func = borrow_func(attr.__func__, cls_name, module)
                attr = type(attr)(func)
            elif isinstance(attr, FunctionType):
                attr = borrow_func(attr, cls_name, module)
            return attr

        def borrow_type(cls_: type, ns: dict[str, Any], cls_name: str) -> None:
            slots: Iterable[str] = getattr(cls_, "__slots__", ())
            for key, attr in cls_.__dict__.items():
                if (
                    key
                    not in {
                        "__module__",
                        "__firstlineno__",
                        "__dict__",
                        "__weakref__",
                        "__static_attributes__",
                        "__mro__",
                        *slots,  # also ignore slotted descriptors
                    }
                    and key not in ns
                ):
                    ns[key] = borrow_attr(attr, cls_name, ns["__module__"])

            if slots and (ns_slots := ns.get("__slots__")) is not None:
                ns["__slots__"] = type(ns_slots)({*slots, *ns_slots})

        abcs = {Protocol, ABC}
        abstract: type = Unset
        origin: type = bases[0] if bases else Unset
        orig_bases: tuple[type, ...] = getattr(origin, "__orig_bases__", ())
        is_protocol: bool = False

        @no_type_check
        def process_bases():
            # Allow Protocol or ABC to be in bases along a concret type
            nonlocal is_protocol, bases, orig_bases, origin, abstract

            if len(bases) != 2:
                return

            abcmeta, origin = bases if bases[0] in abcs else reversed(bases)
            if origin in abcs or abcmeta not in abcs:
                # invalid, exception will be raised later
                return

            bases = (origin,)
            orig_bases = getattr(origin, "__orig_bases__", ())

            def verify_protocol(meta: type, base: type) -> bool:
                if meta is Protocol:
                    if not getattr(base, "_is_protocol", False):
                        msg = (
                            f"Protocol class '{name}' cannot derive"
                            f" from non-Protocol BorrowType '{base.__name__}'"
                        )
                        raise TypeError(msg)
                    return True
                return False

            if not orig_bases:
                # make origin an ABC or Protocol
                is_protocol = verify_protocol(abcmeta, origin)
                # origin = type(f"{name}_tmp", (abcmeta,), dict(origin.__dict__))
                abstract = type(f"{name}_tmp", (abcmeta,), dict(origin.__dict__))
                orig_bases = (abcmeta,)
                return

            if is_protocol := verify_protocol(abcmeta, orig_bases[-1]):
                # so abcmeta and orig_bases[0] are guaranteed to be Protocol
                # if orig_bases[-1] is no more a Protocol, error was raised
                # and origin already have all Protocol attributes, just return
                return

            # Here abcmeta is ABC (otherwise we returned or raised)
            if any(map(lambda x: x in abcs, orig_bases)):  # noqa: C417
                # origin is already an ABC,
                # just return with orig_bases unchanged
                return

            # make origin an ABC
            abstract = type(f"{name}_tmp", (abcmeta,), dict(origin.__dict__))
            orig_bases = (abcmeta, *orig_bases)

        process_bases()

        # Only support a single concret base class
        if len(bases) > 1:
            msg = f"{cls.__name__} do not support multiple inheritance"
            raise TypeError(msg)

        if len(bases) == 1:
            del_init = del_protocol = False

            if origin in abcs:
                abcmeta = cast("ABCMeta | _ProtocolMeta", type(origin))
                abstract = abcmeta(f"{name}_tmp", (origin,), namespace)
            elif orig_bases and orig_bases[0] in abcs:
                abstract = abstract or origin
                namespace.setdefault("__annotations__", {})
                if hasattr(abstract, "_is_protocol"):
                    namespace["_is_protocol"] = is_protocol
                    del_protocol = True
                    if is_protocol:
                        # Set __init__ to prevent protocol instantiation
                        namespace["__init__"] = _no_init_or_replace_init  # pyright: ignore[reportUnreachable]
                del_init = "__init__" not in namespace

            borrow_type(abstract or origin, namespace, name)

            if del_protocol:
                namespace.pop("__protocol_attrs__", None)
            if del_init:
                namespace.pop("__init__", None)
            if namespace.get("__annotations__") == {}:
                del namespace["__annotations__"]

        namespace["__orig_bases__"] = (*orig_bases, origin) if origin else orig_bases

        cls_ = type.__new__(cls, name, (), namespace, **kwds)
        if abstract:
            update_abstractmethods(cls_)
        cls_.__init_subclass__(**kwds)
        return cls_
