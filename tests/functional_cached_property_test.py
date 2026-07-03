"""Tests for the cached_property descriptor."""

from __future__ import annotations

import pytest
from deluxe.functional import cached_property


# =============================================================================
# Basic Functionality Tests
# =============================================================================


def test_cached_property_returns_correct_value():
    """cached_property returns the value computed by the wrapped function."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 42

    obj = MyClass()
    assert obj.value == 42


def test_cached_property_preserves_docstring():
    """cached_property preserves the docstring from the wrapped function."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            """The computed value."""  # noqa: DOC201
            return 42

    # The docstring is set on the descriptor, not the function
    assert MyClass.value.__doc__ == "The computed value."


def test_cached_property_preserves_empty_docstring():
    """cached_property handles functions with no docstring."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 99

    assert not MyClass.value.__doc__


# =============================================================================
# Caching Behavior Tests
# =============================================================================


def test_cached_property_computes_only_once():
    """cached_property computes the value only on first access."""
    call_count = 0

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            nonlocal call_count
            call_count += 1
            return 42

    obj = MyClass()
    _ = obj.value
    _ = obj.value
    _ = obj.value

    assert call_count == 1


def test_cached_property_returns_same_value_on_repeated_access():
    """cached_property returns the same value on repeated access."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 42

    obj = MyClass()
    first = obj.value
    second = obj.value
    third = obj.value

    assert first == second == third == 42


# =============================================================================
# Instance Isolation Tests
# =============================================================================


def test_cached_property_isolated_per_instance():
    """Each instance has its own cached value."""

    class MyClass:
        def __init__(self, x: int) -> None:
            self.x: int = x

        @cached_property
        def computed(self) -> int:
            return self.x * 2

    obj1 = MyClass(10)
    obj2 = MyClass(20)

    assert obj1.computed == 20
    assert obj2.computed == 40


def test_cached_property_different_instances_different_cached_values():
    """Different instances cache different values independently."""

    class MyClass:
        def __init__(self, x: int) -> None:
            self.x: int = x

        @cached_property
        def computed(self) -> int:
            return self.x * 2

    obj1 = MyClass(5)
    obj2 = MyClass(10)

    val1 = obj1.computed
    val2 = obj2.computed

    assert val1 == 10
    assert val2 == 20
    # Verify they are cached independently
    assert obj1.computed == 10
    assert obj2.computed == 20


# =============================================================================
# Class Access Tests
# =============================================================================


def test_cached_property_access_on_class_returns_descriptor():
    """Accessing cached_property on the class returns the descriptor itself."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 42

    descriptor = MyClass.value
    assert isinstance(descriptor, cached_property)


def test_cached_property_class_access_not_cached():
    """Accessing cached_property on class does not trigger computation."""
    call_count = 0

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            nonlocal call_count
            call_count += 1
            return 42

    _ = MyClass.value
    assert call_count == 0


# =============================================================================
# Read-Only Behavior Tests
# =============================================================================


def test_cached_property_set_raises_attribute_error():
    """Attempting to set a cached_property raises AttributeError."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 42

    obj = MyClass()
    with pytest.raises(AttributeError, match="has no setter"):
        obj.value = 100  # type: ignore[misc]


def test_cached_property_delete_raises_attribute_error():
    """Attempting to delete a cached_property raises AttributeError."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 42

    obj = MyClass()
    _ = obj.value  # Compute and cache first
    with pytest.raises(AttributeError, match="has no deleter"):
        del obj.value  # type: ignore[misc]


# =============================================================================
# __set_name__ Protocol Tests
# =============================================================================


def test_cached_property_set_name_sets_attributes():
    """__set_name__ correctly sets attrname, __objclass__, and __module__."""

    class Owner:
        pass

    prop = cached_property(lambda self: 42)  # noqa: ARG005
    prop.__set_name__(Owner, "my_prop")

    assert prop.attrname == "my_prop"
    assert prop.__objclass__ is Owner
    assert prop.__module__ == Owner.__module__


def test_cached_property_set_name_raises_on_rename():
    """__set_name__ raises TypeError when assigning to a different name."""

    class Owner:
        pass

    prop = cached_property(lambda self: 42)  # noqa: ARG005
    prop.__set_name__(Owner, "name_a")

    with pytest.raises(TypeError, match="Cannot assign the same cached_property"):
        prop.__set_name__(Owner, "name_b")


def test_cached_property_set_name_same_name_no_error():
    """__set_name__ with the same name does not raise."""

    class Owner:
        pass

    prop = cached_property(lambda self: 42)  # noqa: ARG005
    prop.__set_name__(Owner, "my_prop")
    prop.__set_name__(Owner, "my_prop")  # Should not raise

    assert prop.attrname == "my_prop"


# =============================================================================
# Multiple Cached Properties Tests
# =============================================================================


def test_multiple_cached_properties_independent():
    """Multiple cached_properties on the same class are independent."""

    class MyClass:
        @cached_property
        def first(self) -> str:  # noqa: PLR6301
            return "first"

        @cached_property
        def second(self) -> str:  # noqa: PLR6301
            return "second"

    obj = MyClass()

    assert obj.first == "first"
    assert obj.second == "second"


def test_multiple_cached_properties_each_cached_independently():
    """Each cached_property caches its value independently."""
    first_count = 0
    second_count = 0

    class MyClass:
        @cached_property
        def first(self) -> str:  # noqa: PLR6301
            nonlocal first_count
            first_count += 1
            return "first"

        @cached_property
        def second(self) -> str:  # noqa: PLR6301
            nonlocal second_count
            second_count += 1
            return "second"

    obj = MyClass()

    _ = obj.first
    _ = obj.first
    _ = obj.second

    # Both should be cached and return consistent values
    assert obj.first == "first"
    assert obj.second == "second"
    assert first_count == 1
    assert second_count == 1


# =============================================================================
# Edge Cases Tests
# =============================================================================


def test_cached_property_with_none_return_value():
    """cached_property correctly caches None as a valid value."""
    call_count = 0

    class MyClass:
        @cached_property
        def value(self) -> None:  # noqa: PLR6301
            nonlocal call_count
            call_count += 1
            return  # noqa: PLR1711

    obj = MyClass()
    assert obj.value is None
    assert call_count == 1
    # Access again - should still be None and not recomputed
    assert obj.value is None
    assert call_count == 1


def test_cached_property_with_false_return_value():
    """cached_property correctly caches False as a valid value."""

    class MyClass:
        @cached_property
        def value(self) -> bool:  # noqa: PLR6301
            return False

    obj = MyClass()
    assert obj.value is False


def test_cached_property_with_zero_return_value():
    """cached_property correctly caches 0 as a valid value."""

    class MyClass:
        @cached_property
        def value(self) -> int:  # noqa: PLR6301
            return 0

    obj = MyClass()
    assert obj.value == 0


def test_cached_property_with_empty_string_return_value():
    """cached_property correctly caches empty string as a valid value."""

    class MyClass:
        @cached_property
        def value(self) -> str:  # noqa: PLR6301
            return ""

    obj = MyClass()
    assert not obj.value


def test_cached_property_with_list_return_value():
    """cached_property correctly caches mutable objects like lists."""
    call_count = 0

    class MyClass:
        @cached_property
        def value(self) -> list[int]:  # noqa: PLR6301
            nonlocal call_count
            call_count += 1
            return [1, 2, 3]

    obj = MyClass()
    result1 = obj.value
    result2 = obj.value

    assert result1 == [1, 2, 3]
    assert result1 is result2  # Same object, not recomputed
    assert call_count == 1
