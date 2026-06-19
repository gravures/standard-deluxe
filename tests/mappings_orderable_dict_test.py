from __future__ import annotations

import copy
from typing import assert_type

import pytest
from deluxe.mappings import OrderableDict
from hypothesis import assume, given
from hypothesis import strategies as st


# Strategy for dictionary keys (using text for simplicity and readability)
keys_strategy = st.text(min_size=1, max_size=20)

# Strategy for dictionary values
values_strategy = st.integers() | st.text()

# Strategy for creating OrderableDict instances
# We need at least 2 items for most reordering tests.
orderable_dicts_strategy = st.dictionaries(
    keys=keys_strategy, values=values_strategy, min_size=2
).map(OrderableDict[str, int | str])

Tested = OrderableDict[str, int | str]


def test_annotations():
    # This test nothing at runtime
    d = {"a": 1}
    o = OrderableDict(d)
    assert_type(o, OrderableDict[str, int])


@given(d=orderable_dicts_strategy)
def test_first_and_last_getters(d: Tested):
    """
    Property: The `first` and `last` properties should return the first and
    last keys of the underlying ordered dictionary, respectively.
    """
    key_list = list(d.keys())
    assert d.first == key_list[0]
    assert d.last == key_list[-1]


def test_first_and_last_on_empty_dict():
    """
    Property: Accessing `first` or `last` on an empty OrderableDict
    should raise an exception.
    """
    d: Tested = OrderableDict()
    with pytest.raises(AttributeError):
        _ = d.first
    with pytest.raises(AttributeError):
        _ = d.last


@given(d=orderable_dicts_strategy)
def test_after_get_mode(d: Tested):
    """
    Property: Calling `after(key)` should return the next (key, value)
    pair in the sequence.
    """
    key_list = list(d.keys())
    # Iterate up to the second-to-last key
    for i in range(len(key_list) - 1):
        current_key = key_list[i]
        next_key = key_list[i + 1]
        next_value = d[next_key]
        assert d.after(current_key) == (next_key, next_value)


@given(d=orderable_dicts_strategy)
def test_before_get_mode(d: Tested):
    """
    Property: Calling `before(key)` should return the previous (key, value)
    pair in the sequence.
    """
    key_list = list(d.keys())
    # Iterate from the second key to the end
    for i in range(1, len(key_list)):
        current_key = key_list[i]
        prev_key = key_list[i - 1]
        prev_value = d[prev_key]
        assert d.before(current_key) == (prev_key, prev_value)


@given(d=orderable_dicts_strategy, data=st.data())
def test_after_move_mode(d: Tested, data: st.DataObject):
    """
    Property: Moving a key `k1` after key `k2` should place `k1`
    immediately after `k2` in the key order.
    """
    original_keys = set(d.keys())
    original_len = len(d)
    key_to_move = data.draw(st.sampled_from(list(d.keys())))
    target_key = data.draw(st.sampled_from(list(d.keys())))

    # Ensure we are actually moving the key to a new position
    assume(key_to_move != target_key)

    d.after(key=key_to_move, other=target_key)

    assert len(d) == original_len
    assert set(d.keys()) == original_keys

    key_list = list(d.keys())
    target_index = key_list.index(target_key)

    # The moved key should be right after the target key
    assert key_list[target_index + 1] == key_to_move


@given(d=orderable_dicts_strategy, data=st.data())
def test_before_move_mode(d: Tested, data: st.DataObject):
    """
    Property: Moving a key `k1` before key `k2` should place `k1`
    immediately before `k2` in the key order.
    """
    original_keys = set(d.keys())
    original_len = len(d)
    key_to_move = data.draw(st.sampled_from(list(d.keys())))
    target_key = data.draw(st.sampled_from(list(d.keys())))

    # Ensure we are actually moving the key to a new position
    assume(key_to_move != target_key)

    d.before(key=key_to_move, other=target_key)

    assert len(d) == original_len
    assert set(d.keys()) == original_keys

    key_list = list(d.keys())
    target_index = key_list.index(target_key)

    # The moved key should be right before the target key
    assert key_list[target_index - 1] == key_to_move


@given(
    d=orderable_dicts_strategy, data=st.data(), new_key=keys_strategy, new_value=values_strategy
)
def test_after_insert_new_key(d: Tested, data: st.DataObject, new_key: str, new_value: str | int):
    """
    Property: Inserting a new key after an existing key should place it
    correctly and increase the dictionary size by one.
    """
    assume(new_key not in d)
    original_len = len(d)
    target_key = data.draw(st.sampled_from(list(d.keys())))

    d.after(key=new_key, other=target_key, value=new_value)

    assert len(d) == original_len + 1
    assert new_key in d
    assert d[new_key] == new_value

    key_list = list(d.keys())
    target_index = key_list.index(target_key)
    assert key_list[target_index + 1] == new_key


@given(
    d=orderable_dicts_strategy, data=st.data(), new_key=keys_strategy, new_value=values_strategy
)
def test_before_insert_new_key(d: Tested, data: st.DataObject, new_key: str, new_value: int | str):
    """
    Property: Inserting a new key before an existing key should place it
    correctly and increase the dictionary size by one.
    """
    assume(new_key not in d)
    original_len = len(d)
    target_key = data.draw(st.sampled_from(list(d.keys())))

    d.before(key=new_key, other=target_key, value=new_value)

    assert len(d) == original_len + 1
    assert new_key in d
    assert d[new_key] == new_value

    key_list = list(d.keys())
    target_index = key_list.index(target_key)
    assert key_list[target_index - 1] == new_key


@given(d=orderable_dicts_strategy, data=st.data(), new_value=values_strategy)
def test_insert_existing_key_updates_value_and_preserves_order(
    d: Tested, data: st.DataObject, new_value: int | str
):
    """
    Property: Attempting to "insert" an existing key should only update
    its value, not change its position in the order.
    """
    original_len = len(d)
    original_order = list(d.keys())
    key_to_update = data.draw(st.sampled_from(list(d.keys())))
    target_key = data.draw(st.sampled_from(list(d.keys())))

    # Test with both `after` and `before`
    d_after = d.copy()
    d_after.after(key=key_to_update, other=target_key, value=new_value)

    assert len(d_after) == original_len
    assert d_after[key_to_update] == new_value
    assert list(d_after.keys()) == original_order

    d_before = d.copy()
    d_before.before(key=key_to_update, other=target_key, value=new_value)

    assert len(d_before) == original_len
    assert d_before[key_to_update] == new_value
    assert list(d_before.keys()) == original_order


@given(d=orderable_dicts_strategy, key=keys_strategy)
def test_raises_key_error_for_nonexistent_keys(d: Tested, key: str):
    """
    Property: All methods should raise KeyError when given a key that
    does not exist in the dictionary where required.
    """
    assume(key not in d)
    existing_key = d.first

    # Get mode
    with pytest.raises(KeyError):
        d.after(key)
    with pytest.raises(KeyError):
        d.before(key)

    # Move mode
    with pytest.raises(KeyError):
        d.after(key=key, other=existing_key)
    with pytest.raises(KeyError):
        d.after(key=existing_key, other=key)
    with pytest.raises(KeyError):
        d.before(key=key, other=existing_key)
    with pytest.raises(KeyError):
        d.before(key=existing_key, other=key)

    # Insert mode (only `other` is checked for existence)
    with pytest.raises(KeyError):
        d.after(key="new_key", other=key, value="new_value")
    with pytest.raises(KeyError):
        d.before(key="new_key", other=key, value="new_value")


@given(d=orderable_dicts_strategy)
def test_copy(d: Tested):
    """Verify that a copied instance is equal to the original."""
    d_copy = copy.copy(d)
    assert d == d_copy
