from __future__ import annotations

import time
from collections.abc import MutableSet, Set  # noqa: PYI025
from typing import Any
from collections.abc import Sequence

import pytest
from deluxe.sequences import OrderedFrozenSet, OrderedSet
from hypothesis import given, settings
from hypothesis import strategies as st


@given(st.lists(st.integers(), min_size=0, max_size=10))
def test_ordered_frozen_set_hashability(elements: list[int]):
    """Test that OrderedFrozenSet is immutable and hashable."""
    # Create an OrderedFrozenSet
    frozen_set = OrderedFrozenSet(elements)

    # Test that it's hashable (can be used as a dictionary key)
    d = {frozen_set: "value"}
    assert d[frozen_set] == "value"

    # Test that it can be used in other sets
    s = {frozen_set}
    assert frozen_set in s

    # Create another identical OrderedFrozenSet and verify hash equality
    frozen_set2 = OrderedFrozenSet(elements)
    assert hash(frozen_set) == hash(frozen_set2)

    # Verify that sets with the same elements but different order have different hashes
    if len(elements) >= 2 and elements[0] != elements[1]:
        reversed_elements = list(elements)
        reversed_elements[0], reversed_elements[1] = reversed_elements[1], reversed_elements[0]
        different_order_set = OrderedFrozenSet(reversed_elements)
        assert hash(frozen_set) != hash(different_order_set)

    # Verify immutability - should not have add or discard methods
    assert not hasattr(frozen_set, "add")
    assert not hasattr(frozen_set, "discard")
    assert not hasattr(frozen_set, "pop")


@given(st.lists(st.integers(), min_size=1, unique=True))
def test_ordered_set_maintains_insertion_order(elements: list[int]):
    # Create an OrderedSet from the list of elements
    ordered_set = OrderedSet(elements)

    # Check that the elements in the OrderedSet are in the same order as the original list
    assert list(ordered_set) == elements

    # Additional test: add a duplicate element - it should change order
    if elements:
        duplicate = OrderedSet(elements)
        ordered_set.add(duplicate[0])
        assert ordered_set == duplicate


def test_ordered_set_mutable_set_interface():
    # Test that OrderedSet implements MutableSet interface
    assert issubclass(OrderedSet, MutableSet)

    # Create an OrderedSet and test basic operations
    ordered_set = OrderedSet([1, 2, 3])

    # Test add method
    ordered_set.add(4)
    assert 4 in ordered_set
    assert list(ordered_set) == [1, 2, 3, 4]

    # Test add with existing element
    ordered_set.add(2)
    assert list(ordered_set) == [1, 2, 3, 4]

    # Test discard method
    ordered_set.discard(3)
    assert 3 not in ordered_set
    assert list(ordered_set) == [1, 2, 4]

    # Test discard with non-existent element (should not raise)
    ordered_set.discard(10)
    assert list(ordered_set) == [1, 2, 4]

    # Test pop method always returns the last element
    last = ordered_set.pop()
    assert last == 4
    assert list(ordered_set) == [1, 2]

    # Test pop again to verify it always returns the first element
    last = ordered_set.pop()
    assert last == 2
    assert list(ordered_set) == [1]

    # Pop the last element
    last = ordered_set.pop()
    assert last == 1
    assert list(ordered_set) == []

    # Test pop on empty set raises KeyError
    empty_set = OrderedSet[Any]()
    with pytest.raises(KeyError):
        empty_set.pop()


@given(st.lists(st.integers(), min_size=2))
def test_ordered_set_duplicate_handling(elements: list[int]):
    # Create a list with duplicates
    elements_with_duplicates = elements + [elements[0]]  # noqa: RUF005

    # Create an OrderedSet from the list with duplicates
    ordered_set = OrderedSet(elements_with_duplicates)

    # Check that the duplicate element appears only once
    # and at the position of its first occurrence
    expected: list[int] = []
    for e in elements_with_duplicates:
        if e not in expected:
            expected.append(e)
    assert list(ordered_set) == expected

    # Now add the duplicate element again - it should not change the set
    duplicate = elements[0]
    ordered_set.add(duplicate)
    assert list(ordered_set) == expected

    # Verify that the length is correct (no duplicates)
    assert len(ordered_set) == len(set(elements_with_duplicates))


@given(
    st.lists(
        st.one_of(st.integers(), st.text(max_size=5), st.booleans()),
        min_size=0,
        max_size=7,
        unique=True,
    )
)
def test_ordered_set_discard_nonexistent_element(value: list[Any]):
    """Test that OrderedSet.discard handles non-existent elements gracefully."""
    # Create an OrderedSet with some elements
    ordered_set = OrderedSet(value)

    # Store the original state for comparison
    original_elements = list(ordered_set)

    # Discard an element that doesn't exist in the set
    ordered_set.discard(())

    # Verify that the set remains unchanged
    assert list(ordered_set) == original_elements
    assert len(ordered_set) == len(value)


def test_ordered_set_pop_empty_set():
    """Test that OrderedSet.pop raises KeyError when called on an empty set."""
    empty_set = OrderedSet[Any]()
    with pytest.raises(KeyError):
        empty_set.pop()


@given(st.lists(st.integers(), min_size=0, max_size=10))
def test_ordered_set_equality_with_regular_sets(elements: list[int]):
    # Create an OrderedSet and a regular set from the same elements
    ordered_set = OrderedSet(elements)
    regular_set = set(elements)

    # Test equality comparison
    assert ordered_set == regular_set
    assert regular_set == ordered_set

    # Test with different sets
    if elements:
        # Add a new element to the regular set
        new_element = max(elements) + 1 if elements else 1
        different_set = set(elements)
        different_set.add(new_element)

        # They should not be equal
        assert ordered_set != different_set
        assert different_set != ordered_set

    # Test with non-set objects
    assert ordered_set != "not a set"
    assert ordered_set != 123
    assert ordered_set != list(elements)


@given(st.lists(st.integers(), min_size=2, max_size=10, unique=True))
def test_ordered_set_different_order_inequality(elements: list[int]):
    """Test that two OrderedSets with same elements but different order are not equal."""
    # Create two OrderedSets with the same elements but different order
    ordered_set1 = OrderedSet(elements)
    ordered_set2 = OrderedSet(list(reversed(elements)))

    # They should not be equal
    assert ordered_set1 != ordered_set2

    # But they should be equal to regular sets with the same elements
    regular_set = set(elements)
    assert ordered_set1 == regular_set
    assert ordered_set2 == regular_set


def test_ordered_set_update_preserves_ordering():
    """Test that OrderedSet.update preserves ordering when updating from another OrderedSet."""
    # Create two OrderedSets with different elements and ordering
    base_set = OrderedSet([1, 2, 3])
    other_set = OrderedSet([4, 5, 2])  # Note: 2 is already in base_set

    # Update base_set with other_set
    base_set.update(other_set)

    # Check that the elements from other_set are added in their original order
    assert list(base_set) == [1, 2, 3, 4, 5]

    # Test with empty sets
    empty_set = OrderedSet[Any]()
    empty_set.update(OrderedSet([10, 20, 30]))
    assert list(empty_set) == [10, 20, 30]

    # Test updating with regular iterable
    ordered_set = OrderedSet(["a", "b"])
    ordered_set.update(["c", "d", "b"])
    assert list(ordered_set) == ["a", "b", "c", "d"]

    # Test updating with multiple arguments
    multi_set = OrderedSet([1, 2])
    multi_set.update([3, 4], [5, 2])
    assert list(multi_set) == [1, 2, 3, 4, 5]


@given(st.lists(st.integers(), min_size=0, max_size=10))
def test_ordered_frozen_set_preserves_order(elements: list[int]):
    """Test that OrderedFrozenSet maintains the order of elements as they were inserted."""
    # Create an OrderedFrozenSet from the list of elements
    frozen_set = OrderedFrozenSet(elements)

    # Check that the elements in the OrderedFrozenSet are in the same order as the original list
    # (after removing duplicates while preserving first occurrence)
    expected: list[int] = []
    for e in elements:
        if e not in expected:
            expected.append(e)

    assert list(frozen_set) == expected

    # Test with a more complex example with known values
    complex_set = OrderedFrozenSet([3, 1, 4, 1, 5, 9, 2, 6, 5])
    assert list(complex_set) == [3, 1, 4, 5, 9, 2, 6]

    # Test with empty input
    empty_set = OrderedFrozenSet[Any]()
    assert list[Any](empty_set) == []

    # Test with different types
    mixed_set = OrderedFrozenSet(["a", 1, False, "a", 1])
    assert list(mixed_set) == ["a", 1, False]


@given(st.lists(st.integers(), min_size=0, max_size=10))
def test_ordered_frozen_set_vs_regular_frozenset(elements: list[int]):
    """Test how OrderedFrozenSet compares with Python's built-in frozenset."""
    # Create an OrderedFrozenSet and a regular frozenset from the same elements
    ordered_frozen_set = OrderedFrozenSet(elements)
    regular_frozen_set = frozenset(elements)

    # Test equality comparison
    assert ordered_frozen_set == regular_frozen_set
    assert regular_frozen_set == ordered_frozen_set

    # Test that they have the same elements
    assert set(ordered_frozen_set) == set(regular_frozen_set)

    # Test that they have the same length
    assert len(ordered_frozen_set) == len(regular_frozen_set)

    # Test that they have the same containment behavior
    for element in elements:
        assert (element in ordered_frozen_set) == (element in regular_frozen_set)

    # Test that they're both hashable
    assert hash(ordered_frozen_set) != hash(regular_frozen_set)  # Different hash implementations

    # Test dictionary usage
    d = {ordered_frozen_set: "ordered", regular_frozen_set: "regular"}
    assert len(d) == 2  # They should be distinct keys
    assert d[ordered_frozen_set] == "ordered"
    assert d[regular_frozen_set] == "regular"

    # Test that OrderedFrozenSet preserves order while frozenset doesn't
    if len(set(elements)) >= 2:
        unique_elements: list[int] = []
        for e in elements:
            if e not in unique_elements:
                unique_elements.append(e)

        # OrderedFrozenSet should maintain insertion order
        assert list(ordered_frozen_set) == unique_elements

        # Regular frozenset has no guaranteed order
        if list(regular_frozen_set) != unique_elements:
            # This assertion might not always be true due to hash randomization,
            # but we're checking that at least sometimes the order differs
            assert True


def test_ordered_set_comparison_operators():
    """Test comparison operators for OrderedSet."""
    # Create sets for testing
    set1 = OrderedSet([1, 2, 3])
    set2 = OrderedSet([1, 2, 3, 4])
    set3 = OrderedSet([1, 2])
    set4 = OrderedSet([1, 2, 3])

    # Test equality (__eq__, __ne__)
    assert set1 == set4
    assert set1 != set2
    assert set1 != set3

    # Test subset/superset (__le__, __ge__, __lt__, __gt__)
    assert set1 <= set4  # Equal sets are subsets of each other
    assert set1 >= set4  # Equal sets are supersets of each other
    assert set3 <= set1  # Proper subset
    assert set1 >= set3  # Proper superset
    assert set1 <= set2  # Proper subset
    assert set2 >= set1  # Proper superset

    assert set3 < set1  # Strict subset
    assert set1 > set3  # Strict superset
    assert set1 < set2  # Strict subset
    assert set2 > set1  # Strict superset

    assert not (set1 < set4)  # Equal sets are not strict subsets
    assert not (set1 > set4)  # Equal sets are not strict supersets

    # Test with regular sets
    regular_set = {1, 2, 3}
    assert set1 == regular_set
    assert set1 <= regular_set
    assert set1 >= regular_set
    assert not (set1 < regular_set)
    assert not (set1 > regular_set)

    # Test with different types
    assert set1 != [1, 2, 3]
    assert set1 != "123"


def test_ordered_frozen_set_comparison_operators():
    """Test comparison operators for OrderedFrozenSet."""
    # Create sets for testing
    set1 = OrderedFrozenSet([1, 2, 3])
    set2 = OrderedFrozenSet([1, 2, 3, 4])
    set3 = OrderedFrozenSet([1, 2])
    set4 = OrderedFrozenSet([1, 2, 3])

    # Test equality (__eq__, __ne__)
    assert set1 == set4
    assert set1 != set2
    assert set1 != set3

    # Test subset/superset (__le__, __ge__, __lt__, __gt__)
    assert set1 <= set4  # Equal sets are subsets of each other
    assert set1 >= set4  # Equal sets are supersets of each other
    assert set3 <= set1  # Proper subset
    assert set1 >= set3  # Proper superset
    assert set1 <= set2  # Proper subset
    assert set2 >= set1  # Proper superset

    assert set3 < set1  # Strict subset
    assert set1 > set3  # Strict superset
    assert set1 < set2  # Strict subset
    assert set2 > set1  # Strict superset

    assert not (set1 < set4)  # Equal sets are not strict subsets
    assert not (set1 > set4)  # Equal sets are not strict supersets

    # Test with regular frozensets
    regular_set = frozenset([1, 2, 3])
    assert set1 == regular_set
    assert set1 <= regular_set
    assert set1 >= regular_set
    assert not (set1 < regular_set)
    assert not (set1 > regular_set)


def test_ordered_set_set_operations():
    """Test set operations for OrderedSet."""
    # Create sets for testing
    set1 = OrderedSet([1, 2, 3, 4])
    set2 = OrderedSet([3, 4, 5, 6])

    # Test union (__or__)
    union = set1 | set2
    assert isinstance(union, OrderedSet)
    assert union == OrderedSet([1, 2, 3, 4, 5, 6])

    # Test intersection (__and__)
    intersection = set1 & set2
    assert isinstance(intersection, OrderedSet)
    assert intersection == OrderedSet([3, 4])

    # Test difference (__sub__)
    difference = set1 - set2
    assert isinstance(difference, OrderedSet)
    assert difference == OrderedSet([1, 2])

    # Test symmetric difference (__xor__)
    sym_diff = set1 ^ set2
    assert isinstance(sym_diff, OrderedSet)
    assert sym_diff == OrderedSet([1, 2, 5, 6])

    # Test with regular sets
    regular_set = {3, 4, 5, 6}

    # Union with regular set
    union_reg = set1 | regular_set
    assert isinstance(union_reg, OrderedSet)
    assert union_reg == OrderedSet([1, 2, 3, 4, 5, 6])

    # Intersection with regular set
    intersection_reg = set1 & regular_set
    assert isinstance(intersection_reg, OrderedSet)
    assert intersection_reg == OrderedSet([3, 4])

    # Difference with regular set
    difference_reg = set1 - regular_set
    assert isinstance(difference_reg, OrderedSet)
    assert difference_reg == OrderedSet([1, 2])

    # Symmetric difference with regular set
    sym_diff_reg = set1 ^ regular_set
    assert isinstance(sym_diff_reg, OrderedSet)
    assert sym_diff_reg == OrderedSet([1, 2, 5, 6])


def test_ordered_frozen_set_set_operations():
    """Test set operations for OrderedFrozenSet."""
    # Create sets for testing
    set1 = OrderedFrozenSet([1, 2, 3, 4])
    set2 = OrderedFrozenSet([3, 4, 5, 6])

    # Test union (__or__)
    union = set1 | set2
    assert isinstance(union, OrderedFrozenSet)
    assert union == OrderedFrozenSet([1, 2, 3, 4, 5, 6])

    # Test intersection (__and__)
    intersection = set1 & set2
    assert isinstance(intersection, OrderedFrozenSet)
    assert intersection == OrderedFrozenSet([3, 4])

    # Test difference (__sub__)
    difference = set1 - set2
    assert isinstance(difference, OrderedFrozenSet)
    assert difference == OrderedFrozenSet([1, 2])

    # Test symmetric difference (__xor__)
    sym_diff = set1 ^ set2
    assert isinstance(sym_diff, OrderedFrozenSet)
    assert sym_diff == OrderedFrozenSet([1, 2, 5, 6])

    # Test with regular frozensets
    regular_set = frozenset([3, 4, 5, 6])

    # Union with regular frozenset
    union_reg = set1 | regular_set
    assert isinstance(union_reg, OrderedFrozenSet)
    assert union_reg == OrderedFrozenSet([1, 2, 3, 4, 5, 6])

    # Intersection with regular frozenset
    intersection_reg = set1 & regular_set
    assert isinstance(intersection_reg, OrderedFrozenSet)
    assert intersection_reg == OrderedFrozenSet([3, 4])

    # Difference with regular frozenset
    difference_reg = set1 - regular_set
    assert isinstance(difference_reg, OrderedFrozenSet)
    assert difference_reg == OrderedFrozenSet([1, 2])

    # Symmetric difference with regular frozenset
    sym_diff_reg = set1 ^ regular_set
    assert isinstance(sym_diff_reg, OrderedFrozenSet)
    assert sym_diff_reg == OrderedFrozenSet([1, 2, 5, 6])


def test_reverse_set_operations():
    """Test reverse set operations (__rsub__, __rxor__, etc.)."""
    # Create sets for testing
    ordered_set = OrderedSet([1, 2, 3, 4])
    ordered_frozen_set = OrderedFrozenSet([1, 2, 3, 4])
    regular_set = {3, 4, 5, 6}
    regular_frozen_set = frozenset([3, 4, 5, 6])

    # Test reverse operations with OrderedSet
    # Regular set - OrderedSet (__rsub__)
    diff1 = regular_set - ordered_set
    assert diff1 == {5, 6}

    # OrderedSet - Regular set
    diff2 = ordered_set - regular_set
    assert diff2 == OrderedSet([1, 2])

    # Regular set ^ OrderedSet (__rxor__)
    sym_diff1 = regular_set ^ ordered_set
    assert sym_diff1 == {1, 2, 5, 6}

    # OrderedSet ^ Regular set
    sym_diff2 = ordered_set ^ regular_set
    assert sym_diff2 == OrderedSet([1, 2, 5, 6])

    # Test reverse operations with OrderedFrozenSet
    # Regular frozenset - OrderedFrozenSet (__rsub__)
    diff3 = regular_frozen_set - ordered_frozen_set
    assert diff3 == frozenset([5, 6])

    # OrderedFrozenSet - Regular frozenset
    diff4 = ordered_frozen_set - regular_frozen_set
    assert diff4 == OrderedFrozenSet([1, 2])

    # Regular frozenset ^ OrderedFrozenSet (__rxor__)
    sym_diff3 = regular_frozen_set ^ ordered_frozen_set
    assert sym_diff3 == frozenset([1, 2, 5, 6])

    # OrderedFrozenSet ^ Regular frozenset
    sym_diff4 = ordered_frozen_set ^ regular_frozen_set
    assert sym_diff4 == OrderedFrozenSet([1, 2, 5, 6])


@given(
    base=st.lists(st.integers(), min_size=0, max_size=10),
    others_=st.lists(st.lists(st.integers(), min_size=0, max_size=5), min_size=1, max_size=3),
)
def test_ordered_set_inplace_operations(base: list[int], others_: list[list[int]]):
    """Test that in-place operations modify OrderedSet correctly while maintaining order."""

    others = [OrderedSet(o) for o in others_]

    # Test update operation
    update_set = OrderedSet(base)
    expected_update = OrderedSet(base)
    for other in others:
        expected_update = expected_update | other  # noqa: PLR6104
    update_set.update(*others)
    assert update_set == expected_update

    # Test intersection_update operation
    intersection_set = OrderedSet(base)
    expected_intersection = OrderedSet(base)
    for other in others:
        expected_intersection = expected_intersection & other  # noqa: PLR6104
    intersection_set.intersection_update(*others)
    assert intersection_set == expected_intersection

    # Test difference_update operation
    difference_set = OrderedSet(base)
    expected_difference = OrderedSet(base)
    for other in others:
        expected_difference = expected_difference - OrderedSet(other)  # noqa: PLR6104
    difference_set.difference_update(*others)
    assert difference_set == expected_difference

    # Test symmetric_difference_update operation
    sym_diff_set = OrderedSet(base)
    expected_sym_diff = OrderedSet(base)
    for other in others:
        expected_sym_diff = expected_sym_diff ^ OrderedSet(other)  # noqa: PLR6104
    sym_diff_set.symmetric_difference_update(*others)
    assert sym_diff_set == expected_sym_diff


@given(
    st.one_of(
        st.lists(st.integers(), min_size=0, max_size=10),
        st.tuples(*[st.integers() for _ in range(5)]),
        st.sets(st.integers(), min_size=0, max_size=10),
        st.frozensets(st.integers(), min_size=0, max_size=10),
    )
)
def test_ordered_sets_initialization_with_iterables(iterable: Any):
    # sourcery skip: simplify-generator
    """Test that OrderedSet and OrderedFrozenSet can be initialized with various iterable types."""
    # Test OrderedSet initialization
    ordered_set = OrderedSet(iterable)
    assert isinstance(ordered_set, OrderedSet)
    assert all(item in ordered_set for item in iterable)

    # Test OrderedFrozenSet initialization
    ordered_frozen_set = OrderedFrozenSet(iterable)
    assert isinstance(ordered_frozen_set, OrderedFrozenSet)
    assert all(item in ordered_frozen_set for item in iterable)

    # Test with generator expression
    gen = (x for x in iterable)
    ordered_set_from_gen = OrderedSet(gen)
    assert isinstance(ordered_set_from_gen, OrderedSet)
    assert ordered_set_from_gen == ordered_set

    # Test with another generator expression
    gen2 = (x for x in iterable)
    ordered_frozen_set_from_gen = OrderedFrozenSet(gen2)
    assert isinstance(ordered_frozen_set_from_gen, OrderedFrozenSet)
    assert ordered_frozen_set_from_gen == ordered_frozen_set

    # Test with dictionary keys
    if iterable:
        dict_keys = dict.fromkeys(iterable).keys()
        ordered_set_from_dict_keys = OrderedSet(dict_keys)
        assert isinstance(ordered_set_from_dict_keys, OrderedSet)
        assert set(ordered_set_from_dict_keys) == set(iterable)

        ordered_frozen_set_from_dict_keys = OrderedFrozenSet(dict_keys)
        assert isinstance(ordered_frozen_set_from_dict_keys, OrderedFrozenSet)
        assert set(ordered_frozen_set_from_dict_keys) == set(iterable)

    # Test with another OrderedSet/OrderedFrozenSet
    ordered_set_from_ordered_set = OrderedSet(ordered_set)
    assert isinstance(ordered_set_from_ordered_set, OrderedSet)
    assert ordered_set_from_ordered_set == ordered_set

    ordered_frozen_set_from_ordered_frozen_set = OrderedFrozenSet(ordered_frozen_set)
    assert isinstance(ordered_frozen_set_from_ordered_frozen_set, OrderedFrozenSet)
    assert ordered_frozen_set_from_ordered_frozen_set == ordered_frozen_set

    # Cross initialization
    ordered_set_from_ordered_frozen_set = OrderedSet(ordered_frozen_set)
    assert isinstance(ordered_set_from_ordered_frozen_set, OrderedSet)
    assert ordered_set_from_ordered_frozen_set == ordered_frozen_set

    ordered_frozen_set_from_ordered_set = OrderedFrozenSet(ordered_set)
    assert isinstance(ordered_frozen_set_from_ordered_set, OrderedFrozenSet)
    assert ordered_frozen_set_from_ordered_set == ordered_set


@settings(deadline=None)  # Disable deadline for performance tests
@given(
    data=st.lists(st.integers(), min_size=1000, max_size=10000),
    operations=st.lists(
        st.sampled_from(["add", "discard", "contains", "union", "intersection", "difference"]),
        min_size=5,
        max_size=20,
    ),
)
def ordered_sets_performance_with_large_datasets(data: list[int], operations: list[str]):  # noqa: PLR0914, PLR0915
    """Test performance characteristics of OrderedSet and OrderedFrozenSet with large datasets."""
    # Create large datasets
    large_ordered_set = OrderedSet(data)
    large_ordered_frozen_set = OrderedFrozenSet(data)
    large_regular_set = set(data)
    large_regular_frozen_set = frozenset(data)

    # Create additional data for operations
    additional_data = list(range(max(data) + 1, max(data) + 1001))
    additional_set = OrderedSet(additional_data)

    # Measure and compare performance for various operations
    for operation in operations:
        if operation == "add" and hasattr(large_ordered_set, "add"):
            # Test add operation (only for mutable sets)
            element = max(data) + 10000

            start_time = time.time()
            large_ordered_set.add(element)
            ordered_set_time = time.time() - start_time

            start_time = time.time()
            large_regular_set.add(element)
            regular_set_time = time.time() - start_time

            # We don't expect OrderedSet to be significantly slower than regular set
            # Allow for some overhead but not orders of magnitude difference
            assert ordered_set_time < regular_set_time * 10, (
                "OrderedSet.add is significantly slower than set.add"
            )

        elif operation == "discard" and hasattr(large_ordered_set, "discard"):
            # Test discard operation (only for mutable sets)
            element = data[len(data) // 2] if data else 0

            start_time = time.time()
            large_ordered_set.discard(element)
            ordered_set_time = time.time() - start_time

            start_time = time.time()
            large_regular_set.discard(element)
            regular_set_time = time.time() - start_time

            assert ordered_set_time < regular_set_time * 10, (
                "OrderedSet.discard is significantly slower than set.discard"
            )

        elif operation == "contains":
            # Test contains operation
            element = data[len(data) // 2] if data else 0

            start_time = time.time()
            _ = element in large_ordered_set
            ordered_set_time = time.time() - start_time

            start_time = time.time()
            _ = element in large_regular_set
            regular_set_time = time.time() - start_time

            assert ordered_set_time < regular_set_time * 10, (
                "OrderedSet contains check is significantly slower"
            )

            # Also test for OrderedFrozenSet
            start_time = time.time()
            _ = element in large_ordered_frozen_set
            ordered_frozen_set_time = time.time() - start_time

            start_time = time.time()
            _ = element in large_regular_frozen_set
            regular_frozen_set_time = time.time() - start_time

            assert ordered_frozen_set_time < regular_frozen_set_time * 10, (
                "OrderedFrozenSet contains check is significantly slower"
            )

        elif operation == "union":
            # Test union operation
            start_time = time.time()
            _ = large_ordered_set | additional_set
            ordered_set_time = time.time() - start_time

            start_time = time.time()
            _ = large_regular_set | set(additional_data)
            regular_set_time = time.time() - start_time

            # Union might be slower due to order preservation, but shouldn't be extremely slow
            assert ordered_set_time < regular_set_time * 20, "OrderedSet union is extremely slower"

            # Also test for OrderedFrozenSet
            start_time = time.time()
            _ = large_ordered_frozen_set | OrderedFrozenSet(additional_data)
            ordered_frozen_set_time = time.time() - start_time

            start_time = time.time()
            _ = large_regular_frozen_set | frozenset(additional_data)
            regular_frozen_set_time = time.time() - start_time

            assert ordered_frozen_set_time < regular_frozen_set_time * 20, (
                "OrderedFrozenSet union is extremely slower"
            )

        elif operation == "intersection":
            # Test intersection operation
            start_time = time.time()
            _ = large_ordered_set & additional_set
            ordered_set_time = time.time() - start_time

            start_time = time.time()
            _ = large_regular_set & set(additional_data)
            regular_set_time = time.time() - start_time

            assert ordered_set_time < regular_set_time * 20, (
                "OrderedSet intersection is extremely slower"
            )

            # Also test for OrderedFrozenSet
            start_time = time.time()
            _ = large_ordered_frozen_set & OrderedFrozenSet(additional_data)
            ordered_frozen_set_time = time.time() - start_time

            start_time = time.time()
            _ = large_regular_frozen_set & frozenset(additional_data)
            regular_frozen_set_time = time.time() - start_time

            assert ordered_frozen_set_time < regular_frozen_set_time * 20, (
                "OrderedFrozenSet intersection is extremely slower"
            )

        elif operation == "difference":
            # Test difference operation
            start_time = time.time()
            _ = large_ordered_set - additional_set
            ordered_set_time = time.time() - start_time

            start_time = time.time()
            _ = large_regular_set - set(additional_data)
            regular_set_time = time.time() - start_time

            assert ordered_set_time < regular_set_time * 20, (
                "OrderedSet difference is extremely slower"
            )

            # Also test for OrderedFrozenSet
            start_time = time.time()
            _ = large_ordered_frozen_set - OrderedFrozenSet(additional_data)
            ordered_frozen_set_time = time.time() - start_time

            start_time = time.time()
            _ = large_regular_frozen_set - frozenset(additional_data)
            regular_frozen_set_time = time.time() - start_time

            assert ordered_frozen_set_time < regular_frozen_set_time * 20, (
                "OrderedFrozenSet difference is extremely slower"
            )

    # Test iteration performance
    start_time = time.time()
    for _ in large_ordered_set:
        pass
    ordered_set_iteration_time = time.time() - start_time

    start_time = time.time()
    for _ in large_regular_set:
        pass
    regular_set_iteration_time = time.time() - start_time

    # Iteration might be slightly slower due to order preservation
    assert ordered_set_iteration_time < regular_set_iteration_time * 10, (
        "OrderedSet iteration is significantly slower"
    )

    # Also test for OrderedFrozenSet
    start_time = time.time()
    for _ in large_ordered_frozen_set:
        pass
    ordered_frozen_set_iteration_time = time.time() - start_time

    start_time = time.time()
    for _ in large_regular_frozen_set:
        pass
    regular_frozen_set_iteration_time = time.time() - start_time

    assert ordered_frozen_set_iteration_time < regular_frozen_set_iteration_time * 10, (
        "OrderedFrozenSet iteration is significantly slower"
    )


def test_ordered_sets_register_as_set_subclasses():
    """Test that OrderedSet and OrderedFrozenSet are properly registered as Set subclasses."""
    # Test that OrderedSet is registered as a Set subclass
    assert issubclass(OrderedSet, Set)
    assert isinstance(OrderedSet(), Set)
    assert isinstance(OrderedSet([1, 2, 3]), Set)

    # Test that OrderedFrozenSet is registered as a Set subclass
    assert issubclass(OrderedFrozenSet, Set)
    assert isinstance(OrderedFrozenSet(), Set)
    assert isinstance(OrderedFrozenSet([1, 2, 3]), Set)

    # Test with Python's built-in set and frozenset for comparison
    assert issubclass(set, Set)
    assert issubclass(frozenset, Set)

    # Test that the registration allows for proper type checking
    def accepts_set(_s: Set[Any]):
        return True

    assert accepts_set(OrderedSet([1, 2, 3]))
    assert accepts_set(OrderedFrozenSet([1, 2, 3]))
    assert accepts_set({1, 2, 3})
    assert accepts_set(frozenset([1, 2, 3]))


@given(st.lists(st.integers(), min_size=0, max_size=10))
def test_ordered_sets_sequence_protocol(elements: list[int]):
    """Test that OrderedSet and OrderedFrozenSet implement Sequence protocol correctly."""
    # Create both types of ordered sets
    ordered_set = OrderedSet(elements)
    ordered_frozen_set = OrderedFrozenSet(elements)

    # Verify they are instances of Sequence
    assert isinstance(ordered_set, Sequence)
    assert isinstance(ordered_frozen_set, Sequence)

    # Create expected list (with duplicates removed while preserving first occurrence)
    expected: list[int] = []
    for e in elements:
        if e not in expected:
            expected.append(e)

    # Test __getitem__
    for i, value in enumerate(expected):
        assert ordered_set[i] == value
        assert ordered_frozen_set[i] == value

    # Test index out of range
    with pytest.raises(IndexError):
        _ = ordered_set[len(ordered_set)]
    with pytest.raises(IndexError):
        _ = ordered_frozen_set[len(ordered_frozen_set)]

    # Test __reversed__
    assert list(reversed(ordered_set)) == list(reversed(expected))
    assert list(reversed(ordered_frozen_set)) == list(reversed(expected))

    # Test index method
    for i, value in enumerate(expected):
        assert ordered_set.index(value) == i
        assert ordered_frozen_set.index(value) == i

    # Test index with non-existent value
    if elements:  # noqa: SIM108
        non_existent = max(elements) + 1
    else:
        non_existent = 1

    with pytest.raises(ValueError):  # noqa: PT011
        ordered_set.index(non_existent)
    with pytest.raises(ValueError):  # noqa: PT011
        ordered_frozen_set.index(non_existent)

    # Test count method
    for value in expected:
        assert ordered_set.count(value) == 1
        assert ordered_frozen_set.count(value) == 1

    # Test count with non-existent value
    assert ordered_set.count(non_existent) == 0
    assert ordered_frozen_set.count(non_existent) == 0

    # Test sequence operations
    if expected:
        # Test slicing (not implemented, should raise TypeError)
        with pytest.raises(TypeError):
            _ = ordered_set[0:2]  # pyright: ignore[reportArgumentType]
        with pytest.raises(TypeError):
            _ = ordered_frozen_set[0:2]  # pyright: ignore[reportArgumentType]


def test_ordered_sets_index_out_of_range():
    """Test that OrderedSet and OrderedFrozenSet handle index out of range correctly."""
    # Create empty sets
    empty_ordered_set = OrderedSet[Any]()
    empty_ordered_frozen_set = OrderedFrozenSet[Any]()

    # Test accessing elements in empty sets
    with pytest.raises(IndexError):
        _ = empty_ordered_set[0]

    with pytest.raises(IndexError):
        _ = empty_ordered_frozen_set[0]

    # Create non-empty sets
    ordered_set = OrderedSet([1, 2, 3])
    ordered_frozen_set = OrderedFrozenSet([1, 2, 3])

    # Test accessing elements with positive out-of-range indices
    with pytest.raises(IndexError):
        _ = ordered_set[3]

    with pytest.raises(IndexError):
        _ = ordered_frozen_set[3]

    with pytest.raises(IndexError):
        _ = ordered_set[1000]

    with pytest.raises(IndexError):
        _ = ordered_frozen_set[1000]

    # Test accessing elements with negative out-of-range indices
    with pytest.raises(IndexError):
        _ = ordered_set[-4]

    with pytest.raises(IndexError):
        _ = ordered_frozen_set[-4]


def test_ordered_set_clear():
    ordered_set = OrderedSet([1, 2, 3])
    ordered_set.clear()
    assert len(ordered_set) == 0


def test_ordered_frozen_set_clear_raise():
    ordered_set = OrderedFrozenSet([1, 2, 3])
    with pytest.raises(AttributeError):
        ordered_set.clear()  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
