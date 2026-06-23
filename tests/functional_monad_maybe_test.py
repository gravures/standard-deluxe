from __future__ import annotations

from typing import Any

from deluxe import types
import pytest
from deluxe.functional import Maybe
from deluxe.types import UnsetType


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def parse_int(value: str) -> Maybe[int]:
    try:
        return Maybe(int(value))
    except ValueError:
        return Maybe()


def is_positive(value: int) -> Maybe[int]:
    return Maybe(value) if value > 0 else Maybe()


def process(value: str) -> Maybe[int]:
    result = Maybe(value).bind(parse_int)
    return result.bind(lambda n: Maybe(2 * n))


# ------------------------------------------------------------------------------
# Pattern Matching Behaviour
# ------------------------------------------------------------------------------
MAYBE_MATCH = [
    ("2", 4),
    ("4", "eight"),
    ("a", "error"),
]


# FIXME: do not work statically nor at runtime
# @pytest.mark.parametrize(argnames="value,expected", argvalues=MAYBE_MATCH)
# def test_match_with_unset(value: Any, expected: Any):
#     match process(value):
#         case Maybe(Unset):
#             result = "error"
#         case Maybe(8):
#             result = "eight"
#         case Maybe(other):
#             result = other
#     assert result == expected


@pytest.mark.parametrize(argnames=("value", "expected"), argvalues=MAYBE_MATCH)
def test_match_with_unsettype(value: Any, expected: Any):
    match process(value):
        case Maybe(UnsetType()):  # ok!
            result = "error"
        case Maybe(8):
            result = "eight"
        case Maybe(other):
            result = other
    assert result == expected


@pytest.mark.parametrize(argnames=("value", "expected"), argvalues=MAYBE_MATCH)
def test_match_with_types_dot_unset(value: Any, expected: Any):
    match process(value):
        case Maybe(types.Unset):  # ok
            result = "error"
        case Maybe(8):
            result = "eight"
        case Maybe(other):
            result = other
    assert result == expected
