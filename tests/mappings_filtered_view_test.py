# ruff: noqa: ARG005
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from copy import copy, deepcopy

import pytest
from deluxe.mappings import FilteredView, FrozenMap, OrderableDict
from hypothesis import given
from hypothesis import strategies as st


# Strategy for source dictionaries. We test with both regular dicts and OrderableDicts.
source_dicts_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.integers() | st.text(min_size=1),
).flatmap(lambda d: st.sampled_from([d, OrderableDict[str, int | str](d)]))

Tested = MutableMapping[str, int | str]
Filter = Callable[[str, int | str], bool]
FilterIn = tuple[str, Filter]

# A collection of simple, pure filter functions to be sampled.
# These cover common filtering scenarios.
filters: list[FilterIn] = [
    ("Always True", lambda k, v: True),
    ("Always False", lambda k, v: False),
    ("Value is Integer", lambda k, v: isinstance(v, int)),
    ("Value is String", lambda k, v: isinstance(v, str)),
    ("Key has length > 5", lambda k, v: len(k) > 5),
    ("Value is > 50", lambda k, v: isinstance(v, int) and v > 50),
]
filters_strategy = st.sampled_from(filters)


@given(source_dict=source_dicts_strategy, filter_tuple=filters_strategy)
def test_length_is_correct(source_dict: Tested, filter_tuple: FilterIn):
    _, filter_func = filter_tuple
    view = FilteredView(source_dict, filter_func)
    expected_len = sum(1 for k, v in source_dict.items() if filter_func(k, v))
    assert len(view) == expected_len


@given(source_dict=source_dicts_strategy, filter_tuple=filters_strategy)
def test_iteration_yields_filtered_keys(source_dict: Tested, filter_tuple: FilterIn):
    _, filter_func = filter_tuple
    view = FilteredView(source_dict, filter_func)
    expected_keys = [k for k, v in source_dict.items() if filter_func(k, v)]
    assert list(view) == expected_keys


@given(source_dict=source_dicts_strategy, filter_tuple=filters_strategy, data=st.data())
def test_contains_respects_filter(
    source_dict: Tested, filter_tuple: FilterIn, data: st.DataObject
):
    if not source_dict:
        return  # Skip empty dicts for this test

    _, filter_func = filter_tuple
    view = FilteredView(source_dict, filter_func)
    key_to_test = data.draw(st.sampled_from(list(source_dict.keys())))

    value = source_dict[key_to_test]
    expected_in = filter_func(key_to_test, value)
    assert (key_to_test in view) == expected_in


@given(source_dict=source_dicts_strategy, filter_tuple=filters_strategy, data=st.data())
def test_getitem_respects_filter(source_dict: Tested, filter_tuple: FilterIn, data: st.DataObject):
    if not source_dict:
        return

    _, filter_func = filter_tuple
    view = FilteredView(source_dict, filter_func)
    key = data.draw(st.sampled_from(list(source_dict.keys())))

    if filter_func(key, source_dict[key]):
        assert view[key] == source_dict[key]
    else:
        with pytest.raises(KeyError):
            _ = view[key]


@given(source_dict=source_dicts_strategy, filter_tuple=filters_strategy, data=st.data())
def test_get_method_respects_filter(
    source_dict: Tested, filter_tuple: FilterIn, data: st.DataObject
):
    if not source_dict:
        return

    _, filter_func = filter_tuple
    view = FilteredView(source_dict, filter_func)
    key = data.draw(st.sampled_from(list(source_dict.keys())))
    default_val = "DEFAULT"

    if filter_func(key, source_dict[key]):
        assert view.get(key, default_val) == source_dict[key]
    else:
        assert view.get(key, default_val) == default_val


@given(
    source_dict=st.dictionaries(st.text(min_size=1), st.integers()),
    new_key=st.text(min_size=1, max_size=5),
    new_value=st.integers(min_value=100),
)
def test_view_reflects_source_changes(source_dict: Tested, new_key: str, new_value: int):
    # Use a simple filter for predictability
    filter_func: Callable[[str, int], bool] = lambda k, v: v > 50  # noqa: E731
    view = FilteredView(source_dict, filter_func)

    # 1. Add a new item that passes the filter
    source_dict[new_key] = new_value  # new_value is > 50
    assert new_key in view
    assert view[new_key] == new_value

    # 2. Modify an item so it no longer passes
    source_dict[new_key] = 10  # 10 is not > 50
    assert new_key not in view

    # 3. Modify an item so it passes again
    source_dict[new_key] = 150
    assert new_key in view

    # 4. Delete the item
    del source_dict[new_key]
    assert new_key not in view


@given(source_dict=source_dicts_strategy, filter_tuple=filters_strategy)
def test_copy_is_independent_and_correct(source_dict: Tested, filter_tuple: FilterIn):
    _, filter_func = filter_tuple
    view = FilteredView(source_dict, filter_func)
    # Create the expected dictionary manually
    expected_dict = {k: v for k, v in source_dict.items() if filter_func(k, v)}
    copied_map = copy(view)

    # Check type and content
    assert isinstance(copied_map, type(source_dict))
    assert copied_map == expected_dict

    # Check for independence
    if source_dict and isinstance(source_dict, dict):
        key_to_add = "a_new_key_for_testing"
        source_dict[key_to_add] = "a_new_value"
        # The copy should not change
        assert key_to_add not in copied_map
        assert copied_map == expected_dict


def test_deep_copy():
    source_dict = {"a": 0, "b": 1}
    mutable = list(source_dict.keys())
    source_dict["mutable"] = mutable  # pyright: ignore[reportArgumentType]
    view = FilteredView(source_dict)
    copied_map = deepcopy(view)
    assert copied_map["mutable"] == mutable
    assert copied_map is not mutable


def test_copy_on_filtered_frozen():
    source_dict = FrozenMap({"a": 0, "b": 1, "c": 2})
    view = FilteredView(source_dict)
    copied_map = copy(view)
    assert type(copied_map) is FrozenMap
