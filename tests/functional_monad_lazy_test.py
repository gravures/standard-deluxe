from __future__ import annotations

from typing import Any, TypeVar

from deluxe.functional import Lazy
from hypothesis import given
from hypothesis import strategies as st


# =============================================================================
# Data Strategies
# =============================================================================

# Strategy for integers (safe for arithmetic operations)
int_strategy = st.integers(min_value=-1000, max_value=1000)

# Strategy for strings
string_strategy = st.text(min_size=0, max_size=20)

# Strategy for floats (avoiding NaN and infinity for predictable tests)
float_strategy = st.floats(
    min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False
)

# Strategy for lists of integers
list_strategy = st.lists(st.integers(min_value=-10, max_value=10), max_size=10)


# =============================================================================
# Helper functions for testing
# =============================================================================
_T = TypeVar("_T")


def identity_func(x: _T) -> _T:
    return x


def add_one(x: int):
    return x + 1


def double(x: int):
    return x * 2


def square(x: int):
    return x * x


def to_string(x: object):
    return str(x)


def to_lazy_string(x: object):
    return Lazy.pure(str(x))


def to_lazy_int(x: object):
    return Lazy.pure(int(x))  # pyright: ignore[reportArgumentType]


def to_lazy_doubled(x: float):
    return Lazy.pure(x * 2)


# =============================================================================
# Pure Properties
# =============================================================================


@given(value=int_strategy)
def test_property_pure_unwrap_returns_original_value(value: int):
    lazy = Lazy.pure(value)
    assert lazy.unwrap() == value


@given(value=int_strategy)
def test_property_pure_unwrap_is_idempotent(value: int):
    lazy = Lazy.pure(value)
    first = lazy.unwrap()
    second = lazy.unwrap()
    third = lazy.unwrap()
    assert first == value
    assert second == value
    assert third == value


@given(value=string_strategy)
def test_property_pure_with_strings(value: int):
    lazy = Lazy.pure(value)
    assert lazy.unwrap() == value


@given(value=float_strategy)
def test_property_pure_with_floats(value: float):
    lazy = Lazy.pure(value)
    assert lazy.unwrap() == value


# =============================================================================
# Map Properties (Functor Laws)
# =============================================================================


@given(value=int_strategy)
def test_property_map_identity_law(value: int):
    lazy = Lazy.pure(value)
    mapped = lazy.map(identity_func, int)
    assert mapped.unwrap() == lazy.unwrap()


@given(value=int_strategy)
def test_property_map_correct_application(value: int):
    lazy = Lazy.pure(value)
    result = lazy.map(add_one, int)
    assert result.unwrap() == add_one(value)


@given(value=int_strategy)
def test_property_map_composition_law(value: int):
    lazy = Lazy.pure(value)

    # Compose maps by chaining
    chained = lazy.map(add_one, int).map(double, int)

    # Compose by using a single composed function
    composed = lazy.map(lambda x: double(add_one(x)), int)

    assert chained.unwrap() == composed.unwrap()


@given(value=int_strategy)
def test_property_map_square_and_double_composition(value: int):
    lazy = Lazy.pure(value)

    # Chain: value -> value + 1 -> (value + 1)^2 -> (value + 1)^2 * 2
    result = lazy.map(add_one, int).map(square, int).map(double, int)

    expected = double(square(add_one(value)))
    assert result.unwrap() == expected


@given(value=int_strategy)
def test_property_map_transforms_types_correctly(value: int):
    lazy = Lazy.pure(value)
    result = lazy.map(to_string, str)
    assert result.unwrap() == str(value)
    assert isinstance(result.unwrap(), str)


@given(value=string_strategy)
def test_property_map_string_to_int(value: str):
    # Only test strings that can be converted to int
    try:
        int(value)
    except ValueError:
        return

    lazy = Lazy.pure(value)
    result = lazy.map(int, int)
    assert result.unwrap() == int(value)


# =============================================================================
# Bind Properties (Monad Laws)
# =============================================================================


@given(value=int_strategy)
def test_property_bind_left_identity_law(value: int):

    def to_lazy_doubled_local(x: float) -> Lazy[float]:
        return Lazy.pure(x * 2)

    pure = Lazy.pure(value)
    bound = pure.bind(to_lazy_doubled_local, int)
    expected = to_lazy_doubled_local(value)

    assert bound.unwrap() == expected.unwrap()


@given(value=int_strategy)
def test_property_bind_right_identity_law(value: int):
    lazy = Lazy.pure(value)
    bound = lazy.bind(Lazy.pure, int)
    assert bound.unwrap() == lazy.unwrap()


@given(value=int_strategy)
def test_property_bind_associativity_law(value: int):
    lazy = Lazy.pure(value)

    # Left side: (m >>= f) >>= g
    left_side = lazy.bind(to_lazy_doubled, int).bind(to_lazy_string, str)

    # Right side: m >>= (x -> f(x) >>= g)
    def composed(x: int):
        return to_lazy_doubled(x).bind(to_lazy_string, str)

    right_side = lazy.bind(composed, str)

    assert left_side.unwrap() == right_side.unwrap()


@given(value=int_strategy)
def test_property_bind_correct_application(value: int):
    lazy = Lazy.pure(value)
    result = lazy.bind(to_lazy_string, str)
    expected = to_lazy_string(value)
    assert result.unwrap() == expected.unwrap()


@given(value=int_strategy)
def test_property_bind_chain_multiple_operations(value: int):
    lazy = Lazy.pure(value)

    # Chain: int -> str -> int -> str
    result = lazy.bind(to_lazy_string, str).bind(to_lazy_int, int).bind(to_lazy_string, str)

    expected = to_lazy_string(to_lazy_int(to_lazy_string(value).unwrap()).unwrap()).unwrap()
    assert result.unwrap() == expected


# =============================================================================
# Join Properties
# =============================================================================


@given(value=int_strategy)
def test_property_join_unwrap_equals_unwrap(value: int):
    lazy = Lazy.pure(value)
    joined = lazy.join()
    assert joined.unwrap() == lazy.unwrap()


@given(value=int_strategy)
def test_property_join_creates_new_lazy_instance(value: int):
    lazy = Lazy.pure(value)
    joined = lazy.join()
    assert joined is not lazy
    assert isinstance(joined, Lazy)


@given(value=int_strategy)
def test_property_join_idempotent(value: int):
    lazy = Lazy.pure(value)
    joined_once = lazy.join()
    joined_twice = lazy.join().join()
    assert joined_once.unwrap() == joined_twice.unwrap()


# =============================================================================
# Call vs Unwrap Properties
# =============================================================================


@given(value=int_strategy)
def test_property_call_equals_unwrap(value: int):
    lazy = Lazy.pure(value)
    assert lazy() == lazy.unwrap()


@given(value=int_strategy)
def test_property_call_multiple_times_consistent(value: int):
    lazy = Lazy.pure(value)
    first = lazy()
    second = lazy()
    third = lazy()
    assert first == value
    assert second == value
    assert third == value


# =============================================================================
# Type Property
# =============================================================================


@given(value=int_strategy)
def test_property_type_returns_correct_type_int(value: int):
    lazy = Lazy.pure(value)
    assert lazy.type is int


@given(value=string_strategy)
def test_property_type_returns_correct_type_str(value: str):
    lazy = Lazy.pure(value)
    assert lazy.type is str


@given(value=float_strategy)
def test_property_type_returns_correct_type_float(value: float):
    lazy = Lazy.pure(value)
    assert lazy.type is float


@given(value=int_strategy)
def test_property_map_preserves_type_annotation(value: int):
    lazy = Lazy.pure(value)
    assert lazy.type is int

    mapped = lazy.map(to_string, str)
    assert mapped.type is str


# =============================================================================
# Lazy Evaluation Properties
# =============================================================================


@given(value=int_strategy)
def test_property_pure_defers_evaluation(value: int):
    call_count: list[int] = []

    def counting_func():
        call_count.append(1)
        return value

    # Create Lazy - function should not be called yet
    lazy = Lazy(counting_func, int)
    assert len(call_count) == 0

    # Unwrap - function should be called now
    result = lazy.unwrap()
    assert len(call_count) == 1
    assert result == value


@given(value=int_strategy)
def test_property_map_defers_evaluation(value: int):
    call_count: list[int] = []

    def counting_add_one(x: int):
        call_count.append(1)
        return x + 1

    lazy = Lazy.pure(value)

    # Map should not call the function yet
    mapped = lazy.map(counting_add_one, int)
    assert len(call_count) == 0

    # Unwrap should call the function now
    result = mapped.unwrap()
    assert len(call_count) == 1
    assert result == value + 1


@given(value=int_strategy)
def test_property_bind_defers_evaluation(value: int):
    call_count: list[int] = []

    def counting_to_lazy(x: int):
        call_count.append(1)
        return Lazy.pure(x * 2)

    lazy = Lazy.pure(value)

    # Bind should not call the function yet
    bound = lazy.bind(counting_to_lazy, int)
    assert len(call_count) == 0

    # Unwrap should call the function now
    result = bound.unwrap()
    assert len(call_count) == 1
    assert result == value * 2


# =============================================================================
# Combined Properties (Map + Bind)
# =============================================================================


@given(value=int_strategy)
def test_property_map_then_bind_composition(value: int):
    lazy = Lazy.pure(value)

    # map then bind
    map_then_bind = lazy.map(to_string, str).bind(to_lazy_int, int)

    # bind with composed function
    def composed(x: int):
        return to_lazy_int(to_string(x))

    bind_composed = lazy.bind(composed, int)

    assert map_then_bind.unwrap() == bind_composed.unwrap()


@given(value=int_strategy)
def test_property_bind_then_map_composition(value: int):
    lazy = Lazy.pure(value)

    # bind then map
    bind_then_map = lazy.bind(to_lazy_doubled, int).map(str, str)

    expected = str(to_lazy_doubled(value).unwrap())
    assert bind_then_map.unwrap() == expected


# =============================================================================
# Constructor Properties
# =============================================================================


@given(value=int_strategy)
def test_property_constructor_with_callable(value: int):

    def return_value():
        return value

    lazy = Lazy(return_value, int)
    assert lazy.type is int
    assert lazy.unwrap() == value


@given(value=int_strategy)
def test_property_constructor_with_lambda(value: int):
    lazy = Lazy(lambda: value, int)
    assert lazy.type is int
    assert lazy.unwrap() == value


@given(value=int_strategy)
def test_property_constructor_preserves_lazy_evaluation(value: int):
    call_count: list[int] = []

    def counting_func():
        call_count.append(1)
        return value

    lazy = Lazy(counting_func, int)
    assert len(call_count) == 0

    lazy.unwrap()
    assert len(call_count) == 1


# =============================================================================
# Nested Lazy Properties
# =============================================================================


@given(value=int_strategy)
def test_property_nested_lazy_with_map(value: int):
    inner = Lazy.pure(value)

    # Create Lazy containing another Lazy
    outer = Lazy(lambda: inner, Lazy)

    # Map over the outer to extract the inner value
    result = outer.map(lambda l: l.unwrap(), int)  # noqa: E741

    assert result.unwrap() == value


@given(value=int_strategy)
def test_property_nested_lazy_with_bind(value: int):
    inner = Lazy.pure(value)

    # Create Lazy containing another Lazy
    outer = Lazy(lambda: inner, Lazy)

    # Bind to extract the inner value
    def extract_inner(lazy_inner: Lazy[Any]):
        return lazy_inner

    result = outer.bind(extract_inner, int)

    assert result.unwrap() == value
