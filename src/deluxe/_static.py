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

from deluxe._types import Unset


if TYPE_CHECKING:
    from collections.abc import Iterable


##
# FrozenType
class FrozenType(type):
    """A metaclass that make class immutable.

    FrozenType creates types that cannot have their attributes modified after
    class creation. This provides compile-time safety and prevents accidental
    or intentional changes to class-level state.

    Immutability Rules:
        * **Deletion**: Attributes cannot be deleted from the class
        * **Assignment**: Most attributes cannot be modified after creation

    Exceptions:
        The following attributes are exempt from immutability and can be modified:

        * ``__abstractmethods__``: Required for ABC/Protocol functionality
        * ``__protocol_attrs__``: Required for Protocol functionality
        * Any attribute that is currently :class:`~deluxe._types.Unset`

    Use Cases:
        * Create classes that should never be modified
        * Prevent accidental class attribute changes in large codebases
        * Provide a stable class interface that cannot be altered by consumers
        * Serve as a base for other metaclasses that need immutability
          (e.g., :class:`StaticType`)

    Examples:
        Create a frozen class::

            class Constants(metaclass=FrozenType):
                VERSION = "1.0"
                MAX_SIZE = 100

            # These raise TypeError
            Constants.VERSION = "2.0"  # TypeError: cannot set 'VERSION' attribute...
            del Constants.VERSION     # TypeError: cannot delete 'VERSION' attribute...

        Check if a class is frozen::

            class Mutable:
                pass

            class Immutable(metaclass=FrozenType):
                pass

            type(Mutable)   # Returns <class 'type'>
            type(Immutable) # Returns <class 'FrozenType'>

    Note:
        FrozenType only prevents changes at the class level. Instance attributes
        (stored in ``__dict__``) are not affected — only class attributes defined
        on the type itself.
    """

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
    """A metaclass that make class derivation static.

    StaticType creates types that "borrow" their attributes (methods, classmethods,
    staticmethods, etc.) from a base class without using normal class inheritance.
    When a class inherits from a StaticType-based type, it automatically becomes
    a new StaticType and borrows all attributes from its parent.

    This approach avoids the drawbacks of inheritance (method resolution order issues,
    diamond problems, tight coupling) while allowing derived classes to use the
    borrowed behaviors as if they were their own.

    The borrowing mechanism:
        * Attributes are copied (not referenced) from the parent to the child
        * The child becomes a new StaticType, allowing further derivation
        * ``__slots__`` from parent and child are merged if both are defined

    Single Inheritance Restriction:
        Because a class can only borrow from one source, multiple concrete base
        classes are not supported. However, this metaclass supports special
        combination with :class:`typing.Protocol` or :class:`abc.ABC` to allow
        borrowing from a Protocol while remaining a Protocol.

    Immutability:
        Like :class:`FrozenType`, StaticType makes the created class immutable —
        attributes cannot be set or deleted after class creation.

    Relation to Traits:
        StaticType shares the core philosophy of the `Traits`_ design pattern:
        composing behavior without traditional inheritance. However, there are
        key differences:

        * **Implementation vs Interface**: Traits define a contract (interface)
          that must be implemented by consuming classes. StaticType copies
          behavior from an already-implemented class—the source already has full
          implementations, not just signatures.

        * **Multiple Composition**: Traits allow composing multiple traits into
          a single class. StaticType supports only a single borrowing source
          per class (linear derivation chain).

        * **Commutativity**: Traits are commutative—``A + B`` is equivalent to
          ``B + A``. StaticType is not commutative: deriving from ``A`` produces
          a different result than deriving from ``B``, and importantly, you can
          only derive from one source at a time.

        * **Associativity**: Traits are associative—``(A + B) + C`` is equivalent
          to ``A + (B + C)``. StaticType is not associative. Since you can only
          borrow from one parent, the derivation is a linear chain:
          ``Child → Parent → GrandParent``, not a tree or composition.

        .. _Traits: https://en.wikipedia.org/wiki/Traits_(computer_programming)

    Examples:
        First, create a class using StaticType as its metaclass.
        This class serves as the source of borrowed implementations::

            class Vehicle(metaclass=StaticType):
                def start(self) -> str:
                    return "Engine started"

                def stop(self) -> str:
                    return "Engine stopped"

        Now derive from it—attributes are copied (borrowed) to the new class::

            class Car(Vehicle):
                pass

            # Car borrows start() and stop() from Vehicle
            c = Car()
            c.start()  # Returns "Engine started"

        Deriving again creates a linear chain—each level borrows from its parent::

            class SportsCar(Car):
                pass

            # Linear chain: SportsCar → Car → Vehicle
            # SportsCar borrows from Car, which borrowed from Vehicle
            sc = SportsCar()
            sc.start()  # Returns "Engine started"

        Combine with :class:`typing.Protocol` to create a non-instantiable
        interface that can be implemented by derivation::

            class Drawable(Protocol, metaclass=StaticType):
                def draw(self) -> None: ...

            # Drawable cannot be instantiated (it's a Protocol)
            Drawable()  # Raises TypeError

            class Shape(Drawable):
                def draw(self) -> None:
                    print("Drawing shape")

            # Shape implements Drawable by derivation
            Shape().draw()  # Prints "Drawing shape"

    Raises:
        TypeError: If multiple concrete base classes are provided, or if
            attempting to create a Protocol from a non-Protocol concrete type.
    """

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
                closure=(),
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
            # Allow Protocol or ABC to be in bases along a concrete type
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
