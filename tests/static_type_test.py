from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

import pytest
from deluxe.types import StaticType


class A: ...


class B: ...


class Slotted:
    __slots__: set[str] = {"x"}


class NakedBorrow(metaclass=StaticType): ...


class ProtocolBorrow(Protocol, metaclass=StaticType): ...


class AbstractBorrow(ABC, metaclass=StaticType):
    @abstractmethod
    def abstract(self): ...


def test_multiple_bases():
    with pytest.raises(TypeError):

        class _(A, B, metaclass=StaticType): ...


def test_naked_protocol():
    assert getattr(ProtocolBorrow, "_is_protocol")


def test_from_protocol():
    class _(ProtocolBorrow): ...

    assert not getattr(_, "_is_protocol")
    assert _.__orig_bases__ == (Protocol, ProtocolBorrow)


def test_protocol_to_abc():
    class _(ProtocolBorrow, ABC): ...

    assert not getattr(_, "_is_protocol")
    assert _.__orig_bases__ == (Protocol, ProtocolBorrow)

    class _(ABC, ProtocolBorrow): ...

    assert not getattr(_, "_is_protocol")
    assert _.__orig_bases__ == (Protocol, ProtocolBorrow)


def test_protocol_to_protocol():
    class _(ProtocolBorrow, Protocol): ...

    assert getattr(_, "_is_protocol")
    assert _.__orig_bases__ == (Protocol, ProtocolBorrow)

    class _(Protocol, ProtocolBorrow): ...  # pyright: ignore[reportGeneralTypeIssues]

    assert getattr(_, "_is_protocol")
    assert _.__orig_bases__ == (Protocol, ProtocolBorrow)


def test_protocol_from_concret():
    with pytest.raises(TypeError):

        class _(A, Protocol, metaclass=StaticType): ...  # pyright: ignore[reportGeneralTypeIssues]  # noqa: PYI046


def test_protocol_from_concret_borrow():
    with pytest.raises(TypeError):

        class _(NakedBorrow, Protocol): ...  # pyright: ignore[reportGeneralTypeIssues]  # noqa: PYI046


def test_from_concret_to_abc():
    class _(A, ABC, metaclass=StaticType): ...

    assert hasattr(_, "__abstractmethods__")
    assert _.__orig_bases__ == (ABC, A)

    class _(ABC, A, metaclass=StaticType): ...

    assert hasattr(_, "__abstractmethods__")
    assert _.__orig_bases__ == (ABC, A)


def test_from_borrow_to_abc():
    class _(NakedBorrow, ABC): ...

    assert hasattr(_, "__abstractmethods__")


def test_protocol_no_instance():
    with pytest.raises(TypeError):
        ProtocolBorrow()  # pyright: ignore[reportAbstractUsage]

    class _(ProtocolBorrow, Protocol): ...

    with pytest.raises(TypeError):
        _()  # pyright: ignore[reportAbstractUsage]


def test_abstract_no_instance():
    with pytest.raises(TypeError):
        AbstractBorrow()  # pyright: ignore[reportAbstractUsage]

    class _(AbstractBorrow, ABC): ...

    with pytest.raises(TypeError):
        _()  # pyright: ignore[reportAbstractUsage]


def test_abstract_to_concret():
    class _(AbstractBorrow):
        def abstract(self):  # noqa: PLR6301
            return

    assert not _.__abstractmethods__
    assert _().abstract() is None


def test_slots_merge():
    class _(Slotted, metaclass=StaticType):
        __slots__: set[str] = {"y"}

    assert _.__slots__ == {"x", "y"}
