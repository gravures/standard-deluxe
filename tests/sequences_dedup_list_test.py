"""Tests for the `dedup_list` function."""

from __future__ import annotations

from deluxe.sequences import dedup_list
from hypothesis import given
from hypothesis import strategies as st


# Strategy for generating lists of primitive, hashable types.
# Using integers as they are simple and effective for testing logic.
list_strategy = st.lists(st.integers() | st.text())


@given(input_list=list_strategy)
def test_uniqueness(input_list: list[int | str]):
    """
    Property: The output list must contain no duplicate elements.
    """
    result_fifo = dedup_list(input_list, lifo=False)
    assert len(result_fifo) == len(set(result_fifo))

    result_lifo = dedup_list(input_list, lifo=True)
    assert len(result_lifo) == len(set(result_lifo))


@given(input_list=list_strategy)
def test_completeness(input_list: list[int | str]):
    """
    Property: The set of elements in the output is identical to the set of
    elements in the input.
    """
    result = dedup_list(input_list)
    assert set(result) == set(input_list)


@given(input_list=list_strategy)
def test_length_invariant(input_list: list[int | str]):
    """
    Property: The length of the output list is always less than or equal to
    the length of the input list.
    """
    result = dedup_list(input_list)
    assert len(result) <= len(input_list)


@given(input_list=list_strategy)
def test_idempotence(input_list: list[int | str]):
    """
    Property: Applying dedup_list again to its output does not change the result.
    """
    result_fifo = dedup_list(input_list, lifo=False)
    assert dedup_list(result_fifo, lifo=False) == result_fifo

    result_lifo = dedup_list(input_list, lifo=True)
    assert dedup_list(result_lifo, lifo=True) == result_lifo


@given(input_list=list_strategy)
def test_fifo_order_preservation(input_list: list[int | str]):
    """
    Property: With lifo=False, the first occurrence of each element is kept,
    and their relative order is preserved.
    """
    result = dedup_list(input_list, lifo=False)

    # Manually compute the expected FIFO result
    seen = set[int | str]()
    expected: list[int | str] = []
    for item in input_list:
        if item not in seen:
            seen.add(item)
            expected.append(item)

    assert result == expected


@given(input_list=list_strategy)
def test_lifo_order_preservation(input_list: list[int | str]):
    """
    Property: With lifo=True, the last occurrence of each element is kept,
    and their relative order is preserved.
    """
    result = dedup_list(input_list, lifo=True)

    # Manually compute the expected LIFO result
    seen = set[str | int]()
    expected: list[int | str] = []
    for item in reversed(input_list):
        if item not in seen:
            seen.add(item)
            expected.append(item)
    expected.reverse()  # The list was built backwards, so reverse it.

    assert result == expected


def test_empty_list_input():
    """
    Property: An empty iterable input should result in an empty list.
    """
    assert dedup_list([]) == []
    assert dedup_list([], lifo=True) == []
