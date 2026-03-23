from __future__ import annotations

from cpython.object cimport PyObject
from cpython.set cimport *
from cpython.ref cimport *
from cpython.dict cimport PyDict_Contains, PyDict_SetItem, PyDict_GetItem
cimport cython

import sys
from types import ModuleType
from typing import TYPE_CHECKING, Any, ClassVar, Never, final, Protocol


cdef extern from "Python.h":
    tuple PyTuple_New(Py_ssize_t len)
    Py_ssize_t PyTuple_GET_SIZE(object  p)
    PyObject* PyTuple_GET_ITEM(object  p, Py_ssize_t pos)
    void PyTuple_SET_ITEM(object p, Py_ssize_t pos, PyObject* o)


class _UnsetMeta(type):
    # NOTE: about unsupported cython metaclass
    # see: https://stackoverflow.com/questions/76501632/creating-a-metaclass-in-cython
    def __delattr__(cls, name: str, /) -> None:
        msg = f"cannot delete '{name}' attribute of immutable type '{cls.__name__}'"
        raise TypeError(msg)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        msg = f"cannot set '{name}' attribute of immutable type '{cls.__name__}'"
        raise TypeError(msg)


Unset: UnsetType


@final
class UnsetType(type, metaclass=_UnsetMeta):
    """The type of the Unset singleton.

    The `Unset` singleton is design to act as a sentinel type that
    could be assigned to any type and mimic as far as possible `None`.

    Example:
        foo: str = None  # static type checker normally complain
        bar: str = Unset  # should be valid for static type checker
        assert not isinstance(bar, str)

        assert not None
        assert not Unset
        assert UnsetType() is Unset
    """
    def __new__(cls, *args: Any, **kwds: Any) -> UnsetType:
        global Unset

        if args:
            msg = "UnsetType takes no arguments"
            raise TypeError(msg)

        if not hasattr(sys.modules[__name__], "Unset"):
            Unset = type.__new__(
                UnsetType, "Unset", (), {"__doc__": UnsetType.__doc__, "__slots__": ()}
            )
        return Unset
        # if not hasattr(sys.modules[__name__], "__"):
        #     sys.modules[__name__].__ = type.__new__(
        #         UnsetType, "Unset", (), {"__doc__": UnsetType.__doc__, "__slots__": ()}
        #     )
        # return sys.modules[__name__].__

    def __init__(cls, *args: Any, **kwds: Any) -> None: ...

    def __init_subclass__(cls) -> None:
        msg = "type 'UnsetType' is not an acceptable base type"
        raise TypeError(msg)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        msg = f"cannot set '{name}' attribute of immutable type 'UnsetType'"
        raise TypeError(msg)

    def __delattr__(cls, name: str, /) -> None:
        msg = f"cannot delete '{name}' attribute of immutable type 'UnsetType'"
        raise TypeError(msg)

    def __bool__(cls) -> bool:
        return False

    def __call__(cls) -> Never:
        msg = "'UnsetType' object is not callable"
        raise TypeError(msg)

    def __repr__(cls) -> str:
        return "Unset"

    __hash__ = None  # pyright: ignore[reportAssignmentType]


Unset = UnsetType()
"""The `Unset` singleton is design to act as a sentinel type that
could be assigned to any type and mimic as far as possible `None`."""
cdef PyObject* UNSET_PTR = <PyObject*> Unset

##
#
#
cdef class _readonly:
    cdef object name
    cdef Py_ssize_t index

    def __cinit__(self, object name, Py_ssize_t index):
        self.name = name
        self.index = index

    def __set__(self, object instance, object value):
        cdef _Frozen frozen = <_Frozen> instance
        if PyTuple_GET_ITEM(frozen.frozen_tp, self.index) is not NULL:
            raise AttributeError(f"{self.name} attribute is immutable")

        cdef PyObject* value_ptr = <PyObject*> value
        if value_ptr == UNSET_PTR:
            return

        Py_INCREF(value)
        PyTuple_SET_ITEM(frozen.frozen_tp, self.index, value_ptr)

    def __get__(self, object instance, object owner):
        if instance is None:
            return self

        cdef _Frozen frozen = <_Frozen> instance
        cdef PyObject* value = PyTuple_GET_ITEM(frozen.frozen_tp, self.index)
        if value is NULL:
            return Unset
        return <object> value

    def __delete__(self, object instance) -> None:
        msg = f"{self.name} attribute is immutable"
        raise TypeError(msg)


@cython.collection_type("sequence")
cdef class _Frozen:
    __frozen__: ClassVar[tuple[str, ...]] = ()
    cdef tuple frozen_tp
    cdef Py_ssize_t size

    def __cinit__(self):
        self.size = PyTuple_GET_SIZE(<tuple> self.__class__.__frozen__)
        self.frozen_tp = PyTuple_New(self.size)

    @staticmethod
    def __cinit_subclass__(subclass):
        cdef list tmp
        cdef Py_ssize_t idx

        tmp = []
        # merge frozen attributes from bases classes preserving order
        for cls in getattr(subclass, "__bases__", ()):
            if issubclass(cls, _Frozen):
                for name in cls.__frozen__:
                    if name not in tmp:
                        tmp.append(name)

        # Update subclass __frozen__ with inherited fields
        subclass.__frozen__ = (
            *tmp,
            *(name for name in subclass.__frozen__ if name not in tmp),
        )

        # NOTE: we need to create all descriptors even for inherited fields
        # otherwise super class descriptor pointers will overlap and we'll
        # segfaull.
        for idx, name in enumerate(subclass.__frozen__):
            setattr(subclass, name, _readonly(name, idx))

    def __iter__(self):
        cdef Py_ssize_t i
        cdef PyObject* value
        for i in range(self.size):
            value = PyTuple_GET_ITEM(self.frozen_tp, i)
            yield <object> value if value is not NULL else Unset

    def __contains__(self, value):
        return value in iter(self)

    def __getitem__(self, index):
        cdef int i = int(index)

        i = self.size + i if i < 0 else i
        if i < 0 or i >= self.size:
            raise IndexError("index out of range")

        cdef PyObject* value = PyTuple_GET_ITEM(self.frozen_tp, i)
        if value is NULL:
            return Unset
        return <object> value

    def __len__(self):
        return self.size

    def count(self, value):
        return tuple(self).index(value)

    def index(self, value, start=0, stop=None):
        return tuple(self).index(value, start, stop)

    def as_dict(self):
        return dict(zip(self.__frozen__, tuple(self)))

    def __hash__(self) -> int:
        if Unset in self:
            unset = tuple(k for k in self.__frozen__ if getattr(self, k) is Unset)
            msg = f"unhashable {self.__class__.__name__}: {unset} attribute(s) still undefined"
            raise TypeError(msg)
        return hash(tuple(self))

    def __eq__(self, value: object, /) -> bool:
        try:
            return tuple(self) == tuple(value)
        except TypeError:
            return False

    def __reduce__(self):
        return (
            self.__class__.__new__,
            (self.__class__,),
            tuple(self),
        )

    def __setstate__(self, object values):
        if not isinstance(values, tuple):
            return
        for k, v in zip(self.__frozen__, values):
            setattr(self, k, v)

    def __repr__(self) -> str:
        inner = ", ".join("=".join((k, str(getattr(self, k, Unset)))) for k in self.__frozen__)
        return f"{self.__class__.__name__}({inner})"


class FrozenProtocol(Protocol):
    __frozen__: ClassVar[tuple[str, ...]]


class Frozen(FrozenProtocol, _Frozen):
    def __init_subclass__(cls, **kwds: Any) -> None:
        _Frozen.__cinit_subclass__(cls)

    def __hash__(self) -> int:
        return _Frozen.__hash__(self)

    def __eq__(self, value: object, /) -> bool:
        return _Frozen.__eq__(self, value)
##
#
class _FrozenModule(ModuleType):
    def __delattr__(self, name: str, /) -> None:
        msg = f"cannot delete '{name}'"
        raise SyntaxError(msg)

    def __setattr__(self, name: str, value: Any, /) -> None:
        msg = f"cannot assign to '{name}'"
        raise SyntaxError(msg)


sys.modules[__name__].__class__ = _FrozenModule
