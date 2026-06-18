from __future__ import annotations

import sys
from typing import Any, Protocol, runtime_checkable

import pytest
from deluxe.functional import Lazy, Maybe

# Import from deluxe.protocols to test the exported items
from deluxe.protocols import (
    IO,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    BinaryIO,
    Callable,
    Collection,
    Container,
    Coroutine,
    Generator,
    Hashable,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MappingView,
    Monad,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Reversible,
    Sequence,
    Set,
    Sized,
    SupportsAbs,
    SupportsBytes,
    SupportsComplex,
    SupportsFloat,
    SupportsIndex,
    SupportsInt,
    SupportsRound,
    TextIO,
    ValuesView,
    ProtocolsContext,
    __protocols__,
    get_protocols,
    register,
    reset,
    unregister,
)
from collections import UserList, UserDict


if (sys.version_info.major, sys.version_info.minor) >= (3, 12):
    from deluxe.protocols import Buffer  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]

if (sys.version_info.major, sys.version_info.minor) >= (3, 14):
    from deluxe.protocols import Reader, Writer  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------
@pytest.fixture(autouse=True)  # noqa: RUF076
def _reset_protocols():  # pyright: ignore[reportUnusedFunction]
    """Reset protocols before each test to ensure isolation."""
    reset()


# ------------------------------------------------------------------------------
# Test Protocol for Registration Testing
# ------------------------------------------------------------------------------
@runtime_checkable
class CustomProtocol(Protocol):
    """A test protocol for registration testing."""

    def custom_method(self) -> int: ...


class ImplementsCustomProtocol:
    """A class that implements CustomProtocol."""

    def custom_method(self) -> int:  # noqa: PLR6301
        return 42


class DoesNotImplementCustomProtocol:
    """A class that does not implement CustomProtocol."""


# ------------------------------------------------------------------------------
# Helper Classes for Testing
# ------------------------------------------------------------------------------
class SimpleSequence(UserList[Any]):
    """A simple sequence implementation."""


class SimpleMapping(UserDict):  # pyright: ignore[reportMissingTypeArgument]
    """A simple mapping implementation."""


class HashableClass:
    """A hashable class."""

    def __init__(self, value: int) -> None:
        self.value: int = value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, HashableClass) and self.value == other.value


class UnhashableClass(UserList):  # pyright: ignore[reportMissingTypeArgument]
    """An unhashable class (inherits from list)."""


class SizedClass:
    """A class that implements Sized."""

    def __len__(self) -> int:
        return 42


class IterableClass:
    """A class that implements Iterable."""

    def __iter__(self) -> Iterator[int]:
        return iter([1, 2, 3])


class ContainerClass:
    """A class that implements Container."""

    def __contains__(self, item: Any) -> bool:
        return item in {1, 2, 3}


class AsyncIterableClass:
    """A class that implements AsyncIterable."""

    async def __aiter__(self) -> AsyncIterator[int]:
        self._iter: Iterator[int] = iter([1, 2, 3])  # pyright: ignore[reportUninitializedInstanceVariable]
        return self  # pyright: ignore[reportReturnType]

    async def __anext__(self) -> int:
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration  # noqa: B904


# ------------------------------------------------------------------------------
# Test __protocols__ Set Content
# ------------------------------------------------------------------------------
def test_protocols_set_contains_collections_abc_protocols():
    """Test that __protocols__ contains all expected collections.abc protocols."""
    expected_collections = {
        AsyncGenerator,
        AsyncIterable,
        AsyncIterator,
        Awaitable,
        Callable,
        Collection,
        Container,
        Coroutine,
        Generator,
        Hashable,
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
    }
    assert expected_collections.issubset(__protocols__)


def test_protocols_set_contains_typing_protocols():
    """Test that __protocols__ contains all expected typing protocols."""
    expected_typing = {
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
    }
    assert expected_typing.issubset(__protocols__)


def test_protocols_set_contains_monad():
    """Test that __protocols__ contains the Monad protocol."""
    assert Monad in __protocols__


def test_protocols_set_does_not_contain_bytestring():
    """Test that __protocols__ does not contain deprecated ByteString."""
    # ByteString is explicitly excluded
    from collections.abc import ByteString  # noqa: PLC0415, PYI057

    assert ByteString not in __protocols__


# ------------------------------------------------------------------------------
# Version-Specific Protocols
# ------------------------------------------------------------------------------
def test_buffer_protocol_present_in_python_312():
    """Test that Buffer protocol is present in Python 3.12+."""
    if (sys.version_info.major, sys.version_info.minor) >= (3, 12):
        assert Buffer in __protocols__  # pyright: ignore[reportPossiblyUnboundVariable]
    else:
        # Buffer should not be available as an import
        # but we also don't expect it in __protocols__
        assert "Buffer" not in globals()


def test_reader_writer_protocols_present_in_python_314():
    """Test that Reader and Writer protocols are present in Python 3.14+."""
    if (sys.version_info.major, sys.version_info.minor) >= (3, 14):
        assert Reader in __protocols__  # pyright: ignore[reportPossiblyUnboundVariable]
        assert Writer in __protocols__  # pyright: ignore[reportPossiblyUnboundVariable]
    else:
        # Reader and Writer should not be available as imports
        assert "Reader" not in globals()
        assert "Writer" not in globals()


# ------------------------------------------------------------------------------
# get_protocols Function Tests
# ------------------------------------------------------------------------------
def test_get_protocols_with_sequence():
    """Test get_protocols returns correct protocols for list."""
    list_protocols = list(get_protocols(list))
    assert Sequence in list_protocols
    assert Iterable in list_protocols
    assert Sized in list_protocols
    assert Container in list_protocols


def test_get_protocols_with_dict():
    """Test get_protocols returns correct protocols for dict."""
    dict_protocols = list(get_protocols(dict))
    assert Mapping in dict_protocols
    assert Iterable in dict_protocols
    assert Sized in dict_protocols
    assert Container in dict_protocols


def test_get_protocols_with_string():
    """Test get_protocols returns correct protocols for str."""
    str_protocols = list(get_protocols(str))
    assert Sequence in str_protocols
    assert Iterable in str_protocols
    assert Sized in str_protocols
    assert Container in str_protocols


def test_get_protocols_with_set_type():
    """Test get_protocols returns correct protocols for set."""
    set_protocols = list(get_protocols(set))
    assert Set in set_protocols
    assert Iterable in set_protocols
    assert Sized in set_protocols
    assert Container in set_protocols


def test_get_protocols_with_int():
    """Test get_protocols returns correct protocols for int."""
    int_protocols = list(get_protocols(int))
    # Int should not support most container protocols
    assert Sequence not in int_protocols
    assert Iterable not in int_protocols
    assert Hashable in int_protocols


def test_get_protocols_with_custom_sequence():
    """Test get_protocols works with custom sequence classes."""
    custom_protocols = list(get_protocols(SimpleSequence))
    assert Sequence in custom_protocols
    assert Iterable in custom_protocols
    assert Sized in custom_protocols


def test_get_protocols_with_custom_mapping():
    """Test get_protocols works with custom mapping classes."""
    custom_protocols = list(get_protocols(SimpleMapping))
    assert Mapping in custom_protocols
    assert Iterable in custom_protocols
    assert Sized in custom_protocols


def test_get_protocols_with_hashable_class():
    """Test get_protocols works with hashable custom classes."""
    hashable_protocols = list(get_protocols(HashableClass))
    assert Hashable in hashable_protocols


def test_get_protocols_with_unhashable_class():
    """Test get_protocols works with unhashable custom classes."""
    unhashable_protocols = list(get_protocols(UnhashableClass))
    assert Hashable not in unhashable_protocols
    assert Sequence in unhashable_protocols


def test_get_protocols_returns_iterator():
    """Test that get_protocols returns an iterator."""
    result = get_protocols(list)
    assert hasattr(result, "__iter__")
    assert hasattr(result, "__next__")


def test_get_protocols_can_be_consumed_multiple_times():
    """Test that get_protocols iterator cannot be reused (it's a generator)."""
    protocols_iter = get_protocols(list)
    first_time = list(protocols_iter)
    second_time = list(protocols_iter)
    # The second call should return empty since iterators are exhausted
    assert len(first_time) > 0
    assert len(second_time) == 0


def test_get_protocols_with_lazy_monad():
    """Test get_protocols works with Lazy monad."""
    lazy_protocols = list(get_protocols(Lazy))
    assert Lazy not in lazy_protocols  # Lazy is a concrete class
    # Lazy is not in __protocols__, only the Monad protocol is
    # So we shouldn't expect any protocol match


def test_get_protocols_with_maybe():
    """Test get_protocols works with Maybe class."""
    maybe_protocols = list(get_protocols(Maybe))
    # Maybe is a concrete class, not a protocol
    assert Maybe not in maybe_protocols


# ------------------------------------------------------------------------------
# Integration Tests with Various Types
# ------------------------------------------------------------------------------
def test_tuple_protocols():
    """Test protocols for tuple."""
    tuple_protocols = list(get_protocols(tuple))
    assert Sequence in tuple_protocols
    assert Iterable in tuple_protocols
    assert Sized in tuple_protocols
    assert Container in tuple_protocols
    assert Hashable in tuple_protocols


def test_bytes_protocols():
    """Test protocols for bytes."""
    bytes_protocols = list(get_protocols(bytes))
    assert Sequence in bytes_protocols
    assert Iterable in bytes_protocols
    assert Sized in bytes_protocols
    assert Container in bytes_protocols
    assert Hashable in bytes_protocols


def test_bytearray_protocols():
    """Test protocols for bytearray."""
    bytearray_protocols = list(get_protocols(bytearray))
    assert Sequence in bytearray_protocols
    assert Iterable in bytearray_protocols
    assert Sized in bytearray_protocols
    assert Container in bytearray_protocols
    assert Hashable not in bytearray_protocols


def test_range_protocols():
    """Test protocols for range."""
    range_protocols = list(get_protocols(range))
    assert Sequence in range_protocols
    assert Iterable in range_protocols
    assert Sized in range_protocols
    assert Container in range_protocols
    assert Reversible in range_protocols


def test_frozenset_protocols():
    """Test protocols for frozenset."""
    frozenset_protocols = list(get_protocols(frozenset))
    assert Set in frozenset_protocols
    assert Iterable in frozenset_protocols
    assert Sized in frozenset_protocols
    assert Container in frozenset_protocols
    assert Hashable in frozenset_protocols


# ------------------------------------------------------------------------------
# Error Handling Tests
# ------------------------------------------------------------------------------
def test_get_protocols_with_none_type():
    """Test get_protocols with NoneType."""
    none_protocols = list(get_protocols(type(None)))
    # NoneType should support Hashable
    assert Hashable in none_protocols


def test_get_protocols_with_callable_type():
    """Test get_protocols with callable objects."""

    def dummy_func():
        pass

    func_protocols = list(get_protocols(type(dummy_func)))
    # Functions should support Callable
    assert Callable in func_protocols


# ------------------------------------------------------------------------------
# Multiple Protocol Support
# ------------------------------------------------------------------------------
def test_class_supporting_multiple_protocols():
    """Test a class that supports multiple protocols."""

    class CustomSeq(UserList[Any]):
        pass

    protocols = list(get_protocols(CustomSeq))
    # Should support all the protocols that list supports
    assert Sequence in protocols
    assert Iterable in protocols
    assert Sized in protocols
    assert Container in protocols
    assert Reversible in protocols


def test_empty_class_protocols():
    """Test protocols for an empty class."""

    class Empty:
        pass

    empty_protocols = list(get_protocols(Empty))
    # Empty class should at least be hashable
    assert Hashable in empty_protocols


def test_class_with_slots_protocols():
    """Test protocols for a class with __slots__."""

    class Slotted:
        __slots__ = ["x"]  # pyright: ignore[reportUnannotatedClassAttribute]

        def __init__(self) -> None:
            self.x: int = 42

    slotted_protocols = list(get_protocols(Slotted))
    assert Hashable in slotted_protocols


# ------------------------------------------------------------------------------
# Module-Level register/unregister/reset Tests
# ------------------------------------------------------------------------------
def test_register_adds_protocol():
    """Test that register adds a protocol to the default context."""
    register(CustomProtocol)
    protocols = list(get_protocols(ImplementsCustomProtocol))
    assert CustomProtocol in protocols


def test_register_does_not_affect_non_implementing_classes():
    """Test that registered protocol is not found for non-implementing classes."""
    register(CustomProtocol)
    protocols = list(get_protocols(DoesNotImplementCustomProtocol))
    assert CustomProtocol not in protocols


def test_unregister_removes_registered_protocol():
    """Test that unregister removes a previously registered protocol."""
    register(CustomProtocol)
    unregister(CustomProtocol)
    protocols = list(get_protocols(ImplementsCustomProtocol))
    assert CustomProtocol not in protocols


def test_unregister_removes_builtin_protocol():
    """Test that unregister can remove a built-in protocol."""
    unregister(Hashable)
    protocols = list(get_protocols(HashableClass))
    assert Hashable not in protocols


def test_unregister_nonexistent_protocol():
    """Test that unregister does not raise when protocol is not in the set."""
    unregister(CustomProtocol)
    # Also unregister something that was already removed
    unregister(CustomProtocol)


def test_unregister_one_protocol_does_not_affect_others():
    """Test that unregistering a protocol doesn't affect other protocol checks."""
    unregister(Hashable)
    protocols = list(get_protocols(IterableClass))
    assert Iterable in protocols


def test_reset_restores_builtin_protocols_after_register():
    """Test that reset restores built-in protocols after register."""
    register(CustomProtocol)
    reset()
    protocols = list(get_protocols(ImplementsCustomProtocol))
    assert CustomProtocol not in protocols


def test_reset_restores_builtin_protocols_after_unregister():
    """Test that reset restores built-in protocols after unregister."""
    unregister(Hashable)
    reset()
    protocols = list(get_protocols(HashableClass))
    assert Hashable in protocols


def test_register_then_unregister_then_check_builtins():
    """Test register followed by unregister and verify builtins still work."""
    register(CustomProtocol)
    unregister(CustomProtocol)
    protocols = list(get_protocols(ImplementsCustomProtocol))
    assert CustomProtocol not in protocols
    # Built-in protocols should still work
    assert Hashable in list(get_protocols(HashableClass))


# ------------------------------------------------------------------------------
# ProtocolsContext Tests
# ------------------------------------------------------------------------------
def test_protocols_context_adds_protocols_temporarily():
    """Test that ProtocolsContext temporarily adds protocols inside the block."""
    with ProtocolsContext(CustomProtocol) as ctx:
        inside = list(ctx.get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol in inside

    # Outside the block, the module-level get_protocols should not find it
    outside = list(get_protocols(ImplementsCustomProtocol))
    assert CustomProtocol not in outside


def test_protocols_context_does_not_leak_to_outer_context():
    """Test that ProtocolsContext changes don't leak to the outer context."""
    with ProtocolsContext(CustomProtocol):
        pass
    outside = list(get_protocols(ImplementsCustomProtocol))
    assert CustomProtocol not in outside


def test_protocols_context_does_not_affect_module_level_get_protocols():
    """Test that module-level get_protocols is unaffected inside a ProtocolsContext."""
    with ProtocolsContext(CustomProtocol):
        # Module-level get_protocols should NOT see the context's protocols
        protocols = list(get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol not in protocols


def test_protocols_context_register_method():
    """Test that register method on ProtocolsContext works."""
    with ProtocolsContext() as ctx:
        ctx.register(CustomProtocol)
        protocols = list(ctx.get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol in protocols


def test_protocols_context_register_then_module_level_unaffected():
    """Test that ctx.register does not affect module-level get_protocols."""
    with ProtocolsContext() as ctx:
        ctx.register(CustomProtocol)
        protocols = list(get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol not in protocols


def test_protocols_context_unregister_method():
    """Test that unregister method on ProtocolsContext works."""
    with ProtocolsContext() as ctx:
        ctx.register(CustomProtocol)
        ctx.unregister(CustomProtocol)
        protocols = list(ctx.get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol not in protocols


def test_protocols_context_unregister_builtin():
    """Test that unregister of built-in protocol inside ProtocolsContext works."""
    with ProtocolsContext() as ctx:
        ctx.unregister(Hashable)
        protocols = list(ctx.get_protocols(HashableClass))
        assert Hashable not in protocols


def test_protocols_context_unregister_builtin_does_not_leak():
    """Test that unregister of built-in inside context does not leak."""
    with ProtocolsContext() as ctx:
        ctx.unregister(Hashable)
    # Outside, Hashable should still be found
    protocols = list(get_protocols(HashableClass))
    assert Hashable in protocols


def test_protocols_context_reset_method():
    """Test that reset method on ProtocolsContext restores built-in protocols."""
    with ProtocolsContext() as ctx:
        ctx.unregister(Hashable)
        ctx.reset()
        protocols = list(ctx.get_protocols(HashableClass))
        assert Hashable in protocols


def test_protocols_context_get_protocols_for_non_implementing():
    """Test that get_protocols on context does not match non-implementing classes."""
    with ProtocolsContext(CustomProtocol) as ctx:
        protocols = list(ctx.get_protocols(DoesNotImplementCustomProtocol))
        assert CustomProtocol not in protocols


def test_protocols_context_empty():
    """Test ProtocolsContext with no arguments works like module-level."""
    with ProtocolsContext() as ctx:
        protocols = list(ctx.get_protocols(list))
        assert Sequence in protocols
        assert Iterable in protocols
        assert Sized in protocols


def test_protocols_context_initial_registration():
    """Test that protocols passed to ProtocolsContext constructor are registered."""
    with ProtocolsContext(CustomProtocol) as ctx:
        protocols = list(ctx.get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol in protocols


def test_nested_protocols_contexts_are_isolated():
    """Test that two ProtocolsContext instances are isolated from each other."""
    with ProtocolsContext(CustomProtocol) as ctx1:
        protocols1 = list(ctx1.get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol in protocols1

        with ProtocolsContext() as ctx2:
            # ctx2 should not have CustomProtocol
            protocols2 = list(ctx2.get_protocols(ImplementsCustomProtocol))
            assert CustomProtocol not in protocols2


def test_protocols_context_does_not_affect_other_context():
    """Test that modifications in one context don't affect another context."""
    with ProtocolsContext(CustomProtocol) as ctx1:  # noqa: F841
        pass

    # ctx2 is a fresh context, should not have CustomProtocol
    with ProtocolsContext() as ctx2:
        protocols = list(ctx2.get_protocols(ImplementsCustomProtocol))
        assert CustomProtocol not in protocols
