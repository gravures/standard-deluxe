# pyright: reportArgumentType=false, reportUnknownVariableType=false, reportUnknownLambdaType=false, reportOperatorIssue=false, reportAssignmentType=false, reportReturnType=false, reportCallIssue=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from __future__ import annotations

from operator import add
from typing import Any, TypeVar

import pytest
from deluxe.functional import MaybeCallable
from hypothesis import given
from hypothesis import strategies as st


# =============================================================================
# Data Strategies
# =============================================================================

int_strategy = st.integers(min_value=-1000, max_value=1000)
string_strategy = st.text(min_size=0, max_size=20)


# =============================================================================
# Helper functions for testing
# =============================================================================

_T = TypeVar("_T")


def identity_func(x: _T) -> _T:
    return x


def add_one(x: int) -> int:
    return x + 1


def double(x: int) -> int:
    return x * 2


def square(x: int) -> int:
    return x * x


def to_string(x: object) -> str:
    return str(x)


def to_int(x: int) -> int:
    return int(x)


# =============================================================================
# Construction Tests
# =============================================================================


def test_construct_with_plain_int():
    mc = MaybeCallable(42)
    assert mc.unwrap() == 42


def test_construct_with_plain_str():
    mc = MaybeCallable("hello")
    assert mc.unwrap() == "hello"


def test_construct_with_plain_none():
    mc = MaybeCallable(None)
    assert mc.unwrap() is None


def test_construct_with_callable():
    def func(x: int) -> int:
        return x * 2

    mc: Any = MaybeCallable(func)
    assert callable(mc)
    assert mc(21) == 42


def test_construct_with_lambda():
    mc: Any = MaybeCallable(lambda: 42)
    assert callable(mc)


def test_construct_with_plain_value_is_not_callable():
    mc: MaybeCallable[int] = MaybeCallable(42)
    with pytest.raises(TypeError, match="'int' object is not callable"):
        mc()


def test_construct_with_callable_is_callable():
    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    assert mc() == 42


# =============================================================================
# Pure Tests
# =============================================================================


@given(value=int_strategy)
def test_pure_returns_maybe_callable_instance(value: int):
    mc = MaybeCallable.pure(value)
    assert isinstance(mc, MaybeCallable)


@given(value=int_strategy)
def test_pure_wraps_value(value: int):
    mc = MaybeCallable.pure(value)
    assert mc.unwrap() == value


@given(value=int_strategy)
def test_pure_with_callable(value: int):
    def func() -> int:
        return value

    mc: Any = MaybeCallable.pure(func)
    assert mc() == value


# =============================================================================
# Unwrap Tests
# =============================================================================


@given(value=int_strategy)
def test_unwrap_returns_plain_value(value: int):
    mc = MaybeCallable(value)
    assert mc.unwrap() == value


@given(value=string_strategy)
def test_unwrap_with_string(value: str):
    mc = MaybeCallable(value)
    assert mc.unwrap() == value


def test_unwrap_with_none():
    mc = MaybeCallable(None)
    assert mc.unwrap() is None


def test_unwrap_raises_on_callable():
    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    with pytest.raises(TypeError, match="could only unwrap plain value"):
        mc.unwrap()


def test_unwrap_raises_on_lambda():
    mc: Any = MaybeCallable(lambda: 42)
    with pytest.raises(TypeError, match="could only unwrap plain value"):
        mc.unwrap()


# =============================================================================
# Call Tests
# =============================================================================


def test_call_on_plain_value_raises():
    mc: MaybeCallable[int] = MaybeCallable(42)
    with pytest.raises(TypeError, match="'int' object is not callable"):
        mc()


def test_call_on_callable_returns_result():
    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    assert mc() == 42


def test_call_on_lambda_returns_result():
    mc: Any = MaybeCallable(lambda: 99)
    assert mc() == 99


def test_call_with_args_forwards_to_callable():
    mc: Any = MaybeCallable(add)
    assert mc(3, 4) == 7


def test_call_with_kwargs_forwards_to_callable():
    def greet(name: str = "world") -> str:
        return f"hello {name}"

    mc: Any = MaybeCallable(greet)
    assert mc("test") == "hello test"


def test_call_preserves_callable_return_type():
    def func() -> str:
        return "result"

    mc: Any = MaybeCallable(func)
    result = mc()
    assert isinstance(result, str)
    assert result == "result"


# =============================================================================
# Map Tests
# =============================================================================


@given(value=int_strategy)
def test_map_on_plain_value(value: int):
    mc: MaybeCallable[int] = MaybeCallable(value)
    result = mc.map(lambda x: x * 2)
    assert isinstance(result, MaybeCallable)
    assert result.unwrap() == value * 2


@given(value=int_strategy)
def test_map_identity_law(value: int):
    mc: MaybeCallable[int] = MaybeCallable(value)
    mapped = mc.map(lambda x: x)
    assert mapped.unwrap() == mc.unwrap()


@given(value=int_strategy)
def test_map_composition_law(value: int):
    mc: MaybeCallable[int] = MaybeCallable(value)
    chained = mc.map(add_one).map(double)
    composed = mc.map(lambda x: double(add_one(x)))
    assert chained.unwrap() == composed.unwrap()


@given(value=int_strategy)
def test_map_returns_new_instance(value: int):
    mc: MaybeCallable[int] = MaybeCallable(value)
    result = mc.map(lambda x: x)
    assert result is not mc
    assert isinstance(result, MaybeCallable)


def test_map_on_callable_passes_callable_to_function():
    """When _value_ is callable, map passes the callable itself, not its result."""

    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    result: Any = mc.map(lambda x: x)
    assert isinstance(result, MaybeCallable)
    # map receives the callable itself, not the result of calling it
    assert result() == 42


def test_map_on_callable_can_transform_to_new_value():
    """map can transform a callable into a new value."""

    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    result: Any = mc.map(lambda f: f() * 2)
    assert isinstance(result, MaybeCallable)
    assert result.unwrap() == 84


@given(value=string_strategy)
def test_map_changes_type(value: str):
    mc: MaybeCallable[str] = MaybeCallable(value)
    result = mc.map(len)
    assert result.unwrap() == len(value)


# =============================================================================
# Bind Tests
# =============================================================================


@given(value=int_strategy)
def test_bind_left_identity_law(value: int):
    def to_maybe_callable(x: int) -> MaybeCallable[int]:
        return MaybeCallable(x * 2)

    pure = MaybeCallable(value)
    bound = pure.bind(to_maybe_callable)
    expected = to_maybe_callable(value)
    assert bound.unwrap() == expected.unwrap()


@given(value=int_strategy)
def test_bind_right_identity_law(value: int):
    mc = MaybeCallable(value)
    bound = mc.bind(MaybeCallable)
    assert bound.unwrap() == mc.unwrap()


@given(value=int_strategy)
def test_bind_associativity_law(value: int):
    mc = MaybeCallable(value)

    def f(x: int) -> MaybeCallable[int]:
        return MaybeCallable(x * 2)

    def g(x: int) -> MaybeCallable[str]:
        return MaybeCallable(str(x))

    left_side = mc.bind(f).bind(g)

    def composed(x: int) -> MaybeCallable[str]:
        return f(x).bind(g)

    right_side = mc.bind(composed)
    assert left_side.unwrap() == right_side.unwrap()


@given(value=int_strategy)
def test_bind_returns_new_instance(value: int):
    mc = MaybeCallable(value)
    result = mc.bind(MaybeCallable)
    assert result is not mc
    assert isinstance(result, MaybeCallable)


def test_bind_on_callable_passes_callable_to_function():
    """When _value_ is callable, bind passes the callable itself to the function."""

    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    result: Any = mc.bind(lambda f: MaybeCallable(f()))
    assert result.unwrap() == 42


def test_bind_with_string_transformation():
    mc: MaybeCallable[int] = MaybeCallable(42)
    result = mc.bind(lambda x: MaybeCallable(str(x)))
    assert result.unwrap() == "42"


# =============================================================================
# Join Tests
# =============================================================================


@given(value=int_strategy)
def test_join_returns_new_instance(value: int):
    mc = MaybeCallable(value)
    joined = mc.join()
    assert joined is not mc
    assert isinstance(joined, MaybeCallable)


@given(value=int_strategy)
def test_join_unwrap_equals_unwrap(value: int):
    mc = MaybeCallable(value)
    joined = mc.join()
    assert joined.unwrap() == mc.unwrap()


@given(value=int_strategy)
def test_join_idempotent(value: int):
    mc = MaybeCallable(value)
    joined_once = mc.join()
    joined_twice = mc.join().join()
    assert joined_once.unwrap() == joined_twice.unwrap()


def test_join_on_callable_raises_type_error():
    """join() calls unwrap() which raises TypeError on callables."""

    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    with pytest.raises(TypeError, match="could only unwrap plain value"):
        mc.join()


# =============================================================================
# Repr and Str Tests
# =============================================================================


def test_repr_on_plain_value():
    mc = MaybeCallable(42)
    repr_str = repr(mc)
    assert "MaybeCallable" in repr_str


def test_repr_on_callable():
    def func() -> int:
        return 42

    mc: Any = MaybeCallable(func)
    repr_str = repr(mc)
    assert "MaybeCallable" in repr_str


def test_str_on_plain_value():
    mc = MaybeCallable(42)
    assert str(mc) == "42"


def test_str_on_string_value():
    mc = MaybeCallable("hello")
    assert str(mc) == "hello"


def test_str_on_none():
    mc = MaybeCallable(None)
    assert str(mc) == "None"


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


@given(value=int_strategy)
def test_property_roundtrip_plain_value(value: int):
    """Unwrapping a plain value should return the original."""
    mc = MaybeCallable(value)
    assert mc.unwrap() == value


@given(value=int_strategy)
def test_property_pure_unwrap_roundtrip(value: int):
    """pure followed by unwrap should return the original value."""
    mc = MaybeCallable.pure(value)
    assert mc.unwrap() == value


@given(value=int_strategy)
def test_property_map_then_unwrap(value: int):
    """map followed by unwrap should apply the function."""
    mc = MaybeCallable(value)
    result = mc.map(lambda x: x + 1)
    assert result.unwrap() == value + 1


@given(value=int_strategy)
def test_property_bind_then_unwrap(value: int):
    """bind followed by unwrap should chain correctly."""
    mc = MaybeCallable(value)
    result = mc.bind(lambda x: MaybeCallable(x * 2))
    assert result.unwrap() == value * 2


@given(value=int_strategy)
def test_property_join_then_unwrap(value: int):
    """join followed by unwrap should return original value."""
    mc = MaybeCallable(value)
    joined = mc.join()
    assert joined.unwrap() == value


@given(value=int_strategy)
def test_property_call_equals_unwrap_on_callable(value: int):
    """Calling a callable MaybeCallable should equal unwrap on plain."""

    def func() -> int:
        return value

    mc_callable: Any = MaybeCallable(func)
    mc_plain = MaybeCallable(value)
    assert mc_callable() == mc_plain.unwrap()


@given(value=int_strategy)
def test_property_map_identity_preserves_value(value: int):
    """Mapping identity should preserve the value."""
    mc = MaybeCallable(value)
    result = mc.map(lambda x: x)
    assert result.unwrap() == mc.unwrap()


@given(value=int_strategy)
def test_property_map_composition(value: int):
    """Chaining maps should equal composing the functions."""
    mc = MaybeCallable(value)
    chained = mc.map(add_one).map(double)
    composed = mc.map(lambda x: double(add_one(x)))
    assert chained.unwrap() == composed.unwrap()


@given(value=int_strategy)
def test_property_bind_left_identity(value: int):
    """pure(x).bind(f) should equal f(x)."""

    def f(x: int) -> MaybeCallable[int]:
        return MaybeCallable(x * 2)

    left = MaybeCallable.pure(value).bind(f)
    right = f(value)
    assert left.unwrap() == right.unwrap()


@given(value=int_strategy)
def test_property_bind_right_identity(value: int):
    """m.bind(pure) should equal m."""
    mc = MaybeCallable(value)
    result = mc.bind(MaybeCallable)
    assert result.unwrap() == mc.unwrap()


@given(value=int_strategy)
def test_property_bind_associativity(value: int):
    """(m >>= f) >>= g should equal m >>= (\\x -> f(x) >>= g)."""
    mc = MaybeCallable(value)

    def f(x: int) -> MaybeCallable[int]:
        return MaybeCallable(x * 2)

    def g(x: int) -> MaybeCallable[str]:
        return MaybeCallable(str(x))

    left = mc.bind(f).bind(g)
    right = mc.bind(lambda x: f(x).bind(g))
    assert left.unwrap() == right.unwrap()


@given(value=int_strategy)
def test_property_map_bind_composition(value: int):
    """map then bind should be equivalent to bind with composed function."""
    mc = MaybeCallable(value)
    map_then_bind = mc.map(add_one).bind(lambda x: MaybeCallable(x * 2))
    bind_composed = mc.bind(lambda x: MaybeCallable(add_one(x) * 2))
    assert map_then_bind.unwrap() == bind_composed.unwrap()


@given(value=int_strategy)
def test_property_isinstance_maybe_callable(value: int):
    """All constructed instances should be MaybeCallable."""
    mc = MaybeCallable(value)
    assert isinstance(mc, MaybeCallable)


@given(value=int_strategy)
def test_property_callable_wrapper_raises_type_error(value: int):
    """Calling the wrapper for plain values should raise TypeError."""
    mc: MaybeCallable[int] = MaybeCallable(value)
    with pytest.raises(TypeError):
        mc()


@given(st.lists(int_strategy, max_size=10))
def test_property_multiple_operations_chain(values: list[int]):
    """Chaining multiple operations should work correctly."""
    mc: MaybeCallable[int] = MaybeCallable(0)
    for v in values:
        mc = mc.map(lambda x, v=v: x + v)
    assert mc.unwrap() == sum(values)
