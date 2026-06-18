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
# ruff: noqa: PLC0414, YTT204
"""
This module provides a collection of commonly used protocols
from Python's standard library and ``standard-deluxe`` itself, along with
utilities to retrieve, register, and manage protocols supported by a class.

The extensible protocol registry is backed by a :class:`~contextvars.ContextVar`,
enabling isolated protocol sets per execution context (asyncio tasks, thread pools, etc.)
without global side effects.

The :class:`ProtocolsContext` context manager allows temporary protocol
registration that is isolated from the module-level registry and from
other :class:`ProtocolsContext` instances.

Examples:
    Defining custom protocol::

        from deluxe.protocols import (
            ProtocolsContext, get_protocols, register, unregister,
        )
        from typing import Protocol, runtime_checkable

        @runtime_checkable
        class MyProto(Protocol):
            def my_method(self) -> int: ...

        class ImplementsMyProto:
            def my_method(self) -> int:
                return 42

    Temporarily register a protocol inside a context block, using
    :meth:`ProtocolsContext.get_protocols` to query the context-local
    registry ; the module-level :func:`get_protocols` is **not** affected::

        >>> proto_ctx = ProtocolsContext(MyProto)
        >>> with proto_ctx as ctx:
        ...     list(ctx.get_protocols(ImplementsMyProto))
        [<class 'MyProto'>]
        >>> list(get_protocols(ImplementsMyProto))
        []

    Register protocols after construction using :meth:`ProtocolsContext.register`::

        >>> with ProtocolsContext() as ctx:
        ...     ctx.register(MyProto)
        ...     list(ctx.get_protocols(ImplementsMyProto))
        [<class 'MyProto'>]

    Unregister built-in or custom protocols inside a context with
    :meth:`ProtocolsContext.unregister`. Changes are scoped to the
    context block::

        >>> with ProtocolsContext() as ctx:
        ...     ctx.unregister(Hashable)
        ...     list(ctx.get_protocols(int))
        []

    Reset the context to the built-in protocol set using
    :meth:`ProtocolsContext.reset`::

        >>> with ProtocolsContext() as ctx:
        ...     ctx.unregister(Hashable)
        ...     ctx.reset()
        ...     Hashable in list(ctx.get_protocols(int))
        True

    Two :class:`ProtocolsContext` instances are fully isolated from each
    other. Modifications in one do not affect the other::

        >>> with ProtocolsContext(MyProto) as ctx1:
        ...     with ProtocolsContext() as ctx2:
        ...         list(ctx2.get_protocols(ImplementsMyProto))
        []

    Nested contexts do not inherit protocols from the enclosing context.
    Each :class:`ProtocolsContext` starts from the built-in :obj:`__protocols__`
    set.
"""

from __future__ import annotations  # noqa: I001

from contextvars import Context, ContextVar, copy_context
import sys
from collections.abc import AsyncGenerator as AsyncGenerator
from collections.abc import AsyncIterable as AsyncIterable
from collections.abc import AsyncIterator as AsyncIterator
from collections.abc import Awaitable as Awaitable
from collections.abc import Callable as Callable
from collections.abc import Collection as Collection
from collections.abc import Container as Container
from collections.abc import Coroutine as Coroutine
from collections.abc import Generator as Generator
from collections.abc import Hashable as Hashable
from collections.abc import ItemsView as ItemsView
from collections.abc import Iterable as Iterable
from collections.abc import Iterator as Iterator
from collections.abc import KeysView as KeysView
from collections.abc import Mapping as Mapping
from collections.abc import MappingView as MappingView
from collections.abc import MutableMapping as MutableMapping
from collections.abc import MutableSequence as MutableSequence
from collections.abc import MutableSet as MutableSet
from collections.abc import Reversible as Reversible
from collections.abc import Sequence as Sequence
from collections.abc import Set as Set  # noqa: PYI025
from collections.abc import Sized as Sized
from collections.abc import ValuesView as ValuesView
from typing import IO as IO, Final, cast, final
from typing import Any
from typing import BinaryIO as BinaryIO
from typing import SupportsAbs as SupportsAbs
from typing import SupportsBytes as SupportsBytes
from typing import SupportsComplex as SupportsComplex
from typing import SupportsFloat as SupportsFloat
from typing import SupportsIndex as SupportsIndex
from typing import SupportsInt as SupportsInt
from typing import SupportsRound as SupportsRound
from typing import TextIO as TextIO, TYPE_CHECKING

from deluxe.functional import Monad as Monad
from deluxe.types import FrozenProtocol

if TYPE_CHECKING:
    from types import TracebackType


# NOTE: collection.abc.Sequence, typing.IO, typing.BinaryIO,
#       typing.TextIO are ABC not Protocol


__: set[type[Any]] = set[type[Any]]((
    # collections.abc
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    # ByteString: deprecated and useless,
    Callable,  # pyright: ignore[reportArgumentType]
    Collection,
    Container,
    Coroutine,
    Generator,
    Hashable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MappingView,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Reversible,
    Sequence,
    Set,
    Sized,
    ValuesView,
    # typing
    IO,
    BinaryIO,
    SupportsAbs,
    SupportsBytes,
    SupportsComplex,
    SupportsFloat,
    SupportsIndex,
    SupportsInt,
    SupportsRound,
    TextIO,
    # deluxe
    FrozenProtocol,
    Monad,
))


if sys.version_info.minor >= 12:  # pragma: no cover
    from collections.abc import (
        Buffer as Buffer,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]
    )

    __.add(Buffer)  # pyright: ignore[reportUnknownArgumentType]

if sys.version_info.minor >= 14:  # pragma: no cover
    from io import (
        Reader as Reader,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]
        Writer as Writer,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]
    )

    __.add(Reader)  # pyright: ignore[reportUnknownArgumentType]
    __.add(Writer)  # pyright: ignore[reportUnknownArgumentType]


__all__ = (
    "ProtocolsContext",
    "__protocols__",
    "get_protocols",
    "register",
    "reset",
    "unregister",
)

__protocols__: Final[frozenset[type[Any]]] = frozenset[type[Any]](__)
"""A :class:`frozenset` containing all built-in protocols."""


# ------------------------------------------------------------------------------
# Extensible protocol registry
# ------------------------------------------------------------------------------
_protocols = ContextVar[frozenset[Any]]("protocols", default=__protocols__.copy())  # noqa: B039


def register(*protocols: type[Any]) -> None:
    """Register additional protocols to check against in the default `Context`.

    Protocols registered via this function are included in every
    subsequent :func:`get_protocols` call alongside the built-in
    :obj:`__protocols__` set.

    Args:
        *protocols: One or more protocol (or ABC) classes to register.
    """
    _protocols.set(frozenset((*__protocols__, *protocols)))


def unregister(*protocols: type[Any]) -> None:
    """Unregister protocols that were previously registered in the default `Context`.

    Args:
        *protocols: One or more protocol (or ABC) classes to remove.
    """
    _protocols.set(_protocols.get().difference(protocols))


def reset() -> None:
    """Reset protocols in the default `Context` to the built-in :obj:`__protocols__` set."""
    _protocols.set(__protocols__.copy())


@final
class ProtocolsContext:
    """Context manager to temporarily register protocols.

    All *protocols* are checked by :func:`get_protocols` for the
    duration of the context block. When the block exits, only the
    protocols passed to the context manager are removed; any
    modifications via :func:`register` or :func:`unregister` inside
    the block persist unchanged.
    """

    def __init__(self, *protocols: type[Any]) -> None:
        self._context: Context = copy_context()
        self.register(*protocols)

    def __enter__(self) -> ProtocolsContext:
        return self

    def register(self, *protocols: type[Any]) -> None:
        """Register additional protocols to check against in this `Context`."""
        self._context.run(register, *protocols)

    def unregister(self, *protocols: type[Any]) -> None:
        """Unregister protocols that were previously registered in this `Context`."""
        self._context.run(unregister, *protocols)

    def reset(self) -> None:
        """Reset protocols in this `Context` to the built-in :obj:`__protocols__` set."""
        self._context.run(reset)

    def get_protocols(self, cls: type) -> Iterator[type[Any]]:
        """Return an iterator over protocols supported by *cls* in this context.

        Behaves like the module-level :func:`get_protocols` but uses the
        protocol set isolated in this :class:`ProtocolsContext`.

        Args:
            cls: The class to check for protocol support.
        """
        # Eagerly consume the inner generator inside the copied context
        # so that ContextVar lookups happen in the correct context.
        return iter(self._context.run(lambda: list(get_protocols(cls))))

    def __exit__(
        self, t: type[BaseException] | None, i: BaseException | None, tb: TracebackType | None
    ) -> None:
        del self._context


def _implements_protocol(cls: type, protocol: Any) -> bool:
    try:
        return issubclass(cls, protocol)
    except TypeError:
        pass

    # For non-runtime-checkable Protocols, do a structural check
    # similar to typing._proto_hook: verify each required attribute
    # exists in the class's MRO __dict__ (not inherited via __getattr__).
    protocol_attrs: frozenset[str] = getattr(
        protocol,
        "__protocol_attrs__",
        frozenset(),
    )
    if not protocol_attrs:
        return False

    # Check each required attribute exists in cls's MRO __dict__.
    # If an attribute is found but set to None, it's explicitly
    # `not implemented` (same convention as _proto_hook).
    for attr in protocol_attrs:
        for base in cls.__mro__:
            if attr in base.__dict__:
                if base.__dict__[attr] is None:
                    return False
                break
        else:
            return False

    return True


def get_protocols(cls: type) -> Iterator[type]:
    """Returns an Iterator over protocols supported by a class.

    Checks each protocol in :obj:`__protocols__` and any extra protocols
    registered via :func:`register` or a :class:`ProtocolsContext` against
    *cls* using structural subtyping rules (not just explicit inheritance).

    Notes:
        For ABCs (which use :meth:`~object.__subclasshook__`) and
        :func:`~typing.runtime_checkable` Protocols, this delegates to the
        standard :func:`issubclass` mechanism which performs structural checking.

        For non-:func:`~typing.runtime_checkable` Protocols, this manually
        verifies that all attributes listed in the protocol's
        ``__protocol_attrs__`` exist in the class's MRO ``__dict__``,
        mirroring the logic used by :func:`typing.runtime_checkable`'s
        ``_proto_hook``.

    Extra protocols can be added with:

    - :func:`register` for permanent registration
    - :class:`ProtocolsContext` for temporary registration within a
      context block

    Args:
        cls: The class to check for protocol support.

    Yields:
        Each protocol that the class supports.
    """
    all_protocols = _protocols.get()
    yield from (cast("type", proto) for proto in all_protocols if _implements_protocol(cls, proto))
