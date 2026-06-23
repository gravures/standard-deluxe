from __future__ import annotations

import os
from pathlib import Path
from typing import Any, final

import pytest
from deluxe.environ import Separator, evar
from deluxe.types import Unset, UnsetType
from hypothesis import assume, given, settings
from hypothesis import strategies as st


# ------------------------------------------------------------------------------
# Tested Properties
# ------------------------------------------------------------------------------
# 1. Type Detection Property Tests
# 2. Unwrap - Default Value Property Tests
# 3. Unwrap - Environment Variable Conversion Property Tests
# 4. Unwrap - Unset Default Property Tests
# 5. Boolean Conversion Behavior Tests
# 6. List Conversion Behavior Tests
# 7. Arithmetic Operations - Supported Types Property Tests
# 8. Arithmetic Operations - Unsupported Types Property Tests
# 9. Arithmetic Operations with evar Operands Property Tests
# 10. Recursive Default Resolution Property Tests
# 11. Representation Property Tests
# 12. Idempotence Property Tests
# 13. Derived evar Uses Default Property Tests


# ------------------------------------------------------------------------------
# Strategies
# ------------------------------------------------------------------------------
# Strategy for generating valid string values for environment variables
# Exclude null characters which can cause issues in os.getenv
string_strategy = st.text(min_size=0, max_size=100).filter(lambda s: "\x00" not in s)

# Strategy for generating integers
int_strategy = st.integers(min_value=-10_000_000, max_value=10_000_000)

# Strategy for generating floats (excluding NaN and infinity for simplicity)
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

# Strategy for generating non-empty lists of strings
non_empty_str_list_strategy = st.lists(
    string_strategy.filter(lambda s: s),  # non-empty strings
    min_size=1,
    max_size=10,
)

# Strategy for generating non-empty lists of Path objects
non_empty_path_list_strategy = st.lists(
    path_strategy,
    min_size=1,
    max_size=10,
)

# Strategy for generating truthy tuples (for boolean conversion)
truthy_strategy = st.tuples(
    st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters=("\x00")),
        min_size=1,
        max_size=10,
    ),
    st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters=("\x00")),
        min_size=1,
        max_size=10,
    ),
    st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters=("\x00")),
        min_size=1,
        max_size=10,
    ),
).map(tuple)

# Strategy for generating separators
separator_strategy = st.sampled_from([";", ":", ",", " "])

# Strategy for generating valid string representations of integers
int_string_strategy = st.integers(min_value=-10_000_000, max_value=10_000_000).map(str)

# Strategy for generating valid string representations of floats
float_string_strategy = st.floats(
    min_value=-1_000_000.0,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
).map(str)


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def _save_and_clear_env() -> dict[str, str]:
    original_env = os.environ.copy()
    os.environ.clear()
    return original_env


def _restore_env(saved_env: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(saved_env)


# ------------------------------------------------------------------------------
# Type Detection Property Tests
# ------------------------------------------------------------------------------
@given(
    default=st.one_of(string_strategy, int_strategy, float_strategy, st.booleans(), path_strategy)
)
@settings(max_examples=20)
def test_property_type_matches_default_type(default: str | float | bool | Path) -> None:
    e = evar(default=default)
    assert e.type is type(default)


@given(default=non_empty_str_list_strategy)
@settings(max_examples=10)
def test_property_type_is_list_for_string_lists(default: list[str]) -> None:
    e = evar(default=default)
    assert e.type is list


@given(default=non_empty_path_list_strategy)
@settings(max_examples=10)
def test_property_type_is_list_for_path_lists(default: list[Path]) -> None:
    e = evar(default=default)
    assert e.type is list


# ------------------------------------------------------------------------------
# Unwrap - Default Value Property Tests
# ------------------------------------------------------------------------------


@given(default=string_strategy)
@settings(max_examples=15)
def test_property_unwrap_returns_default_string_when_env_not_set(default: str) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[str] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == default
    finally:
        _restore_env(saved_env)


@given(default=int_strategy)
@settings(max_examples=15)
def test_property_unwrap_returns_default_int_when_env_not_set(default: int) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[int] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == default
    finally:
        _restore_env(saved_env)


@given(default=float_strategy)
@settings(max_examples=15)
def test_property_unwrap_returns_default_float_when_env_not_set(default: float) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[float] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == default
    finally:
        _restore_env(saved_env)


@given(default=st.booleans())
@settings(max_examples=5)
def test_property_unwrap_returns_default_bool_when_env_not_set(default: bool) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[bool] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() is default
    finally:
        _restore_env(saved_env)


@given(default=path_strategy)
@settings(max_examples=10)
def test_property_unwrap_returns_default_path_when_env_not_set(default: Path) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[Path] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == default
    finally:
        _restore_env(saved_env)


@given(default=non_empty_str_list_strategy)
@settings(max_examples=10)
def test_property_unwrap_returns_default_string_list_when_env_not_set(default: list[str]) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[list[str]] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == default
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Unwrap - Environment Variable Conversion Property Tests
# ------------------------------------------------------------------------------
@given(env_value=string_strategy, default=string_strategy)
@settings(max_examples=15)
def test_property_unwrap_converts_env_to_string(env_value: str, default: str) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = env_value

        class TestConfig:
            TEST_VAR: evar[str] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == env_value
    finally:
        _restore_env(saved_env)


@given(env_string=int_string_strategy, default=int_strategy)
@settings(max_examples=15)
def test_property_unwrap_converts_env_string_to_int(env_string: str, default: int) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = env_string

        class TestConfig:
            TEST_VAR: evar[int] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == int(env_string)
    finally:
        _restore_env(saved_env)


@given(env_string=float_string_strategy, default=float_strategy)
@settings(max_examples=15)
def test_property_unwrap_converts_env_string_to_float(env_string: str, default: float) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = env_string

        class TestConfig:
            TEST_VAR: evar[float] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == float(env_string)  # noqa: RUF069
    finally:
        _restore_env(saved_env)


@given(
    env_value=string_strategy,
    default=st.booleans(),
    truthy=truthy_strategy,
)
@settings(max_examples=20)
def test_property_unwrap_converts_env_to_bool_using_truthy(
    env_value: str,
    default: bool,
    truthy: tuple[str, ...],
) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = env_value

        class TestConfig:
            TEST_VAR: evar[bool] = evar(default=default, truthy=truthy)

        expected = env_value.casefold() in tuple(t.casefold() for t in truthy)
        assert TestConfig.TEST_VAR.unwrap() == expected
    finally:
        _restore_env(saved_env)


@given(env_value=_path_text_strategy, default=path_strategy)
@settings(max_examples=15)
def test_property_unwrap_converts_env_to_path(env_value: str, default: Path) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = env_value

        class TestConfig:
            TEST_VAR: evar[Path] = evar(default=default)

        assert TestConfig.TEST_VAR.unwrap() == Path(env_value)
    finally:
        _restore_env(saved_env)


@given(
    items=non_empty_str_list_strategy,
    separator=separator_strategy,
)
@settings(max_examples=15)
def test_property_unwrap_converts_env_to_string_list(
    items: list[str], separator: Separator
) -> None:
    saved_env = _save_and_clear_env()
    try:
        joined = separator.join(items)
        os.environ["TEST_VAR"] = joined

        class TestConfig:
            TEST_VAR: evar[list[Any]] = evar(default=[], separator=separator)

        result = TestConfig.TEST_VAR.unwrap()
        # Filter empty strings for comparison (they can come from consecutive separators)
        non_empty_items = [item for item in joined.split(separator) if item]
        non_empty_result = [item for item in result if item]
        assert non_empty_result == non_empty_items
    finally:
        _restore_env(saved_env)


@given(
    items=non_empty_path_list_strategy,
    separator=separator_strategy,
)
@settings(max_examples=15)
def test_property_unwrap_converts_env_to_path_list(
    items: list[Path], separator: Separator
) -> None:
    assume(all(separator not in str(p) for p in items))
    saved_env = _save_and_clear_env()
    try:
        joined = separator.join(str(item) for item in items)
        os.environ["TEST_VAR"] = joined

        class TestConfig:
            TEST_VAR: evar[list[Path]] = evar(default=[Path("/")], separator=separator)

        result = TestConfig.TEST_VAR.unwrap()
        # Filter empty paths for comparison
        non_empty_result = [item for item in result if str(item)]
        assert non_empty_result == items  # non_empty_items
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Unwrap - Unset Default Property Tests
# ------------------------------------------------------------------------------
def test_property_unwrap_returns_unset_when_no_default_and_no_env() -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[UnsetType] = evar()

        result = TestConfig.TEST_VAR.unwrap()
        assert isinstance(result, UnsetType)
        assert result is Unset
    finally:
        _restore_env(saved_env)


@given(env_value=string_strategy)
@settings(max_examples=15)
def test_property_unwrap_returns_string_when_no_default_but_env_set(env_value: str) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = env_value

        class TestConfig:
            TEST_VAR: evar[UnsetType] = evar()

        assert TestConfig.TEST_VAR.unwrap() == env_value
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Boolean Conversion Behavior Tests (via unwrap)
# ------------------------------------------------------------------------------
@given(
    truthy=truthy_strategy,
    value=string_strategy,
)
@settings(max_examples=30)
def test_property_bool_conversion_returns_true_only_for_truthy_values(
    truthy: tuple[str, ...],
    value: str,
) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["TEST_VAR"] = value

        class TestConfig:
            TEST_VAR: evar[bool] = evar(default=False, truthy=truthy)

        result = TestConfig.TEST_VAR.unwrap()
        expected = value.casefold() in tuple(t.casefold() for t in truthy)
        assert result == expected
    finally:
        _restore_env(saved_env)


@given(truthy=truthy_strategy)
@settings(max_examples=10)
def test_property_bool_conversion_case_insensitive(truthy: tuple[str, ...]) -> None:
    assume(len(truthy) > 0)

    class TestConfig:
        TEST_VAR: evar[bool] = evar(default=False, truthy=truthy)

    original = truthy[0]
    # Test uppercase, lowercase, and mixed case versions
    variations = [original.upper(), original.lower(), original.swapcase()]
    for variation in variations:
        saved_env = _save_and_clear_env()
        try:
            os.environ["TEST_VAR"] = variation
            result = TestConfig.TEST_VAR.unwrap()
            expected = variation.casefold() in tuple(t.casefold() for t in truthy)
            assert result == expected
        finally:
            _restore_env(saved_env)


# ------------------------------------------------------------------------------
# List Conversion Behavior Tests (via unwrap)
# ------------------------------------------------------------------------------
@given(
    separator=separator_strategy,
    items=non_empty_str_list_strategy,
)
@settings(max_examples=20)
def test_property_list_conversion_join_split_roundtrip(
    separator: Separator, items: list[str]
) -> None:
    assume(all(separator not in p for p in items))
    saved_env = _save_and_clear_env()
    try:
        joined = separator.join(items)
        os.environ["TEST_VAR"] = joined

        class TestConfig:
            TEST_VAR: evar[list[str]] = evar(default=[], separator=separator)

        result = TestConfig.TEST_VAR.unwrap()
        # Items that don't contain the separator should be preserved
        items_without_sep = [item for item in items if separator not in item]
        result_without_sep = [item for item in result if separator not in item]
        assert items_without_sep == result_without_sep
    finally:
        _restore_env(saved_env)


@given(
    items=non_empty_path_list_strategy,
    separator=separator_strategy,
)
@settings(max_examples=15)
def test_property_list_conversion_returns_paths_when_default_is_path_list(
    items: list[Path],
    separator: Separator,
) -> None:
    saved_env = _save_and_clear_env()
    try:
        joined = separator.join(str(item) for item in items)
        os.environ["TEST_VAR"] = joined

        class TestConfig:
            TEST_VAR: evar[list[Path]] = evar(default=[Path("/")], separator=separator)

        result = TestConfig.TEST_VAR.unwrap()
        assert all(isinstance(item, Path) for item in result)
    finally:
        _restore_env(saved_env)


@given(
    items=non_empty_str_list_strategy,
    separator=separator_strategy,
)
@settings(max_examples=15)
def test_property_list_conversion_returns_strings_when_default_is_string_list(
    items: list[str],
    separator: Separator,
) -> None:
    saved_env = _save_and_clear_env()
    try:
        joined = separator.join(items)
        os.environ["TEST_VAR"] = joined

        class TestConfig:
            TEST_VAR: evar[list[str]] = evar(default=[""], separator=separator)

        result = TestConfig.TEST_VAR.unwrap()
        assert all(isinstance(item, str) for item in result)
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Arithmetic Operations - Supported Types Property Tests
# ------------------------------------------------------------------------------
@given(value=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_addition_returns_correct_int(value: int, operand: int) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = TestConfig.BASE_VAR + operand
        # assert isinstance(derived, evar)
        assert derived.type is int
        assert derived.unwrap() == value + operand
    finally:
        _restore_env(saved_env)


@given(value=float_strategy, operand=float_strategy)
@settings(max_examples=15)
def test_property_addition_returns_correct_float(value: float, operand: float) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[float] = evar(default=value)

        derived = TestConfig.BASE_VAR + operand
        # assert isinstance(derived, evar)
        assert derived.type is float
        assert abs(derived.unwrap() - (value + operand)) < 1e-9  # noqa: PLR2004
    finally:
        _restore_env(saved_env)


@given(value=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_subtraction_returns_correct_int(value: int, operand: int) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = TestConfig.BASE_VAR - operand
        # assert isinstance(derived, evar)
        assert derived.type is int
        assert derived.unwrap() == value - operand
    finally:
        _restore_env(saved_env)


@given(value=float_strategy, operand=float_strategy)
@settings(max_examples=15)
def test_property_subtraction_returns_correct_float(value: float, operand: float) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[float] = evar(default=value)

        derived = TestConfig.BASE_VAR - operand
        # assert isinstance(derived, evar)
        assert derived.type is float
        assert abs(derived.unwrap() - (value - operand)) < 1e-9  # noqa: PLR2004
    finally:
        _restore_env(saved_env)


@given(value=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_multiplication_returns_correct_int(value: int, operand: int) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = TestConfig.BASE_VAR * operand
        # assert isinstance(derived, evar)
        assert derived.type is int
        assert derived.unwrap() == value * operand
    finally:
        _restore_env(saved_env)


@given(value=float_strategy, operand=float_strategy)
@settings(max_examples=15)
def test_property_multiplication_returns_correct_float(value: float, operand: float) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[float] = evar(default=value)

        derived = TestConfig.BASE_VAR * operand
        # assert isinstance(derived, evar)
        assert derived.type is float
        assert abs(derived.unwrap() - (value * operand)) < 1e-9  # noqa: PLR2004
    finally:
        _restore_env(saved_env)


@given(value=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_division_returns_correct_int(value: int, operand: int) -> None:
    assume(operand != 0)
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = TestConfig.BASE_VAR / operand
        # assert isinstance(derived, evar)
        assert derived.type is int
        assert derived.unwrap() == int(value / operand)  # value // operand
    finally:
        _restore_env(saved_env)


@given(value=float_strategy, operand=float_strategy)
@settings(max_examples=15)
def test_property_division_returns_correct_float(value: float, operand: float) -> None:

    assume(abs(operand) > 1e-9)  # Avoid division by near-zero  # noqa: PLR2004
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[float] = evar(default=value)

        derived = TestConfig.BASE_VAR / operand
        # assert isinstance(derived, evar)
        assert derived.type is float
        assert abs(derived.unwrap() - (value / operand)) < 1e-9  # noqa: PLR2004
    finally:
        _restore_env(saved_env)


@given(value=int_strategy)
@settings(max_examples=15)
def test_property_abs_returns_positive_int(value: int) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = abs(TestConfig.BASE_VAR)
        # assert isinstance(derived, evar)
        assert derived.type is int
        assert derived.unwrap() == abs(value)
    finally:
        _restore_env(saved_env)


@given(value=float_strategy)
@settings(max_examples=15)
def test_property_abs_returns_positive_float(value: float) -> None:
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(value)

        class TestConfig:
            BASE_VAR: evar[float] = evar(default=value)

        derived = abs(TestConfig.BASE_VAR)
        # assert isinstance(derived, evar)
        assert derived.type is float
        assert abs(derived.unwrap() - abs(value)) < 1e-9  # noqa: PLR2004
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Arithmetic Operations - Unsupported Types Property Tests
# ------------------------------------------------------------------------------
@given(value=string_strategy, operand=string_strategy)
@settings(max_examples=10)
def test_property_addition_not_implemented_for_strings(value: str, operand: str) -> None:
    class TestConfig:
        TEST_VAR: evar[str] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR + operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=path_strategy, operand=path_strategy)
@settings(max_examples=10)
def test_property_addition_not_implemented_for_paths(value: Path, operand: Path) -> None:
    class TestConfig:
        TEST_VAR: evar[Path] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR + operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=string_strategy, operand=int_strategy)
@settings(max_examples=10)
def test_property_subtraction_not_implemented_for_strings(value: str, operand: int) -> None:
    class TestConfig:
        TEST_VAR: evar[str] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR - operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=path_strategy, operand=int_strategy)
@settings(max_examples=10)
def test_property_subtraction_not_implemented_for_paths(value: Path, operand: int) -> None:
    class TestConfig:
        TEST_VAR: evar[Path] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR - operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=string_strategy, operand=int_strategy)
@settings(max_examples=10)
def test_property_multiplication_not_implemented_for_strings(value: str, operand: int) -> None:
    class TestConfig:
        TEST_VAR: evar[str] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR * operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=path_strategy, operand=int_strategy)
@settings(max_examples=10)
def test_property_multiplication_not_implemented_for_paths(value: Path, operand: int) -> None:
    class TestConfig:
        TEST_VAR: evar[Path] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR * operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=string_strategy, operand=int_strategy)
@settings(max_examples=10)
def test_property_division_not_implemented_for_strings(value: str, operand: int) -> None:
    class TestConfig:
        TEST_VAR: evar[str] = evar(default=value)

    with pytest.raises(NotImplementedError):
        _ = TestConfig.TEST_VAR / operand  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]


@given(value=string_strategy)
@settings(max_examples=10)
def test_property_abs_not_implemented_for_strings(value: str) -> None:
    class TestConfig:
        TEST_VAR: evar[str] = evar(default=value)

    with pytest.raises(NotImplementedError):
        abs(TestConfig.TEST_VAR)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]


# ------------------------------------------------------------------------------
# Arithmetic Operations with evar Operands Property Tests
# ------------------------------------------------------------------------------
@given(base=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_arithmetic_with_evar_operand_add(base: int, operand: int) -> None:
    """
    Property: Adding two int evars should compute the correct sum.
    """
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(base)
        os.environ["OPERAND_VAR"] = str(operand)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=base)
            OPERAND_VAR: evar[int] = evar(default=operand)

        derived = TestConfig.BASE_VAR + TestConfig.OPERAND_VAR
        # assert isinstance(derived, evar)
        assert derived.unwrap() == base + operand
    finally:
        _restore_env(saved_env)


@given(base=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_arithmetic_with_evar_operand_subtract(base: int, operand: int) -> None:
    """
    Property: Subtracting two int evars should compute the correct difference.
    """
    saved_env = _save_and_clear_env()
    try:
        os.environ["BASE_VAR"] = str(base)
        os.environ["OPERAND_VAR"] = str(operand)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=base)
            OPERAND_VAR: evar[int] = evar(default=operand)

        derived = TestConfig.BASE_VAR - TestConfig.OPERAND_VAR
        # assert isinstance(derived, evar)
        assert derived.unwrap() == base - operand
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Recursive Default Resolution Property Tests
# ------------------------------------------------------------------------------
@given(default1=string_strategy)
@settings(max_examples=10)
def test_property_recursive_default_resolution(default1: str) -> None:
    saved_env = _save_and_clear_env()
    try:

        @final
        class TestConfig:
            TEST_VAR_A: evar[str] = evar(default=default1)
            TEST_VAR_B: evar[str] = evar(default=TEST_VAR_A)

        assert TestConfig.TEST_VAR_B.unwrap() == default1
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Representation Property Tests
# ------------------------------------------------------------------------------
@given(
    default=st.one_of(string_strategy, int_strategy, float_strategy, st.booleans(), path_strategy)
)
@settings(max_examples=15)
def test_property_repr_contains_type_name(default: str | float | bool | Path) -> None:
    e = evar(default=default)
    repr_str = repr(e)
    type_name = type(default).__name__
    assert type_name in repr_str


@given(default=st.one_of(string_strategy, int_strategy, float_strategy, st.booleans()))
@settings(max_examples=15)
def test_property_repr_contains_default_value(default: str | float | bool) -> None:
    e = evar(default=default)
    repr_str = repr(e)
    assert repr(default) in repr_str


def test_property_repr_for_unset_default() -> None:
    e = evar()
    repr_str = repr(e)
    assert "Unset" in repr_str


# ------------------------------------------------------------------------------
# Idempotence Property Tests
# ------------------------------------------------------------------------------
@given(default=string_strategy)
@settings(max_examples=15)
def test_property_unwrap_idempotent_for_string(default: str) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[str] = evar(default=default)

        first = TestConfig.TEST_VAR.unwrap()
        second = TestConfig.TEST_VAR.unwrap()
        assert first == second
    finally:
        _restore_env(saved_env)


@given(default=int_strategy)
@settings(max_examples=15)
def test_property_unwrap_idempotent_for_int(default: int) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            TEST_VAR: evar[int] = evar(default=default)

        first = TestConfig.TEST_VAR.unwrap()
        second = TestConfig.TEST_VAR.unwrap()
        assert first == second
    finally:
        _restore_env(saved_env)


# ------------------------------------------------------------------------------
# Derived evar Uses Default Property Tests
# ------------------------------------------------------------------------------
@given(value=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_derived_evar_uses_default_when_env_not_set(value: int, operand: int) -> None:
    saved_env = _save_and_clear_env()
    try:

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = TestConfig.BASE_VAR + operand
        assert derived.unwrap() == value + operand
    finally:
        _restore_env(saved_env)


@given(value=int_strategy, operand=int_strategy)
@settings(max_examples=15)
def test_property_derived_evar_uses_env_when_set(value: int, operand: int) -> None:
    saved_env = _save_and_clear_env()
    try:
        env_value = value + 100  # Different from default
        os.environ["BASE_VAR"] = str(env_value)

        class TestConfig:
            BASE_VAR: evar[int] = evar(default=value)

        derived = TestConfig.BASE_VAR + operand
        assert derived.unwrap() == env_value + operand
    finally:
        _restore_env(saved_env)
