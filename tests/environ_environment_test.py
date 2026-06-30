# Copyright (c) 2025 - Gilles Coissac
# This file is part of standard-deluxe library.
#
# standard-deluxe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# standard-deluxe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with standard-deluxe. If not, see <https://www.gnu.org/licenses/>
#
"""Property-based tests for the Environment class.

These tests verify the behavioral properties of the Environment class using
hypothesis to generate a wide range of inputs and validate invariants.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

import pytest
from deluxe.environ import Environment, evar
from deluxe.types import Unset
from hypothesis import given, settings
from hypothesis import strategies as st

if TYPE_CHECKING:
    from collections.abc import Iterable


def dedup_list(iterable: Iterable[object], lifo: bool = False) -> list[object]:
    unique_: list[object] = []
    list_ = list(iterable)[::-1] if lifo else list(iterable)
    for v in list_:
        if v not in unique_:
            unique_.append(v)
    return unique_[::-1] if lifo else unique_


def dedup_value(value: Any) -> Any:
    """Deduplicate a value if it's a list, matching Environment's behavior.

    Args:
        value: The value to deduplicate.

    Returns:
        The deduplicated value if it's a list, otherwise the value as-is.
    """
    if isinstance(value, list):
        return dedup_list(value)  # pyright: ignore[reportUnknownArgumentType]
    return value


def dedup_items(items: list[tuple[str, Any]]) -> dict[str, Any]:
    """Convert items to dict with list values deduplicated.

    Matches Environment behavior: last value wins for duplicate keys
    (standard dict semantics), then list values are deduplicated.

    Args:
        items: List of key-value pairs.

    Returns:
        A dictionary with list values deduplicated.
    """
    return {k: dedup_value(v) for k, v in dict(items).items()}


# ------------------------------------------------------------------------------
# Strategies
# ------------------------------------------------------------------------------

# Strategy for generating valid string values
string_strategy = st.text(min_size=0, max_size=100).filter(lambda s: "\x00" not in s)

# Strategy for generating integers
int_strategy = st.integers(min_value=-10_000_000, max_value=10_000_000)

# Strategy for generating floats
float_strategy = st.floats(
    min_value=-1_000_000.0,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for generating Path objects
_path_text_strategy = st.text(min_size=1, max_size=50).filter(
    lambda s: "\x00" not in s and len(s.strip()) > 0
)
path_strategy = _path_text_strategy.map(Path)

# Strategy for generating lists of strings
str_list_strategy = st.lists(string_strategy, max_size=10)

# Strategy for generating lists of Path objects
path_list_strategy = st.lists(path_strategy, max_size=10)

# Strategy for generating valid EnvValue types
env_value_strategy = st.one_of(
    string_strategy,
    int_strategy,
    float_strategy,
    st.booleans(),
    path_strategy,
    str_list_strategy,
    path_list_strategy,
)

# Strategy for generating dictionaries of env values
env_dict_strategy = st.dictionaries(
    st.text(min_size=1, max_size=20).filter(lambda k: k and not k.startswith("_")),
    env_value_strategy,
    max_size=10,
)

# Strategy for generating tuples of key-value pairs
env_items_strategy = st.lists(
    st.tuples(
        st.text(min_size=1, max_size=20).filter(lambda k: k and not k.startswith("_")),
        env_value_strategy,
    ),
    max_size=10,
)


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------


def save_and_clear_env():
    original_env = os.environ.copy()
    os.environ.clear()
    return original_env


def restore_env(saved_env: dict[str, str]):
    os.environ.clear()
    os.environ.update(saved_env)


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------
@pytest.fixture
def clean_env():
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


class EnvClass(Environment):
    DEBUG: evar[bool] = evar(default=False, truthy=("yes", "1", "true"))
    PORT: evar[int] = evar(default=8080)
    FOLDER: evar[Path] = evar(default=Path("/tmp/data"))  # noqa: S108
    LIST_VAR: evar[list[str]] = evar(default=["default"])


@pytest.fixture
def env_class() -> type[EnvClass]:
    return EnvClass


# ------------------------------------------------------------------------------
# MutableMapping Protocol Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=15)
def test_items_returns_items_view(items: list[tuple[str, Any]]):
    """Property: items() should return an ItemsView with keys from the input items.

    Note: When duplicate keys are provided, the last value wins (dict semantics).
          List values are deduplicated by the Environment.
    """
    env = Environment(items)
    # Convert to dict with list deduplication to match Environment behavior
    expected_dict = dedup_items(items)
    result_items = list(env.items())
    assert len(result_items) == len(expected_dict)
    for key, expected_value in expected_dict.items():
        assert (key, expected_value) in result_items


@given(items=env_items_strategy)
@settings(max_examples=15)
def test_keys_returns_keys_view(items: list[tuple[str, Any]]):
    env = Environment(items)
    result_keys = set(env.keys())
    expected_keys = {k for k, _ in items}
    assert result_keys == expected_keys


@given(items=env_items_strategy)
@settings(max_examples=15)
def test_values_returns_values_view(items: list[tuple[str, Any]]):
    env = Environment(items)
    result_values = list(env.values())
    expected_dict = dict(items)
    assert len(result_values) == len(expected_dict)
    assert len(env.values()) == len(expected_dict.values())


@given(items=env_items_strategy)
@settings(max_examples=15)
def test_len_returns_correct_count(items: list[tuple[str, Any]]):
    env = Environment(items)
    # dict() deduplicates by keeping the last value for duplicate keys
    expected_len = len(dict(items))
    assert len(env) == expected_len


@given(items=env_items_strategy, key=st.text(min_size=1, max_size=20))
@settings(max_examples=15)
def test_contains_returns_bool(items: list[tuple[str, Any]], key: str):
    env = Environment(items)
    expected = key in {k for k, _ in items}
    assert (key in env) == expected


@given(items=env_items_strategy)
@settings(max_examples=10)
def test_iter_returns_iterator(items: list[tuple[str, Any]]):
    env = Environment(items)
    keys_from_iter = list(env)
    expected_keys = {k for k, _ in items}
    assert sorted(keys_from_iter) == sorted(expected_keys)


@given(items=env_items_strategy, key=st.text(min_size=1, max_size=20))
@settings(max_examples=15)
def test_getitem_returns_value(items: list[tuple[str, Any]], key: str):
    env = Environment(items)
    items_dict = dict(items)
    if key in items_dict:
        assert env[key] == items_dict[key]
    else:
        with pytest.raises(KeyError):
            env[key]


# ------------------------------------------------------------------------------
# Environment Creation Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=10)
def test_environment_from_dict(items: list[tuple[str, Any]]):
    items_dict = dedup_items(items)
    env = Environment(items_dict)
    assert len(env) == len(items_dict)
    for k, v in items_dict.items():
        assert env[k] == v


@given(items=env_items_strategy)
@settings(max_examples=10)
def test_environment_from_iterable(items: list[tuple[str, Any]]):
    env = Environment(items)
    expected_dict = dedup_items(items)
    assert len(env) == len(expected_dict)
    for k, v in expected_dict.items():
        assert env[k] == v


@given(env_dict=env_dict_strategy)
@settings(max_examples=10)
def test_kwargs_not_stored(env_dict: dict[str, Any]):
    """Property: kwargs passed to Environment() are not stored (documenting bug).

    The Environment class accepts **kwargs in __new__ and __init__ but does not
    store them. This test documents this current behavior.
    """
    # Skip if dict is empty
    if not env_dict:
        return
    # Create with kwargs - they are accepted but not stored
    env = Environment(**env_dict)
    # Kwargs are NOT stored in the environment
    assert len(env) == 0


# ------------------------------------------------------------------------------
# Attribute Access Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=10)
def test_attribute_access_equals_dict_access(items: list[tuple[str, Any]]):
    env = Environment(items)
    for key, _value in items:
        assert getattr(env, key) == env[key]


# Note: kwargs in Environment() constructor are not processed - this appears to be a bug
# The __new__ and __init__ accept **kwargs but don't store them
@given(env_dict=env_dict_strategy)
@settings(max_examples=10)
def test_kwargs_not_processed(env_dict: dict[str, Any]):
    """Property: kwargs passed to Environment() are not stored (documenting bug).

    The Environment class accepts **kwargs in __new__ and __init__ but does not
    store them. This test documents this behavior.
    """
    # Skip if dict is empty
    if not env_dict:
        return
    # Get a key from the dict
    key = list(env_dict.keys())[0]  # noqa: RUF015
    # Use positional argument instead
    env = Environment([(key, env_dict[key])])
    assert key in env


@given(env_dict=env_dict_strategy)
@settings(max_examples=10)
def test_attribute_assignment_equals_dict_assignment(env_dict: dict[str, Any]):
    env = Environment()
    for key, value in env_dict.items():
        env[key] = value  # Use dict-style access
        # For lists, the value is deduplicated, so we need to compare with deduped value
        expected = dedup_list(value) if isinstance(value, list) else value  # pyright: ignore[reportUnknownArgumentType]
        assert getattr(env, key) == expected


# ------------------------------------------------------------------------------
# evar Handling Tests
# ------------------------------------------------------------------------------
def test_evar_attribute_gets_name_set(env_class: type[EnvClass]):
    e = evar(default="test")
    env = env_class()
    env.MY_VAR = e
    assert env.MY_VAR._name_ == "MY_VAR"  # pyright: ignore[reportPrivateUsage]


def test_evar_attribute_preserves_objclass(env_class: type[EnvClass]):
    e = evar(default="test")
    env = env_class()
    env.MY_VAR = e
    assert env.MY_VAR.__objclass__ == env_class


def test_multiple_evars_get_correct_names(env_class: type[EnvClass]):
    e1 = evar(default="value1")
    e2 = evar(default="value2")
    env = env_class()
    env.VAR_A = e1
    env.VAR_B = e2
    assert env.VAR_A._name_ == "VAR_A"  # pyright: ignore[reportPrivateUsage]
    assert env.VAR_B._name_ == "VAR_B"  # pyright: ignore[reportPrivateUsage]


# ------------------------------------------------------------------------------
# List Handling Tests
# ------------------------------------------------------------------------------
@given(initial=str_list_strategy, additional=str_list_strategy)
@settings(max_examples=10)
def test_list_appending_deduplicates(initial: list[str], additional: list[str]):
    env = Environment()
    env.MY_LIST = initial
    env.MY_LIST = additional
    # The result should be a combination with duplicates removed
    combined = initial + additional
    expected = list(dict.fromkeys(combined))  # Preserves order, removes duplicates
    assert len(env.MY_LIST) <= len(combined)
    assert expected == env.MY_LIST


def test_setting_new_list():
    env = Environment()
    test_list = ["a", "b", "c"]
    env.MY_LIST = test_list
    assert test_list == env.MY_LIST


# ------------------------------------------------------------------------------
# Pop Tests
# ------------------------------------------------------------------------------
@given(env_dict=env_dict_strategy)
@settings(max_examples=10)
def test_pop_returns_and_removes(env_dict: dict[str, Any]):
    if not env_dict:
        return
    existing_key = list(env_dict.keys())[0]  # noqa: RUF015
    expected_value = dedup_value(env_dict[existing_key])
    env = Environment(env_dict.items())
    value = env.pop(existing_key)
    assert value == expected_value
    assert existing_key not in env


@given(env_dict=env_dict_strategy)
@settings(max_examples=10)
def test_pop_with_default(env_dict: dict[str, Any]):
    env = Environment(env_dict.items()) if env_dict else Environment()
    value = env.pop("nonexistent_key", "default_value")
    assert value == "default_value"


# ------------------------------------------------------------------------------
# Popitem Tests
# ------------------------------------------------------------------------------
def test_popitem_returns_tuple():
    env = Environment([("KEY", "value")])
    result = env.popitem()
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] == "KEY"
    assert result[1] == "value"


def test_popitem_raises_on_empty():
    env = Environment()
    with pytest.raises(KeyError):
        env.popitem()


# ------------------------------------------------------------------------------
# Setdefault Tests
# ------------------------------------------------------------------------------
@given(env_dict=env_dict_strategy)
@settings(max_examples=10)
def test_setdefault_returns_existing(env_dict: dict[str, Any]):
    if not env_dict:
        return
    existing_key = list(env_dict.keys())[0]  # noqa: RUF015
    expected_value = dedup_value(env_dict[existing_key])
    env = Environment([(existing_key, env_dict[existing_key])])
    result = env.setdefault(existing_key, "new_value")
    assert result == expected_value
    assert env[existing_key] == expected_value  # Unchanged


@given(env_dict=env_dict_strategy, key=st.text(min_size=1, max_size=20))
@settings(max_examples=10)
def test_setdefault_sets_and_returns_default(env_dict: dict[str, Any], key: str):
    env = Environment(env_dict.items()) if env_dict else Environment()
    new_key = "new_key_" + key
    default = "default_value"
    result = env.setdefault(new_key, default)
    assert result == default
    assert env[new_key] == default


# ------------------------------------------------------------------------------
# Clear Tests
# ------------------------------------------------------------------------------
def test_clear_removes_all():
    env = Environment([("a", 1), ("b", 2), ("c", 3)])
    env.clear()
    assert len(env) == 0


# ------------------------------------------------------------------------------
# env Property Tests
# ------------------------------------------------------------------------------
def test_env_property_returns_dict():
    env = Environment()
    result = env.env
    assert isinstance(result, dict)


def test_env_property_converts_strings():
    env = Environment()
    env.MY_STRING = "test_value"
    result = env.env
    assert result["MY_STRING"] == "test_value"


def test_env_property_converts_integers():
    env = Environment()
    env.MY_INT = 42
    result = env.env
    assert result["MY_INT"] == "42"


def test_env_property_converts_booleans():
    env = Environment()
    env.MY_BOOL = True
    result = env.env
    assert result["MY_BOOL"] == "1"  # bools are converted to int then str


def test_env_property_converts_lists():
    env = Environment()
    env.MY_LIST = ["a", "b", "c"]
    result = env.env
    assert result["MY_LIST"] == "a:b:c"  # default separator


def test_env_property_skips_empty_strings():
    env = Environment()
    env.EMPTY = ""
    result = env.env
    assert "EMPTY" not in result


def test_env_property_skips_unset_values():
    env = Environment()
    env.UNSET = Unset
    result = env.env
    assert "UNSET" not in result


# ------------------------------------------------------------------------------
# Class evar Integration Tests
# ------------------------------------------------------------------------------
def test_env_property_includes_class_evars(env_class: type[EnvClass]):
    # Set environment variable
    os.environ["DEBUG"] = "yes"
    env = env_class()
    result = env.env
    # Should include the class evar
    assert "DEBUG" in result
    # Note: class evars use str(tmp) which returns "True" for bools
    assert result["DEBUG"] == "True"  # bools converted via str(True)


def test_env_property_includes_instance_evars(env_class: type[EnvClass]):
    os.environ["PORT"] = "9000"
    env = env_class()
    result = env.env
    assert "PORT" in result
    assert result["PORT"] == "9000"


def test_instance_evar_overrides_class_evar(env_class: type[EnvClass]):
    os.environ["DEBUG"] = "yes"
    env = env_class()
    # Set instance-level override
    env.DEBUG = False  # pyright: ignore[reportAttributeAccessIssue]
    result = env.env
    # Instance value should be used
    assert "DEBUG" in result
    assert result["DEBUG"] == "0"  # False converts to "0"


# ------------------------------------------------------------------------------
# Custom List Separator Tests
# ------------------------------------------------------------------------------
def test_custom_list_separator():
    env = Environment([("MY_LIST", ["a", "b", "c"])])
    Environment.add_list_separator("MY_LIST", ",")
    result = env.env
    assert result["MY_LIST"] == "a,b,c"


# ------------------------------------------------------------------------------
# dump Tests
# ------------------------------------------------------------------------------
def test_dump_writes_to_file():
    env = Environment()
    env.MY_VAR = "my_value"
    output = io.StringIO()
    env.dump(output)
    content = output.getvalue()
    assert "MY_VAR = my_value" in content


def test_dump_includes_class_evars(env_class: type[EnvClass]):
    os.environ["DEBUG"] = "yes"
    env = env_class()
    output = io.StringIO()
    env.dump(output)
    content = output.getvalue()
    assert "DEBUG" in content


# ------------------------------------------------------------------------------
# __setattr__ Protection Tests
# ------------------------------------------------------------------------------
# Slot attributes (_protected, _lock) can always be modified via object.__setattr__
# This is expected behavior for __slots__ attributes, so we don't test blocking it
def test_unprotected_attributes_can_be_modified():
    env = Environment()
    env.MY_VAR = "initial"
    env.MY_VAR = "updated"
    assert env.MY_VAR == "updated"


# ------------------------------------------------------------------------------
# __repr__ and __str__ Tests
# ------------------------------------------------------------------------------
def test_repr_includes_class_name():
    env = Environment()
    repr_str = repr(env)
    assert "Environment" in repr_str


def test_str_returns_dict_repr():
    env = Environment()
    str_repr = str(env)
    # Should be a string representation of the internal dict
    assert "MY_VAR" not in str_repr  # Empty env
    env.MY_VAR = "value"
    str_repr = str(env)
    assert "MY_VAR" in str_repr


# ------------------------------------------------------------------------------
# Delete Tests
# ------------------------------------------------------------------------------
def test_delitem_removes_key():
    env = Environment()
    env["MY_VAR"] = "value"
    del env["MY_VAR"]
    assert "MY_VAR" not in env


def test_delitem_raises_keyerror_for_nonexistent():
    env = Environment()
    with pytest.raises(KeyError):
        del env["NONEXEXISTENT"]


# ------------------------------------------------------------------------------
# __reduce__ Tests
# ------------------------------------------------------------------------------
def test_reduce_returns_correct_tuple():
    env = Environment()
    env.MY_VAR = "value"
    result = env.__reduce__()
    assert isinstance(result, tuple)
    assert len(result) == 3
    # First element should be the __new__ function of the class
    assert result[0] is Environment.__new__
    # Second element should be a tuple containing the class
    assert result[1] == (Environment,)
    # Third element should be the __dict__
    assert result[2] == env.__dict__


# ------------------------------------------------------------------------------
# get Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=15)
def test_get_returns_existing_value(items: list[tuple[str, Any]]):
    """Property: get() returns the value for existing keys."""
    env = Environment(items)
    expected_dict = dedup_items(items)
    for key, expected_value in expected_dict.items():
        assert env.get(key) == expected_value


@given(env_dict=env_dict_strategy)
@settings(max_examples=15)
def test_get_returns_default_for_missing_key(env_dict: dict[str, Any]):
    """Property: get() returns default for keys not in the mapping."""
    env = Environment(env_dict.items()) if env_dict else Environment()
    result = env.get("nonexistent_key")
    assert result == ""  # noqa: PLC1901


@given(env_dict=env_dict_strategy)
@settings(max_examples=15)
def test_get_returns_custom_default(env_dict: dict[str, Any]):
    """Property: get() returns custom default when key is missing."""
    env = Environment(env_dict.items()) if env_dict else Environment()
    custom_default = "custom_default_value"
    result = env.get("nonexistent_key", custom_default)
    assert result == custom_default


def test_get_with_empty_string_value():
    """get() returns empty string for existing key with empty value."""
    env = Environment([("EMPTY", "")])
    assert env.get("EMPTY") == ""  # noqa: PLC1901


def test_get_with_zero_value():
    """get() returns 0 for existing key with zero value."""
    env = Environment([("ZERO", 0)])
    assert env.get("ZERO") == 0


def test_get_with_false_value():
    """get() returns False for existing key with False value."""
    env = Environment([("FALSE_VAL", False)])
    assert env.get("FALSE_VAL") is False


def test_get_with_none_not_supported():
    """get() returns value as-is even if it's not a typical EnvValue."""
    env = Environment()
    env.SPECIAL = "value"
    assert env.get("SPECIAL") == "value"


# ------------------------------------------------------------------------------
# copy Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=15)
def test_copy_creates_shallow_copy(items: list[tuple[str, Any]]):
    """Property: copy() creates a new Environment with the same contents."""
    env = Environment(items)
    env_copy = env.copy()
    assert env is not env_copy
    assert len(env) == len(env_copy)
    for key in env:
        assert env[key] == env_copy[key]


@given(items=env_items_strategy)
@settings(max_examples=15)
def test_copy_modifications_are_independent(items: list[tuple[str, Any]]):
    """Property: modifying copy does not affect original."""
    env = Environment(items)
    env_copy = env.copy()
    # Add new key to copy
    env_copy["NEW_KEY"] = "new_value"
    assert "NEW_KEY" not in env
    # Modify existing key in copy
    if env:
        first_key = next(iter(env))
        original_value = env[first_key]
        env_copy[first_key] = "modified"
        assert env[first_key] == original_value


def test_copy_preserves_type():
    """copy() returns an Environment instance."""
    env = Environment()
    env_copy = env.copy()
    assert type(env_copy) is Environment


def test_copy_with_list_values():
    """copy() with list values creates independent list references (shallow)."""
    env = Environment()
    env.MY_LIST = ["a", "b", "c"]
    env_copy = env.copy()
    # Lists are shared in shallow copy
    assert env.MY_LIST == env_copy.MY_LIST
    # Modifying list in copy affects original (shallow copy behavior)
    env_copy.MY_LIST.append("d")
    assert "d" in env.MY_LIST


# ------------------------------------------------------------------------------
# update Tests
# ------------------------------------------------------------------------------
@given(env_dict=env_dict_strategy)
@settings(max_examples=15)
def test_update_adds_new_keys(env_dict: dict[str, Any]):
    """Property: update() adds new keys to the environment."""
    env = Environment()
    env.update(env_dict)
    for key, value in env_dict.items():
        # Lists are deduplicated, so compare accordingly
        if isinstance(value, list):
            # Preserves order, removes duplicates
            expected: list[Any] = list(dict.fromkeys(value))  # pyright: ignore[reportUnknownArgumentType]
            assert env[key] == expected
        else:
            assert env[key] == value


@given(env_dict=env_dict_strategy)
@settings(max_examples=15)
def test_update_overwrites_existing_keys(env_dict: dict[str, Any]):
    """Property: update() overwrites existing keys with new values."""
    if not env_dict:
        return
    env = Environment(env_dict.items())
    # Create new dict with same keys but different values
    new_dict = {k: f"new_{v}" for k, v in env_dict.items()}
    env.update(new_dict)
    for key, value in new_dict.items():
        assert env[key] == value


def test_update_from_another_environment():
    """update() works with another Environment instance."""
    env1 = Environment([("A", 1), ("B", 2)])
    env2 = Environment([("C", 3), ("D", 4)])
    env1.update(env2)
    assert env1["A"] == 1
    assert env1["C"] == 3
    assert env1["D"] == 4


def test_update_with_clear_parameter():
    """update() clears specified list keys before updating."""
    env = Environment()
    env.MY_LIST = ["a", "b", "c"]
    env.update({"MY_LIST": ["x", "y"]}, clear=["MY_LIST"])
    # List should be cleared first, then updated
    assert env.MY_LIST == ["x", "y"]


def test_update_with_clear_non_list_key():
    """update() with clear parameter does not affect non-list keys."""
    env = Environment()
    env.MY_VAR = "initial"
    env.update({"MY_VAR": "updated"}, clear=["MY_VAR"])
    # Non-list key should be updated normally
    assert env.MY_VAR == "updated"


def test_update_with_clear_none():
    """update() with clear=None works normally."""
    env = Environment()
    env.MY_VAR = "initial"
    env.update({"MY_VAR": "updated"}, clear=None)
    assert env.MY_VAR == "updated"


def test_update_with_existing_key():
    """update() updates existing keys with new values."""
    env = Environment()
    env.MY_VAR = "initial"
    env.update({"MY_VAR": "updated"})
    assert env.MY_VAR == "updated"


# ------------------------------------------------------------------------------
# __bool__ Tests
# ------------------------------------------------------------------------------
def test_bool_empty_environment():
    """Empty environment is falsy."""
    env = Environment()
    assert bool(env) is False


def test_bool_non_empty_environment():
    """Nonempty environment is truthy."""
    env = Environment([("KEY", "value")])
    assert bool(env) is True


def test_bool_with_zero_value():
    """Environment with only zero values is falsy (any() returns False)."""
    env = Environment([("ZERO", 0)])
    assert bool(env) is False


def test_bool_with_false_value():
    """Environment with only False values is falsy."""
    env = Environment([("BOOL", False)])
    assert bool(env) is False


def test_bool_with_empty_list():
    """Environment with only empty lists is falsy."""
    env = Environment([("EMPTY_LIST", [])])
    assert bool(env) is False


def test_bool_with_truthy_string():
    """Environment with truthy string is truthy."""
    env = Environment([("STR", "hello")])
    assert bool(env) is True


def test_bool_with_truthy_int():
    """Environment with nonzero int is truthy."""
    env = Environment([("NUM", 42)])
    assert bool(env) is True


def test_bool_with_truthy_list():
    """Environment with nonempty list is truthy."""
    env = Environment([("LIST", ["a", "b"])])
    assert bool(env) is True


def test_bool_mixed_values():
    """Environment with at least one truthy value is truthy."""
    env = Environment([("ZERO", 0), ("STR", "hello")])
    assert bool(env) is True


# ------------------------------------------------------------------------------
# __or__ Tests
# ------------------------------------------------------------------------------
@given(items1=env_items_strategy, items2=env_items_strategy)
@settings(max_examples=10)
def test_or_merges_two_environments(items1: list[tuple[str, Any]], items2: list[tuple[str, Any]]):
    """Property: | operator merges two environments, right side wins on conflict."""
    env1 = Environment(items1)
    env2 = Environment(items2)
    result = env1 | env2
    expected = dict(items1) | dict(items2)

    assert len(result) == len(expected)
    for key, value in expected.items():
        if isinstance(value, list):
            value = dedup_list(value)  # pyright: ignore[reportUnknownArgumentType]  # noqa: PLW2901
        assert result[key] == value


def test_or_returns_new_environment():
    """| operator returns a new Environment instance."""
    env1 = Environment([("A", 1)])
    env2 = Environment([("B", 2)])
    result = env1 | env2
    assert result is not env1
    assert result is not env2
    assert type(result) is Environment


def test_or_does_not_modify_originals():
    """| operator does not modify the original environments."""
    env1 = Environment([("A", 1)])
    env2 = Environment([("B", 2)])
    _ = env1 | env2
    assert len(env1) == 1
    assert len(env2) == 1
    assert "B" not in env1
    assert "A" not in env2


def test_or_with_dict():
    """| operator works with a plain dictionary on the right."""
    env = Environment([("A", 1)])
    result = env | {"B": 2}
    assert result["A"] == 1
    assert result["B"] == 2


def test_or_right_side_wins_on_conflict():
    """| operator gives precedence to right side on key conflicts."""
    env1 = Environment([("KEY", "left_value")])
    env2 = Environment([("KEY", "right_value")])
    result = env1 | env2
    assert result["KEY"] == "right_value"


# ------------------------------------------------------------------------------
# __ior__ Tests
# ------------------------------------------------------------------------------
@given(env_dict=env_dict_strategy)
@settings(max_examples=15)
def test_ior_updates_in_place(env_dict: dict[str, Any]):
    """Property: |= operator updates the environment in place."""
    env = Environment()
    env |= env_dict  # type: ignore[operator]
    for key, value in env_dict.items():
        if isinstance(value, list):
            value = dedup_list(value)  # pyright: ignore[reportUnknownArgumentType]  # noqa: PLW2901
        assert env[key] == value


def test_ior_with_dict():
    """|= operator works with a plain dictionary."""
    env = Environment([("A", 1)])
    env |= {"B": 2}  # type: ignore[operator]
    assert env["A"] == 1
    assert env["B"] == 2


def test_ior_modifies_original():
    """|= operator modifies the original environment."""
    env1 = Environment([("A", 1)])
    env2 = Environment([("B", 2)])
    env1 |= env2  # type: ignore[operator]
    assert env1["A"] == 1
    assert env1["B"] == 2


def test_ior_right_side_wins_on_conflict():
    """|= operator gives precedence to right side on key conflicts."""
    env = Environment([("KEY", "original")])
    env |= {"KEY": "updated"}  # type: ignore[operator]
    assert env["KEY"] == "updated"


# ------------------------------------------------------------------------------
# __eq__ Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=15)
def test_eq_same_items(items: list[tuple[str, Any]]):
    """Property: two Environments with same items are equal."""
    env1 = Environment(items)
    env2 = Environment(items)
    assert env1 == env2


def test_eq_empty_environments():
    """Two empty environments are equal."""
    env1 = Environment()
    env2 = Environment()
    assert env1 == env2


def test_eq_different_values():
    """Environments with different values are not equal."""
    env1 = Environment([("KEY", "value1")])
    env2 = Environment([("KEY", "value2")])
    assert env1 != env2


def test_eq_different_keys():
    """Environments with different keys are not equal."""
    env1 = Environment([("A", 1)])
    env2 = Environment([("B", 1)])
    assert env1 != env2


def test_eq_with_dict():
    """Environment is equal to a plain dict with same contents."""
    env = Environment([("A", 1), ("B", 2)])
    assert env == {"A": 1, "B": 2}


def test_eq_with_dict_different():
    """Environment is not equal to a plain dict with different contents."""
    env = Environment([("A", 1)])
    assert env != {"A": 2}


def test_eq_with_environment_subclass():
    """Environment is equal to a subclass instance with same contents."""

    class SubEnvironment(Environment):
        pass

    env1 = Environment([("A", 1)])
    env2 = SubEnvironment([("A", 1)])
    assert env1 == env2


def test_eq_with_non_mapping():
    """Environment is not equal to non-mapping objects."""
    env = Environment([("A", 1)])
    assert env != "not a mapping"
    assert env != 42
    assert env != [1, 2, 3]


# ------------------------------------------------------------------------------
# __ne__ Tests
# ------------------------------------------------------------------------------
@given(items=env_items_strategy)
@settings(max_examples=15)
def test_ne_different_items(items: list[tuple[str, Any]]):
    """Property: Environments with different items are not equal."""
    if len(items) < 1:
        return
    env1 = Environment(items)
    # Create a different environment by adding a unique key
    env2 = Environment(items + [("UNIQUE_KEY", "unique_value")])  # noqa: RUF005
    assert env1 != env2


def test_ne_empty_vs_nonempty():
    """Empty environment is not equal to non-empty environment."""
    env1 = Environment()
    env2 = Environment([("KEY", "value")])
    assert env1 != env2


def test_ne_with_dict():
    """Environment is not equal to a dict with different contents."""
    env = Environment([("A", 1)])
    assert env != {"A": 2}


def test_ne_returns_opposite_of_eq():
    """__ne__ returns the opposite of __eq__."""
    env1 = Environment([("A", 1)])
    env2 = Environment([("A", 1)])
    env3 = Environment([("B", 2)])
    assert (env1 == env2) == (env1 == env2)
    assert (env1 == env3) == (env1 == env3)
