from __future__ import annotations

import pytest  # noqa: F401
from deluxe.enums import Enum
from hypothesis import given
from hypothesis import strategies as st


class A(Enum):
    """My documented enum."""

    ONE = 1
    """The 1 literal value.

    Body of this docstring.
    """

    TWO = 2
    """Another literal value.

    Body of this docstring.
    """


class Named:
    def __init__(self, value: object) -> None:
        self.my_value: object = value
        self.my_name: str
        self.__objclass__: type

    def __set_name__(self, owner: type, name: str) -> None:
        self.my_name = name
        self.__objclass__ = owner


class E(Enum):
    ONE = Named(1)
    TWO = Named("2")


@given(st.just(E))
def test_set_name_member_method_was_called(enum: type[Enum]):
    for member in enum:
        assert member.value.my_name == member.name
        assert member.value.__objclass__ is enum


@given(st.just(A))
def test_inline_docstring_not_class_docstring(enum: type[Enum]):
    assert enum(1).__doc__ != enum.__doc__


@given(st.just(A))
def test_inline_docstring_not_another_meember_docstring(enum: type[Enum]):
    assert enum(1).__doc__ != enum(2).__doc__


@given(st.just(A))
def test_inline_docstring_is_multiline(enum: type[Enum]):
    assert len(getattr(enum(1), "__doc__", "").splitlines()) > 1
