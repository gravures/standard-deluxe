from __future__ import annotations

from typing import TYPE_CHECKING, Any, assert_type

import pytest
from deluxe.types import Unset, UnsetType


if TYPE_CHECKING:
    from collections.abc import Callable


def test_is_falsy():
    assert bool(Unset) is False


def test_is_singleton():
    assert UnsetType() is Unset


def test_do_not_instantiate():
    with pytest.raises(TypeError):
        Unset()


def test_subclassing_unset():
    with pytest.raises(TypeError):

        class _(Unset): ...


def test_subclassing_unsettype():
    with pytest.raises(TypeError):

        class _(UnsetType): ...


def test_unset_imutability():
    with pytest.raises(TypeError):
        Unset.a = 0


def test_unsettype_imutability():
    with pytest.raises(TypeError):
        UnsetType.a = 0


def test_hashability():
    with pytest.raises(TypeError):
        hash(Unset)


# NOTE: Not really essential
# def test_weakref():
#     with pytest.raises(TypeError):
#         weakref.ref(Unset)


def test_repr():
    assert repr(Unset) == "Unset"


def test_type_annonation():
    # This test nothing at runtime

    string: str = "hello"  # noqa: F841
    other: str = Unset  # noqa: F841

    class A: ...

    func: Callable[..., Any] = Unset  # noqa: F841

    a: A = Unset  # noqa: F841
    # none: NoneType = Unset
    # u: Unset = "world"  # invalid


def test_typing_puzzle_006():
    # This test nothing at runtime
    # see: https://github.com/anthonywritescode/typing-puzzles/blob/main/puzzles/006/README.md

    def do(x: int | None = Unset) -> None:
        if x is Unset:
            _ = "no `x` was passed!"  # pyright: ignore[reportUnreachable]
        elif x is None:
            _ = "`x` was explicitly passed as `None`"
        else:
            assert_type(x, int)
            _ = f"x**2 is {x**2}"

    do()
    do(None)
    do(9001)
    with pytest.raises(TypeError):
        do("no")  # should be a static type error!  # pyright: ignore[reportArgumentType]
