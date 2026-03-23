from __future__ import annotations

import sys
from copy import copy
from dataclasses import dataclass
from typing import Any, ClassVar, NamedTuple

import pytest

# from deluxe._ctypes import Freeze as CFreeze
from deluxe.types import Frozen, Unset


def test_fields_polymorphism():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a",)

    class B(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("b",)

    class C(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("c",)

    class Z(A, B, C): ...

    assert Z.__frozen__ == ("a", "b", "c")
    assert tuple(Z()) == (Unset, Unset, Unset)


def test_fields_inheritance():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a",)

    class B(A):
        __frozen__: ClassVar[tuple[str, ...]] = ("b",)

    class C(B):
        __frozen__: ClassVar[tuple[str, ...]] = ("c",)

    class Z(C): ...

    assert Z.__frozen__ == ("a", "b", "c")
    assert tuple(Z()) == (Unset, Unset, Unset)

    class Y(C):
        __frozen__: ClassVar[tuple[str, ...]] = ("a", "c", "z")

    assert Y.__frozen__ == ("a", "b", "c", "z")
    assert tuple(Y()) == (Unset, Unset, Unset, Unset)


def test_unhashable():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a",)

    with pytest.raises(TypeError):
        hash(A())


def test_hashable():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a", "b")

    a = A()
    a.a = "a"  # pyright: ignore[reportAttributeAccessIssue]
    a.b = "b"  # pyright: ignore[reportAttributeAccessIssue]
    assert hash(a) == hash(("a", "b"))


def test_unset():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a", "b")

    a = A()
    assert tuple(a) == (Unset, Unset)


def test_set_unset_not_freeze():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a", "b")

    a = A()
    a.a = Unset  # pyright: ignore[reportAttributeAccessIssue]
    a.a = "a"  # pyright: ignore[reportAttributeAccessIssue]
    assert a.a == "a"  # pyright: ignore[reportAttributeAccessIssue]


def test_reset():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a", "b")

    a = A()
    a.a = "a"  # pyright: ignore[reportAttributeAccessIssue]

    with pytest.raises(AttributeError):
        a.a = None  # pyright: ignore[reportAttributeAccessIssue]


def test_del():
    class A(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("a", "b")

    a = A()
    a.a = "a"  # pyright: ignore[reportAttributeAccessIssue]

    with pytest.raises(TypeError):
        del a.a  # pyright: ignore[reportAttributeAccessIssue]


@pytest.fixture
def point():
    class Point(Frozen):
        __frozen__: ClassVar[tuple[str, ...]] = ("x", "y", "z")

        def __init__(self, x: float, y: float, z: float):
            self.x: float = x
            self.y: float = y
            self.z: float = z

    return Point


def test_iter(point: type):
    p = point(1, 2, 3)
    for a, b in zip(p, (1, 2, 3), strict=False):
        assert a == b


def test_contains(point: type):
    p = point(1, 2, 3)
    assert 2 in p
    assert 0 not in p


def test_len(point: type):
    p = point(1, 2, 3)
    assert len(p) == 3


def test_getitem(point: type):
    p = point(1, 2, 3)
    assert p[0] == 1
    assert p[1] == 2
    assert p[2] == 3
    assert p[-1] == 3


def test_getitem_out_of_range(point: type):
    p = point(1, 2, 3)

    with pytest.raises(IndexError):
        _ = p[3]
    with pytest.raises(IndexError):
        _ = p[-4]


def test_as_dict(point: type):
    p = point(1, 2, 3)
    assert p.as_dict() == {"x": 1, "y": 2, "z": 3}


def test_huge_instantiation_not_crash(point: type):
    p = None
    for _i in range(1_000_000):
        p = point(1, 2, 3)
    assert bool(p)


def test_reference_counting(point: type):
    class O: ...  # noqa: E742

    o = O()
    ref_count = sys.getrefcount(o)
    ref = None
    for _i in range(1_000):
        ref = point(o, o, o)
    del ref
    assert sys.getrefcount(o) == ref_count


def test_copy_protocol(point: type):
    p = point(1, 2, 3)
    c = copy(p)
    assert type(c) is type(p)
    assert c is not p
    assert p == c
    assert c == p


##
# Benchmarks
#
BENCHMARK_ROUNDS = 100


class DictPoint:  # noqa: B903
    def __init__(self, x: float, y: float, z: float):
        self.x: float = x
        self.y: float = y
        self.z: float = z


class SlottedPoint:  # noqa: B903
    __slots__: ClassVar[set[str]] = {"x", "y", "z"}

    def __init__(self, x: float, y: float, z: float):
        self.x: float = x
        self.y: float = y
        self.z: float = z


class HandFrozenPoint:
    __slots__: ClassVar[set[str]] = {"x", "y", "z"}

    def __init__(self, x: float, y: float, z: float):
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "z", z)

    def __setattr__(self, name: str, value: object, /) -> None:
        if name in {"x", "y", "z"} and hasattr(self, name):
            msg = f"{name} attribute is immutable"
            raise AttributeError(msg)
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str, /) -> None:
        if name in {"x", "y", "z"}:
            msg = f"{name} attribute is immutable"
            raise TypeError(msg)
        object.__delattr__(self, name)


class FrozenPoint(Frozen):
    __frozen__: ClassVar[tuple[str, ...]] = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float):
        self.x: float = x
        self.y: float = y
        self.z: float = z


class NtPoint(NamedTuple):
    x: float
    y: float
    z: float


@dataclass(frozen=True, slots=True)
class DataclassPoint:
    x: float
    y: float
    z: float


def test_new_slots_point(benchmark: Any):
    benchmark(SlottedPoint, 1.3, 2.432, -4.72)


def test_new_dict_point(benchmark: Any):
    benchmark(DictPoint, 1.3, 2.432, -4.72)


def test_new_frozen_point(benchmark: Any):
    benchmark(FrozenPoint, 1.3, 2.432, -4.72)


def test_new_hand_frozen_point(benchmark: Any):
    benchmark(HandFrozenPoint, 1.3, 2.432, -4.72)


def test_new_named_tuple_point(benchmark: Any):
    benchmark(NtPoint, 1.3, 2.432, -4.72)


def test_new_dataclass_point(benchmark: Any):
    benchmark(DataclassPoint, 1.3, 2.432, -4.72)
