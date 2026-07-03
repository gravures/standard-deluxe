from __future__ import annotations

import pytest
from deluxe.mappings import FrozenMap
from hypothesis import given
from hypothesis import strategies as st


# Strategy for generating dictionaries to be used as source for FrozenMap
# Using simple, hashable types for keys and values.
source_dicts_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50) | st.integers(),
    values=st.integers() | st.text() | st.booleans() | st.none(),
)

Tested = dict[str | int, int | str | bool | None]


@given(st.dictionaries(keys=st.text(min_size=1, max_size=10), values=st.integers()))
def test_source_handling(source_dict: dict[str, int]):
    """
    Property: A FrozenMap initialized from a dictionary has the same
    length as the source dictionary.
    """
    frozen_map = FrozenMap(source_dict)
    frozen_map_kwds = FrozenMap(**source_dict)
    assert frozen_map._source is source_dict  # pyright: ignore[reportPrivateUsage]
    assert frozen_map_kwds._source == source_dict  # pyright: ignore[reportPrivateUsage]


@given(source_dict=source_dicts_strategy)
def test_initialization_and_length(source_dict: Tested):
    """
    Property: A FrozenMap initialized from a dictionary has the same
    length as the source dictionary.
    """
    frozen_map = FrozenMap(source_dict)
    assert len(frozen_map) == len(source_dict)


@given(source_dict=source_dicts_strategy)
def test_behaves_like_readonly_mapping(source_dict: Tested):
    """
    Property: A FrozenMap should behave identically to a read-only
    dictionary for all fundamental read operations.
    """
    frozen_map = FrozenMap(source_dict)

    # __iter__
    assert list(frozen_map) == list(source_dict)

    # __contains__, __getitem__
    for key in source_dict:
        assert key in frozen_map
        assert frozen_map[key] == source_dict[key]

    # keys(), values(), items()
    assert set(frozen_map.keys()) == set(source_dict.keys())
    # Note: list comparison for values might fail if order is not guaranteed
    # or if values are unhashable. For this strategy, it's okay.
    assert sorted(map(str, frozen_map.values())) == sorted(map(str, source_dict.values()))
    assert set(frozen_map.items()) == set(source_dict.items())


@given(source_dict=source_dicts_strategy, missing_key=st.text(min_size=1))
def test_getitem_raises_keyerror(source_dict: Tested, missing_key: str):
    """
    Property: Accessing a non-existent key raises a KeyError, just
    like a regular dictionary.
    """
    # Ensure the key is actually missing
    if missing_key in source_dict:
        del source_dict[missing_key]

    frozen_map = FrozenMap(source_dict)
    with pytest.raises(KeyError):
        _ = frozen_map[missing_key]


@given(source_dict=source_dicts_strategy, data=st.data())
def test_get_method(source_dict: Tested, data: st.DataObject):
    """
    Property: The `get()` method should return the value for a key if it
    exists, or the default value otherwise.
    """
    frozen_map = FrozenMap(source_dict)
    default_value = "default"

    if source_dict:
        # Test with an existing key
        existing_key = data.draw(st.sampled_from(list(source_dict.keys())))
        assert frozen_map.get(existing_key, default_value) == source_dict[existing_key]

    # Test with a non-existent key
    missing_key = data.draw(st.text(min_size=1).filter(lambda k: k not in source_dict))
    assert frozen_map.get(missing_key) is None
    assert frozen_map.get(missing_key, default_value) == default_value


@given(d1=source_dicts_strategy, d2=source_dicts_strategy)
def test_equality(d1: Tested, d2: Tested):
    """
    Property: Two FrozenMaps are equal if and only if their underlying
    source dictionaries are equal. A FrozenMap is also equal to its
    source dictionary.
    """
    fm1 = FrozenMap(d1)
    fm2 = FrozenMap(d2)

    # Equality between FrozenMaps
    assert (fm1 == fm2) == (d1 == d2)
    assert (fm1 != fm2) == (d1 != d2)

    # Equality with other mapping types
    assert fm1 == d1
    assert d1 == fm1
    assert (fm1 == d2) == (d1 == d2)


def test_immutability():
    """
    Property: A FrozenMap cannot be modified after creation.
    """
    frozen_map = FrozenMap({"a": 1, "b": 2})

    # __setitem__
    with pytest.raises(TypeError):
        frozen_map["c"] = 3  # pyright: ignore[reportIndexIssue]

    # __delitem__
    with pytest.raises(TypeError):
        del frozen_map["a"]  # pyright: ignore[reportIndexIssue]

    # No update, pop, etc. methods
    assert not hasattr(frozen_map, "update")
    assert not hasattr(frozen_map, "pop")
    assert not hasattr(frozen_map, "popitem")
    assert not hasattr(frozen_map, "clear")
    assert not hasattr(frozen_map, "setdefault")

    # __slots__ prevents adding new attributes
    with pytest.raises(AttributeError):
        frozen_map.new_attr = "test"  # pyright: ignore[reportAttributeAccessIssue]


@given(source_dict=source_dicts_strategy)
def test_repr_is_correct(source_dict: Tested):
    """
    Property: The `repr()` of a FrozenMap should be a valid string
    representation that can be evaluated.
    """
    frozen_map = FrozenMap(source_dict)
    repr_str = repr(frozen_map)

    # Basic check for format
    assert repr_str.startswith("FrozenMap({")
    assert repr_str.endswith("})")
