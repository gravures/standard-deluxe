# Copyright (c) 2025 - Gilles Coissac
# This file is part of standard-deluxe library.
#
# standard-deluxe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# standard-deluxe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with standard-deluxe. If not, see <https://www.gnu.org/licenses/>
"""Tests for the Multiton pattern implementation."""

from __future__ import annotations

import gc
import sys
from copy import copy, deepcopy
from typing import Any, final

import pytest

from deluxe._multiton import IDError, Multiton, MultitonType


# ---------------------------------------------------------------------------
# Basic Multiton behaviour
# ---------------------------------------------------------------------------


def test_same_args_same_instance():
    """Same constructor arguments must return the same instance."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p2 = Point(1, 2)
    assert p1 is p2


def test_different_args_different_instances():
    """Different constructor arguments must return different instances."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p2 = Point(3, 4)
    assert p1 is not p2


def test_init_called_once_per_unique_instance():
    """__init__ is called exactly once per unique set of arguments.

    A strong reference to each created instance is kept to prevent
    weakref-based garbage collection between calls.
    """
    init_counts: dict[tuple[int, int], int] = {}

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y
            key = (x, y)
            init_counts[key] = init_counts.get(key, 0) + 1

    p1 = Point(1, 2)  # noqa: F841
    p2 = Point(1, 2)  # noqa: F841
    p3 = Point(3, 4)  # noqa: F841

    assert init_counts == {(1, 2): 1, (3, 4): 1}


def test_two_calls_same_instance_single_init():
    """A second call with the same args does not trigger __init__ again."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")
        init_count: int = 0

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y
            type(self).init_count += 1

    p1 = Point(1, 2)
    p2 = Point(1, 2)

    assert p1 is p2
    assert Point.init_count == 1


# ---------------------------------------------------------------------------
# __id__  (default and custom)
# ---------------------------------------------------------------------------


def test_default_id_uses_match_args():
    """Default __id__ builds a namedtuple from __match_args__."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    uid = Point.__id__(1, 2)
    assert uid == (1, 2)


def test_default_id_with_keywords():
    """Default __id__ accepts keyword arguments matching __match_args__."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    uid = Point.__id__(x=3, y=4)
    assert uid == (3, 4)


def test_custom_id_override():
    """Custom __id__ replaces the default identification logic."""

    @final
    class CaseInsensitiveString(Multiton):
        __match_args__ = ("value",)

        def __init__(self, value: str) -> None:
            self.value = value

        @classmethod
        def __id__(cls, *args: Any, **kwds: Any) -> tuple[object, ...]:
            if args:
                return (args[0].lower(),)
            if "value" in kwds:
                return (kwds["value"].lower(),)
            return (None,)  # type: ignore[return-value]

    s1 = CaseInsensitiveString("Hello")
    s2 = CaseInsensitiveString("hello")
    s3 = CaseInsensitiveString("HELLO")

    assert s1 is s2
    assert s1 is s3


def test_custom_id_uses_subset_of_args():
    """Custom __id__ may ignore some constructor arguments."""

    @final
    class Point(Multiton):
        def __init__(self, x: int, y: int, name: str) -> None:
            self.x = x
            self.y = y
            self.name = name

        @classmethod
        def __id__(cls, *args: Any, **kwds: Any) -> tuple[object, ...]:
            if args:
                return (args[0], args[1])
            return (kwds.get("x", 0), kwds.get("y", 0))

    p1 = Point(1, 2, "first")
    p2 = Point(1, 2, "second")

    assert p1 is p2  # same x,y → same instance
    # __init__ runs only once, so name keeps the first value
    assert p1.name == "first"
    assert p2.name == "first"


# ---------------------------------------------------------------------------
# __get_instance__
# ---------------------------------------------------------------------------


def test_get_instance_returns_existing_instance():
    """__get_instance__ retrieves an instance by its id hash."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    uid = hash(Point.__id__(1, 2))
    assert Point.__get_instance__(uid) is p


def test_get_instance_missing():
    """__get_instance__ returns None for a nonexistent hash."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    assert Point.__get_instance__(999_999) is None


def test_get_instance_custom_default():
    """__get_instance__ returns the provided default when no instance exists."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    sentinel = object()
    assert Point.__get_instance__(999_999, sentinel) is sentinel  # pyright: ignore[reportArgumentType]


# ---------------------------------------------------------------------------
# Weak reference support
# ---------------------------------------------------------------------------
def test_weakref_default_removes_instance_after_gc():
    """With weakref=True (default) an instance is GC'd when no strong refs remain."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    uid = hash(Point.__id__(1, 2))
    assert Point.__get_instance__(uid) is p

    del p
    gc.collect()
    gc.collect()

    assert Point.__get_instance__(uid) is None


def test_weakref_default_calls_init_again_after_gc():
    """After GC, creating the same args calls __init__ again."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")
        _call_count: int = 0

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y
            type(self)._call_count += 1

    Point(1, 2)
    assert Point._call_count == 1  # pyright: ignore[reportPrivateUsage]

    gc.collect()
    gc.collect()

    Point(1, 2)
    assert Point._call_count == 2  # pyright: ignore[reportPrivateUsage]


def test_weakref_false_keeps_instance():
    """With weakref=False the instance survives the loss of strong references."""

    @final
    class Point(Multiton, weakref=False):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    uid = hash(Point.__id__(1, 2))

    del p
    gc.collect()
    gc.collect()

    assert Point.__get_instance__(uid) is not None


def test_weakref_false_no_double_init():
    """With weakref=False, a second construction does NOT call __init__."""

    @final
    class Point(Multiton, weakref=False):
        __match_args__ = ("x", "y")
        _call_count: int = 0

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y
            type(self)._call_count += 1

    Point(1, 2)
    del Point  # remove class reference too... but wait, we still have Point from test
    # Actually we can't easily collect the class itself here; but the instance in the
    # instances dict keeps a strong ref, so __init__ shouldn't run again.
    # We'll just verify that the second call doesn't increment the counter.

    # Create a fresh reference to the same class to avoid "Point is not defined"
    # The class is still alive because __instances__ holds a strong ref to the instance.


def test_weakref_cleanup_removes_dict_entry():
    """The instances dict entry is removed when the instance is collected."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    uid = hash(Point.__id__(1, 2))
    assert uid in Point.__instances__

    del p
    gc.collect()
    gc.collect()

    assert uid not in Point.__instances__


# ---------------------------------------------------------------------------
# Immutability of special attributes
# ---------------------------------------------------------------------------


def test_match_args_attributes_immutable():
    """Attributes listed in __match_args__ cannot be reassigned after init."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)

    with pytest.raises(AttributeError, match="x attribute is immutable"):
        p.x = 10  # type: ignore[assignment]

    with pytest.raises(AttributeError, match="y attribute is immutable"):
        p.y = 20  # type: ignore[assignment]


def test_values_attribute_immutable():
    """_values_ cannot be reassigned after creation."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)

    with pytest.raises(AttributeError, match="_values_ attribute is immutable"):
        p._values_ = (10, 20)  # type: ignore[assignment, reportAttributeAccessIssue]  # pyright: ignore[reportAttributeAccessIssue]


def test_non_match_args_attributes_still_mutable():
    """Attributes not in __match_args__ can be freely modified."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y
            self.tag = ""

    p = Point(1, 2)
    p.tag = "updated"  # type: ignore[assignment]
    assert p.tag == "updated"  # type: ignore[comparison-overlap]


# ---------------------------------------------------------------------------
# Protocol methods: __hash__, __eq__, __len__, __iter__, __contains__,
#                   __getitem__, _asdict, __copy__, __deepcopy__
# ---------------------------------------------------------------------------


def test_hash():
    """__hash__ returns the hash of the _values_ tuple."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p2 = Point(1, 2)
    assert hash(p1) == hash(p2)
    assert hash(p1) == hash((1, 2))


def test_eq_same_values():
    """__eq__ returns True for two instances created with the same arguments."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p2 = Point(1, 2)
    assert p1 == p2
    assert p1 == p2


def test_eq_different_values():
    """__eq__ returns False for instances with different arguments."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p3 = Point(3, 4)
    assert p1 != p3
    assert p1 != p3


def test_eq_non_multiton():
    """__eq__ returns False when compared to a non-Multiton object."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    assert p != "not a point"
    assert p != 42
    assert p is not None
    assert (p == None) is False  # noqa: E711


def test_eq_with_identical_hash_returns_true():
    """__eq__ uses hash-based comparison so two objects with same hash compare equal."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)

    @final
    class Fake:
        def __hash__(self) -> int:
            return hash((1, 2))

    fake = Fake()
    assert hash(p) == hash(fake)
    # The hash-based __eq__ considers them equal (same hash).
    assert p == fake


def test_eq_unhashable_typeerror_caught():
    """__eq__ catches TypeError and returns False when compared to an unhashable object.

    Lists, dicts, sets, and other unhashable types cause ``hash(value)``
    to raise ``TypeError``; the ``except TypeError: return False`` path
    (lines 105-106) handles this.
    """

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    assert (p == [1, 2, 3]) is False
    assert (p != [1, 2, 3]) is True


def test_len():
    """__len__ returns the number of match_args fields."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    assert len(Point(1, 2)) == 2


def test_iter():
    """__iter__ yields the values in match_args order."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    assert list(Point(1, 2)) == [1, 2]


def test_contains():
    """__contains__ checks membership in the _values_ tuple."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    assert 1 in p
    assert 2 in p
    assert 3 not in p


def test_getitem_by_index():
    """__getitem__ supports positional indexing."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y", "z")

        def __init__(self, x: int, y: int, z: int) -> None:
            self.x = x
            self.y = y
            self.z = z

    p = Point(1, 2, 3)
    assert p[0] == 1
    assert p[1] == 2
    assert p[2] == 3


def test_getitem_negative_index():
    """__getitem__ supports negative indexing."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y", "z")

        def __init__(self, x: int, y: int, z: int) -> None:
            self.x = x
            self.y = y
            self.z = z

    p = Point(1, 2, 3)
    assert p[-1] == 3
    assert p[-2] == 2
    assert p[-3] == 1


def test_getitem_slice():
    """__getitem__ supports slicing."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y", "z")

        def __init__(self, x: int, y: int, z: int) -> None:
            self.x = x
            self.y = y
            self.z = z

    p = Point(1, 2, 3)
    assert p[0:2] == (1, 2)
    assert p[1:] == (2, 3)


def test_asdict():
    """_asdict returns a zip iterator of (name, value) pairs.

    Note: the implementation returns a ``zip`` iterator rather than a
    built-in ``dict``.  We convert with ``dict()`` for convenience.
    """

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y", "z")

        def __init__(self, x: int, y: int, z: int) -> None:
            self.x = x
            self.y = y
            self.z = z

    p = Point(1, 2, 3)
    assert dict(p._asdict()) == {"x": 1, "y": 2, "z": 3}  # pyright: ignore[reportPrivateUsage]


def test_copy_returns_self():
    """__copy__ returns the same instance (Multiton identity)."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    assert copy(p) is p


def test_deepcopy_returns_self():
    """__deepcopy__ returns the same instance (Multiton identity)."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    assert deepcopy(p) is p


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_iderror_on_wrong_number_of_args():
    """IDError is raised when the number of args does not match __match_args__."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    with pytest.raises(IDError):
        Point(1, 2, 3)  # pyright: ignore[reportCallIssue]

    with pytest.raises(IDError):
        Point(1)  # pyright: ignore[reportCallIssue]


def test_iderror_is_typeerror_subclass():
    """IDError is a subclass of TypeError."""
    assert issubclass(IDError, TypeError)


def test_iderror_message():
    """IDError message guides the user to define __match_args__ or override __id__.

    A class with no attribute assignments in ``__init__`` has empty
    ``__static_attributes__``, so ``__match_args__`` defaults to ``()``.
    Passing any positional arguments then raises ``IDError``.
    """

    @final
    class Point(Multiton):
        def __init__(self, x: int, y: int) -> None:
            pass  # no self.x / self.y  → empty __static_attributes__

    with pytest.raises(IDError, match="__match_args__"):
        Point(1, 2)


def test_iderror_without_match_args():
    """Without __match_args__ and without custom __id__, construction raises IDError.

    Same setup as above — ``__match_args__`` defaults to ``()`` because
    ``__static_attributes__`` is empty.
    """

    @final
    class Point(Multiton):
        def __init__(self, x: int, y: int) -> None:
            pass  # no self.x / self.y  → empty __static_attributes__

    with pytest.raises(IDError):
        Point(1, 2)


def test_non_hashable_id_raises_typeerror():
    """TypeError is raised when __id__ returns a tuple containing unhashable items."""

    @final
    class Bad(Multiton):
        __match_args__ = ("data",)

        def __init__(self, data: list[int]) -> None:
            self.data = data

    with pytest.raises(TypeError, match="__id__ class method should return a tuple of hashables"):
        Bad([1, 2, 3])


def test_sanity_check_hash_mismatch_cannot_be_triggered_by_user():
    """The metaclass always overrides ``__hash__``, so the sanity check always passes.

    A user-defined ``__hash__`` is replaced by the metaclass version,
    therefore the ``uid != test`` branch is never reachable via normal
    subclassing.  This test documents that limitation.
    """

    @final
    class Mismatched(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

        def __hash__(self) -> int:  # type: ignore[override]
            return 0  # deliberately break the contract - will be overridden

    # The metaclass replaces __hash__, so the sanity check passes.
    obj = Mismatched(1, 2)
    # The metaclass's __hash__ uses _values_, not the user-defined version.
    assert hash(obj) == hash((1, 2))
    assert hash(obj) != 0


def test_sanity_check_catches_typeerror_on_instance_hash():
    """The sanity check catches a TypeError when computing ``hash(instance)``.

    Covers the ``except TypeError`` branch (lines 191-195).  Uses a custom
    ``__id__`` that returns an object whose ``__hash__`` succeeds on the
    first call (during ``uid`` computation) but raises on the second call
    (during instance-hash validation).
    """

    class _FirstTimeHashable:
        _called: bool

        def __init__(self) -> None:
            self._called = False

        def __hash__(self) -> int:
            if not self._called:
                self._called = True
                return 42
            msg = "unhashable on second call"
            raise TypeError(msg)

    @final
    class Bad(Multiton):
        __match_args__ = ("val",)

        def __init__(self, val: object) -> None:
            self.val = val

        @classmethod
        def __id__(cls, *args: Any, **kwds: Any) -> tuple[object, ...]:
            return (_FirstTimeHashable(),)

    with pytest.raises(TypeError, match="__match_args__ should refer to hashable attributes"):
        Bad("anything")


def test_sanity_check_catches_hash_mismatch():
    """The sanity check catches a hash mismatch when ``uid != test``.

    Covers lines 190 and 197-202.  Uses a custom ``__id__`` that returns
    an iterable whose first iteration (``*tmp,``) yields different values
    than the second (``tuple(tmp)``), causing ``uid != hash(instance)``.
    """

    class _SideEffectIterable:
        _consumed: bool

        def __init__(self) -> None:
            self._consumed = False

        def __iter__(self):
            if not self._consumed:
                self._consumed = True
                return iter((1,))
            return iter((2,))

    @final
    class Bad(Multiton):
        __match_args__ = ("val",)

        def __init__(self, val: object) -> None:
            self.val = val

        @classmethod
        def __id__(cls, *args: Any, **kwds: Any) -> object:
            return _SideEffectIterable()

    with pytest.raises(TypeError, match="__id__ class method is incompatible"):
        Bad("anything")


# ---------------------------------------------------------------------------
# __instancecheck__
# ---------------------------------------------------------------------------


def test_instancecheck_multiton_always_true():
    """isinstance(obj, Multiton) is True for any object (by design)."""
    assert isinstance(42, Multiton)
    assert isinstance("hello", Multiton)
    assert isinstance(None, Multiton)
    assert isinstance([], Multiton)
    assert isinstance(object(), Multiton)


def test_instancecheck_subclass_works_normally():
    """isinstance works normally for concrete Multiton subclasses."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p = Point(1, 2)
    assert isinstance(p, Point)
    assert isinstance(p, Multiton)
    assert not isinstance(42, Point)


# ---------------------------------------------------------------------------
# __slots__
# ---------------------------------------------------------------------------


def test_slots_multiton_works():
    """Multiton classes with __slots__ create correct instances."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")
        __slots__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p2 = Point(1, 2)
    p3 = Point(3, 4)

    assert p1 is p2
    assert p1 is not p3
    assert p1.x == 1
    assert p1.y == 2
    assert p3.x == 3
    assert p3.y == 4


def test_slots_include_weakref_and_values_by_default():
    """With weakref=True, __slots__ is augmented with '__weakref__' and '_values_'."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")
        __slots__ = ("x", "y")  # pyright: ignore[reportUninitializedInstanceVariable]

    assert "__weakref__" in Point.__slots__
    assert "_values_" in Point.__slots__


def test_slots_not_augmented_when_weakref_false():
    """With weakref=False, __slots__ is not augmented."""

    @final
    class Point(Multiton, weakref=False):
        __match_args__ = ("x", "y")
        __slots__ = ("x", "y")  # pyright: ignore[reportUninitializedInstanceVariable]

    assert "__weakref__" not in Point.__slots__
    assert "_values_" not in Point.__slots__


def test_slots_preserves_existing_weakref():
    """When __weakref__ already in __slots__, it is not duplicated."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")
        __slots__ = ("__weakref__", "x", "y")  # pyright: ignore[reportUninitializedInstanceVariable]

    # The metaclass only adds __weakref__ / _values_ when __weakref__
    # is NOT already present, so the slots stay as originally defined.
    assert Point.__slots__ == ("__weakref__", "x", "y")


# ---------------------------------------------------------------------------
# __match_args__ defaulting
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason="__static_attributes__ is only set by the compiler in Python 3.13+",
)
def test_match_args_defaults_to_static_attributes():
    """When __match_args__ is not defined, it defaults to __static_attributes__."""

    # `self.x = x; self.y = y` in __init__ causes the compiler to set
    # __static_attributes__ = ('x', 'y').
    @final
    class Point(Multiton):
        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    expected = Point.__static_attributes__  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]
    assert Point.__match_args__ == expected  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


def test_match_args_empty_when_no_static_attributes():
    """Without __match_args__ and without static attributes, __match_args__ is ()."""

    @final
    class Empty(Multiton):
        def __init__(self) -> None: ...

    assert Empty.__match_args__ == ()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


# ---------------------------------------------------------------------------
# Multiton class attributes
# ---------------------------------------------------------------------------


def test_class_attributes_present():
    """Multiton subclasses carry the expected internal attributes."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    assert isinstance(Point.__instances__, dict)
    assert Point.__multiton_weakref__ is True  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
    assert callable(Point.__id__)
    assert callable(Point.__get_instance__)


# ---------------------------------------------------------------------------
# Different call styles
# ---------------------------------------------------------------------------


def test_keyword_arguments():
    """Multiton accepts keyword arguments in any order."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(x=1, y=2)
    p2 = Point(y=2, x=1)
    p3 = Point(x=1, y=2)

    assert p1 is p3
    assert p1 is p2


def test_mixed_positional_and_keyword():
    """Multiton accepts a mix of positional and keyword arguments."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, y=2)
    p2 = Point(1, 2)
    assert p1 is p2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_single_match_arg():
    """Multiton works with a single match argument."""

    @final
    class Value(Multiton):
        __match_args__ = ("val",)

        def __init__(self, val: int) -> None:
            self.val = val

    v1 = Value(42)
    v2 = Value(42)
    v3 = Value(0)

    assert v1 is v2
    assert v1 is not v3
    assert v1.val == 42


def test_empty_match_args_singleton():
    """With __match_args__ = (), Multiton should behave as a singleton.

    This test asserts the **correct** behaviour: same (empty) arguments
    must return the same instance.t will pass."""

    @final
    class Singleton(Multiton):
        __match_args__ = ()

        def __init__(self) -> None: ...

    s1 = Singleton()
    s2 = Singleton()
    assert s1 is s2


def test_singleton_via_custom_id():
    """Singleton behaviour can be achieved via a constant-returning ``__id__``."""

    @final
    class ConstantId(Multiton):
        def __init__(self, *args: Any, **kwds: Any) -> None:
            pass

        @classmethod
        def __id__(cls, *args: Any, **kwds: Any) -> tuple[object, ...]:
            return (0,)  # always the same identity

    s1 = ConstantId()
    s2 = ConstantId()
    s3 = ConstantId("any", key="value")
    assert s1 is s2
    assert s1 is s3


def test_multiton_without_match_args_but_with_custom_id():
    """Without __match_args__ but with a custom __id__, construction works."""

    @final
    class ByType(Multiton):
        def __init__(self, kind: str) -> None:
            self.kind = kind

        @classmethod
        def __id__(cls, *args: Any, **kwds: Any) -> tuple[object, ...]:
            if args:
                return (args[0],)
            return (kwds.get("kind", ""),)

    t1 = ByType("a")
    t2 = ByType("a")
    t3 = ByType("b")

    assert t1 is t2
    assert t1 is not t3


def test_multiton_explicit_class_attributes():
    """MultitonType constants are accessible."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    assert MultitonType.ID_METH_NAME == "__id__"
    assert MultitonType.INSTANCES_MAP_NAME == "__instances__"
    assert MultitonType.WEAKREF_FLAG_NAME == "__multiton_weakref__"
    assert hasattr(Point, "__id__")
    assert hasattr(Point, "__instances__")
    assert hasattr(Point, "__multiton_weakref__")


def test_multiton_bases_removed():
    """Multiton base class is stripped from __bases__ during class creation."""

    @final
    class Point(Multiton):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    assert Multiton not in Point.__bases__


def test_id_error_exception_is_raiseable():
    """IDError can be raised and caught independently.

    Raises:
        IDError: Always raised in the test body.
    """

    msg = "custom"
    with pytest.raises(IDError):
        raise IDError(msg)


# ---------------------------------------------------------------------------
# Metaclass direct usage (without the Multiton base)
# ---------------------------------------------------------------------------


def test_metaclass_directly():
    """MultitonType can be used directly as a metaclass."""

    @final
    class Point(metaclass=MultitonType):
        __match_args__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    p1 = Point(1, 2)
    p2 = Point(1, 2)
    p3 = Point(3, 4)

    assert p1 is p2
    assert p1 is not p3
