"""Functional programming utilities and monadic types.

This module provides functional programming constructs including monads,
lazy evaluation, and caching utilities. It implements the monad pattern
for composing computations in a functional style, with support for
chaining operations and deferred evaluation.

Examples:
    Using :class:`Maybe` for optional value handling::

        from deluxe.functional import Maybe

        def parse_int(value: str) -> Maybe[int]:
            try:
                return Maybe.pure(int(value))
            except ValueError:
                return Maybe()

        result = parse_int("42")
        match result:
            case Maybe(value):
                print(f"Parsed: {value}")
            case _:
                print("Invalid input")

    Using :class:`Lazy` for deferred computation::

        from deluxe.functional import Lazy

        def expensive_computation() -> int:
            print("Computing...")
            return 42

        # Computation not executed yet
        lazy_value = Lazy(expensive_computation, int)

        # Computation executed here
        result = lazy_value.unwrap()  # Prints "Computing..."

    Using :class:`MaybeCallable` with enumerations::

        from enum import Enum, member
        from deluxe.functional import MaybeCallable

        class Key(MaybeCallable[bytes]):
            def __call__(self, *args: bytes) -> bytes:
                return self._callable_(*args)

        class KeyStroke(Key[bytes], Enum):
            @member
            @staticmethod
            def Ctrl(key: bytes) -> str:
                return f"C-{key.decode()}"

            Space = b"Space"

See Also:
    - :mod:`deluxe.types`: Additional type utilities.
    - :mod:`deluxe.enums`: Enhanced enumeration support.
"""

from __future__ import annotations

from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Never,
    Protocol,
    Self,
    TypeVar,
    cast,
    no_type_check,
    overload,
    runtime_checkable,
)

from deluxe.types import Unset


if TYPE_CHECKING:
    from collections.abc import Callable


__all__ = ("Lazy", "Maybe", "MaybeCallable", "Monad", "cached_property")


_T_co = TypeVar("_T_co", covariant=True)


# NOTE: based on the code from Python 3.14: https://github.com/python/cpython/blob/
# 5507eff19c757a908a2ff29dfe423e35595fda00/Lib/functools.py#L1089-L1138
# Copyright (C) 2006 Python Software Foundation.
# vendored under the PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
#
# Prior to Python 3.12 cached_property used threading.Lock,
# which makes it very slow.
class cached_property(Generic[_T_co]):  # noqa: N801
    """Similar to property(), with the addition of caching.

    Transform a method of a class into a property whose value is computed
    once and then cached as a normal attribute for the life of the instance.
    Useful for expensive computed properties of instances that are otherwise
    effectively immutable.

    Keys Differences from `functools.cached_property`:

    * support pure python class as well as `mypyc` compiled Native
      and Non-Native extension class.
    * prevent reset or deletion of the property on the instance
    * allow usage in class with or without writable __dict__ (eg., class
      with __slots__)
    """

    def __init__(self, func: Callable[[Any], _T_co]) -> None:
        self.__cache__: dict[int, Any] = {}
        self.func: Callable[[Any], _T_co] = func
        self.__doc__: str = func.__doc__ or ""
        self.attrname: str
        self.__objclass__: type[Any]
        self.__module__: str

    def __set_name__(self, owner: type[Any], name: str) -> None:
        # NOTE: with mypyc Native extension class, __set_name__
        # will never be called, but as the implicit name of
        # the property is the func.__name__, we could set it latter
        # in the __get__ method body
        if not hasattr(self, "attrname"):
            self.attrname = name
        elif name != self.attrname:
            msg = (
                "Cannot assign the same cached_property to two different names "
                f"({self.attrname!r} and {name!r})."
            )
            raise TypeError(msg)
        self.__objclass__ = owner
        self.__module__ = owner.__module__

    @overload
    def __get__(self, instance: None, owner: type[Any]) -> Self: ...
    @overload
    def __get__(self, instance: object, owner: type[Any]) -> _T_co: ...
    def __get__(self, instance: object | None, owner: type[Any]) -> _T_co | Self:
        if instance is None:
            return self

        if not hasattr(self, "attrname"):
            self.__set_name__(owner, self.func.__name__)

        key: int = id(instance)
        if (val := self.__cache__.get(key, Unset)) is Unset:
            val = self.func(instance)
            self.__cache__[key] = val
        return val

    def __set__(self, instance: Any, value: object) -> Never:
        msg = f"property of '{object.__class__.__name__}' object has no setter"
        raise AttributeError(msg)

    def __delete__(self, instance: Any) -> Never:
        msg = f"property of '{object.__class__.__name__}' object has no deleter"
        raise AttributeError(msg)


_T = TypeVar("_T")
_U = TypeVar("_U")


@runtime_checkable
class Monad(Protocol[_T]):  # pragma: no cover
    """Protocol defining the interface for monadic types.

    A monad is a design pattern from functional programming that provides a way
    to structure computations. It defines a standard interface for values that can
    be "wrapped" in a context, enabling consistent handling of computations that
    might involve side effects, error handling, or delayed evaluation.

    The protocol requires implementations to provide methods for wrapping values in
    the monadic context (:meth:`pure`), transforming wrapped values
    (:meth:`map`), and chaining computations that produce monadic results
    (:meth:`bind`).

    Examples:
        Basic usage with the :class:`Lazy` implementation::

            from deluxe.functional import Lazy

            # Wrap a value using pure
            lazy_value = Lazy.pure(42)

            # Transform the value using map
            lazy_doubled = lazy_value.map(lambda x: x * 2)
            print(lazy_doubled.unwrap())  # 84

            # Chain computations using bind
            def to_lazy(x: int) -> Lazy[str]:
                return Lazy.pure(str(x))

            lazy_string = lazy_value.bind(to_lazy)
            print(lazy_string.unwrap())  # "42"

    Protocol Methods:
        :meth:`pure`: Wrap a plain value in the monadic context.
        :meth:`map`: Apply a function to the wrapped value (functorial map).
        :meth:`bind`: Chain a function that returns cast(_OST, a monadic value.)
        :meth:`join`: Flatten a monad of monads into a single monad.
        :meth:`unwrap`: Extract the wrapped value from the monadic context.
        :meth:`__call__`: Alias for :meth:`unwrap`, allowing monads to be called.

    Type Parameters:
        _T: The type of the value wrapped in the monadic context.

    See Also:
        - :class:`Lazy`: A concrete implementation of the :class:`Monad` protocol for
            lazy evaluation.
        - :class:`deluxe.environ.evar`
    """

    # __hash__: ClassVar[None] = None

    @classmethod
    def pure(cls, value: _T) -> Self:
        """Wrap a plain value into the monadic context.

        This is a class method that creates a new monadic instance containing
        the given plain value. This is the primary way to enter the monadic
        context from a non-monadic value.

        Args:
            value: The plain value to wrap in the monadic context.

        Returns:
            A monadic instance of the same type as ``cls`` containing the
            wrapped ``value``.
        """
        ...

    def map(self, func: Callable[[_T], _U], *args: Any, **kwds: Any) -> Monad[_U]:
        """Apply a function to the wrapped value (functorial map).

        This method transforms the value inside the monadic context by applying
        the given function. It preserves the monadic structure, returning a new
        monad containing the transformed value.

        The ``map`` method implements the functor pattern, which is typically
        derived from :meth:`bind` and :meth:`pure` in functional programming
        theory.

        Args:
            func: A function that takes a value of type ``_T`` and returns a
                value of type ``_U``.
            *args: Additional positional arguments to pass to ``func``.
            **kwds: Additional keyword arguments to pass to ``func``.

        Returns:
            A monadic instance of type ``Monad[_U]`` containing the result
            of applying ``func`` to the wrapped value.
        """
        ...

    def bind(self, func: Callable[[_T], Monad[_U]], *args: Any, **kwds: Any) -> Monad[_U]:
        """Chain a function that returns a monadic value.

        This method allows for chaining computations that produce monadic results.
        It applies the function to the wrapped value, which itself returns a monad,
        and then flattens the result to avoid nested monads.

        The ``bind`` operation (also known as ``flatMap`` or ``>>=`` in other
        languages) is the fundamental operation that gives monads their power
        for sequencing computations.

        Args:
            func: A function that takes a value of type ``_T`` and returns a
                monadic value of type ``Monad[_U]``.
            *args: Additional positional arguments to pass to ``func``.
            **kwds: Additional keyword arguments to pass to ``func``.

        Returns:
            A monadic instance of type ``Monad[_U]`` containing the result
            of applying ``func`` to the wrapped value, with the nested monadic
            structure flattened.
        """
        ...

    def join(self) -> Self:
        """Flatten a monad of monads into a single monad.

        This method unwraps one level of monadic structure, which is useful
        when dealing with nested monadic contexts. For monads wrapping other
        monads of the same type, ``join`` provides a way to reduce the
        nesting level.

        The ``join`` operation is related to ``bind`` and is defined as:
        ``m.join() == m.bind(lambda x: x)``.

        Returns:
            A monadic instance with one level of nesting removed.
        """
        ...

    def unwrap(self) -> _T:
        """Extract the wrapped value from the monadic context.

        This method returns the plain value contained within the monadic structure.
        This operation is sometimes called ``run`` or ``value`` in other monad
        implementations.

        Note that not all monads support this operation, as some monadic
        contexts (like IO monads) are meant to remain encapsulated to maintain
        referential transparency.

        Returns:
            The plain value of type ``_T`` that was wrapped in the monadic
            context.
        """
        ...

    def __call__(self) -> _T:
        """Alias for :meth:`unwrap`, allowing monads to be called as functions.

        This method enables syntactic sugar by allowing monadic instances to be
        called directly to extract their wrapped value, rather than explicitly
        calling :meth:`unwrap`.

        Returns:
            The plain value of type ``_T`` that was wrapped in the monadic
            context.
        """
        ...


class Maybe(Generic[_T]):
    """Maybe class.

    Usage
    -----

    .. code-block:: python
        import deluxe.types as types

        def parse_int(value: str) -> Maybe[int]:
            try:
                return Maybe(int(value))
            except ValueError:
                return Maybe()


        def is_positive(value: int) -> Maybe[int]:
            return Maybe(value) if value > 0 else Maybe()


        def process(value: str) -> Maybe[int]:
            result = Maybe(value).bind(parse_int)
            result = result.bind(lambda n: Maybe(2 * n))
            return result

        result = process("4")
        match result:
            case Maybe(types.Unset):
                print("error")
            case Maybe(8):
                print("eight")
            case Maybe(other):
                print("value:", other)

    Note:
        For pattern matching against :class:`deluxe.types.Unset` you can't use
        `Maybe(Unset)`, this won't work at runtime nor statically with typechecker.
        You should instead import the :py:mod:`deluxe.types` module and use
        `Maybe(types.Unset)`.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("__objclass__", "_name_", "_type", "_value")
    __hash__: ClassVar[None] = None  # pyright: ignore[reportIncompatibleMethodOverride]
    __match_args__ = ("_value",)  # pyright: ignore[reportUnannotatedClassAttribute]

    def __init__(self, value: _T = Unset) -> None:
        self._value: _T = value
        self._type: type[_T] = type(self._value)
        self._name_: str = Unset
        self.__objclass__: type = Unset

    def __set_name__(self, owner: type, name: str) -> None:
        self.__objclass__ = owner
        self._name_ = name

    @property
    def type(self) -> type[_T]:
        return self._type

    @classmethod
    def pure(cls, value: _T) -> Self:
        if value is Unset:
            msg = "Invalid 'Unset' value"
            raise ValueError(msg)
        return cls(value)

    def map(self, func: Callable[[_T], _U], *_args: Any, **_kwds: Any) -> Maybe[_U]:
        if self._value is Unset:
            return cast("Maybe[_U]", Maybe())
        return Maybe(func(self._value))

    def bind(self, func: Callable[[_T], Maybe[_U]], *_args: Any, **_kwds: Any) -> Maybe[_U]:
        if self._value is Unset:
            return cast("Maybe[_U]", Maybe())
        return func(self._value)

    def join(self) -> Self:
        return self.pure(self.unwrap())

    def unwrap(self) -> _T:
        return self._value

    def __call__(self) -> _T:
        return self.unwrap()

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}[{self._type.__name__}]({self._value})"


##
# NOTE: https://blog.ploeh.dk/2022/05/30/the-lazy-monad/
class Lazy(Generic[_T]):
    """Implementation of the :class:`Monad` protocol for lazy evaluation.

    The :class:`Lazy` class wraps a callable that defers computation until explicitly
    requested. This enables lazy evaluation, where computations are only performed
    when their results are needed, and results are cached across multiple accesses.

    The :meth:`__set_name__` method is present solely to allow usage of :class:`Lazy`
    as enumeration's member in :class:`deluxe.enums.Enum`.

    Examples:
        Creating a lazy value from a callable::

            from deluxe.functional import Lazy

            def expensive_computation() -> int:
                print("Computing...")
                return 42

            lazy_value = Lazy(expensive_computation, int)
            # Nothing printed yet - computation not executed

            result = lazy_value.unwrap()  # Prints "Computing..."
            # result is now 42

            result2 = lazy_value.unwrap()  # Prints again - result is not cached

        Using :meth:`pure` to wrap static values::

            from deluxe.functional import Lazy

            lazy_int = Lazy.pure(42)
            print(lazy_int.unwrap())  # 42

        Chaining transformations with :meth:`map`::

            from deluxe.functional import Lazy

            lazy_value = Lazy.pure(5)
            lazy_doubled = lazy_value.map(lambda x: x * 2, int)
            lazy_squared = lazy_doubled.map(lambda x: x * x, int)
            print(lazy_squared.unwrap())  # 100

        Chaining monadic computations with :meth:`bind`::

            from deluxe.functional import Lazy

            def parse_int(s: str) -> Lazy[int]:
                return Lazy.pure(int(s))

            lazy_str = Lazy.pure("42")
            lazy_int = lazy_str.bind(parse_int, int)
            print(lazy_int.unwrap())  # 42

        Calling lazy values as functions::

            from deluxe.functional import Lazy

            lazy_value = Lazy.pure(10)
            result = lazy_value()  # Equivalent to lazy_value.unwrap()
            print(result)  # 10

    Note:
        While this class has a :meth:`__set_name__` method, it is **not**
        a descriptor. The method is used only to track metadata
        (``__objclass__`` and ``_name_``) when instances are assigned
        as class attributes. To access the value, explicitly call :meth:`unwrap`
        or use the callable syntax ``instance()``.

    Type Parameters:
        _T: The type of the value that will be produced when the lazy
            computation is evaluated.

    Args:
        value: A callable (typically a function or lambda) that will be
            executed when the lazy value is unwrapped.
        type: The type of the value that will be produced when ``value``
            is called. This is used for type annotations and can be
            different from the callable's actual return type.

    Note:
        The ``value`` callable is not executed during initialization.
        The computation is deferred until :meth:`unwrap` or :meth:`__call__`
        is invoked.

    See Also:
        - :class:`Monad`: The protocol that this class implements.
        - :class:`deluxe.environ.evar`
    """

    __slots__: ClassVar[tuple[str, ...]] = ("__objclass__", "_name_", "_type", "_value")
    __hash__: ClassVar[None] = None  # pyright: ignore[reportIncompatibleMethodOverride]

    def __new__(cls, value: Callable[[], _T], type: type[_T]) -> Self:  # noqa: A002, D102
        self = object.__new__(cls)
        self._value = value
        self._name_ = ""
        self.__objclass__ = NoneType
        self._type = cast("_T", value.type) if isinstance(value, Lazy) else type  # pyright: ignore[reportAttributeAccessIssue]

        return self

    def __init__(self, value: Callable[[], _T], type: type[_T]) -> None:  # noqa: A002, ARG002
        self._value: Callable[[], _T]
        self._name_: str
        self.__objclass__: type
        self._type: type[_T]

    def __set_name__(self, owner: type, name: str) -> None:
        self.__objclass__ = owner
        self._name_ = name

    @property
    def type(self) -> type[_T]:
        """Return the Python type that this :class:`Lazy` instance will produce.

        Returns:
            The type annotation of the value that will be produced when
            this lazy computation is evaluated.

        Examples:
            >>> from deluxe.functional import Lazy
            >>> lazy_int = Lazy(lambda: 42, int)
            >>> lazy_int.type
            <class 'int'>
        """
        return self._type

    @classmethod
    def pure(cls, value: _U) -> Lazy[_U]:
        """Wrap a plain value into the lazy monadic context.

        Creates a :class:`Lazy` instance that will always return the given
        static value when unwrapped. This is the primary way to create a lazy
        value from a non-callable.

        Args:
            value: The plain value to wrap in the lazy context.

        Returns:
            A :class:`Lazy` instance that will produce ``value`` when unwrapped.

        Examples:
            >>> from deluxe.functional import Lazy
            >>> lazy_int = Lazy.pure(42)
            >>> lazy_int.unwrap()
            42
        """

        def pure() -> _U:
            return value

        return cast("Lazy[_U]", cls(pure, type(value)))  # pyright: ignore[reportArgumentType]

    def map(self, func: Callable[[_T], _U], type: type[_U]) -> Lazy[_U]:  # noqa: A002
        """Apply a function to the lazy value using functorial map.

        Creates a new :class:`Lazy` instance that will apply ``func`` to
        the result of this lazy computation when unwrapped. This allows for
        chaining transformations in a lazy context.

        Args:
            func: A function that takes a value of type ``_T`` and returns
                a value of type ``_U``.
            type: The type of the value that ``func`` will return.

        Returns:
            A new :class:`Lazy` instance that will produce ``func(value)``
            when unwrapped, where ``value`` is the result of unwrapping this
            instance.

        Examples:
            >>> from deluxe.functional import Lazy
            >>> lazy_value = Lazy.pure(5)
            >>> lazy_doubled = lazy_value.map(lambda x: x * 2, int)
            >>> lazy_doubled.unwrap()
            10
        """

        def lambda_() -> _U:
            return func(self._value())

        lambda_.__name__ = func.__name__
        return Lazy(lambda_, type)

    def bind(self, func: Callable[[_T], Lazy[_U]], type: type[_U]) -> Lazy[_U]:  # noqa: A002
        """Chain a function that returns a lazy value using monadic bind.

        Applies ``func`` to the result of this lazy computation and returns the
        resulting :class:`Lazy` instance directly. This allows for chaining
        computations where each step produces a new lazy context.

        Args:
            func: A function that takes a value of type ``_T`` and returns a
                :class:`Lazy` instance of type ``_U``.
            type: The type of the value that the returned :class:`Lazy` will
                produce.

        Returns:
            The :class:`Lazy` instance returned by ``func(value)``, where
            ``value`` is the result of unwrapping this instance.

        Examples:
            >>> from deluxe.functional import Lazy
            >>> def parse_int(s: str) -> Lazy[int]:
            ...     return Lazy.pure(int(s))
            >>> lazy_str = Lazy.pure("42")
            >>> lazy_int = lazy_str.bind(parse_int, int)
            >>> lazy_int.unwrap()
            42
        """

        def lambda_() -> _U:
            return func(self._value())._value()

        lambda_.__name__ = func.__name__
        return Lazy(lambda_, type)

    def join(self) -> Self:
        """Flatten this lazy value by wrapping it again.

        Creates a new :class:`Lazy` instance that will produce the result of
        unwrapping this instance. This is useful for normalizing lazy values
        and ensuring a consistent lazy context.

        Returns:
            A :class:`Lazy` instance that will produce the same value as
            calling :meth:`unwrap` on this instance.

        Examples:
            >>> from deluxe.functional import Lazy
            >>> lazy_value = Lazy.pure(42)
            >>> lazy_joined = lazy_value.join()
            >>> lazy_joined.unwrap()
            42
        """
        return self.pure(self.unwrap())  # pyright: ignore[reportReturnType]

    def __call__(self) -> _T:  # noqa: D102
        return self._value()

    def unwrap(self) -> _T:
        """Execute the lazy computation and return its result.

        This method invokes the wrapped callable and returns its result. The
        callable is executed each time :meth:`unwrap` is called; results are
        not automatically cached.

        Returns:
            The result of executing the wrapped callable of type ``_T``.

        Examples:
            >>> from deluxe.functional import Lazy
            >>> def compute() -> int:
            ...     print("Computing...")
            ...     return 42
            >>> lazy_value = Lazy(compute, int)
            >>> result = lazy_value.unwrap()
            Computing...
            >>> print(result)
            42

        Note:
            lazy_value() is equivalent to lazy_value.unwrap()
        """
        return self._value()

    @no_type_check
    def __repr__(self) -> str:  # pragma: no cover
        if isinstance(self._value, Lazy):
            intern = repr(self._value)
            value = f"{self._value.__name__}({intern})"
        elif self._value.__name__ == "pure":
            value = repr(self._value())
        else:
            value = self._value.__name__
        return f"{self.__class__.__name__}[{self._type.__name__}]({value})"


class MaybeCallable(Generic[_T]):
    """Monad wrapping up a type or a callable returning this same type.

    The :class:`MaybeCallable` type is designed to represent values that can
    be either plain values or callables that produce values of the same type.
    This is particularly useful when defining enumerations where some members
    are simple values while others are callable (factory) members.

    When used as a base class for enumerations, :class:`MaybeCallable` enables
    a hybrid pattern where enum members can be either:

    - **Plain values**: Direct values of the wrapped type.
    - **Callable members**: Methods decorated with ``@member`` that accept
      arguments and return values of the wrapped type.

    Examples:
        Basic usage with plain values and callables::

            from deluxe.functional import MaybeCallable

            # Wrapping a plain value
            plain = MaybeCallable(42)
            print(plain.unwrap())  # 42

            # Wrapping a callable
            def double(x: int) -> int:
                return x * 2

            callable_val = MaybeCallable(double)
            print(callable_val(21))  # 42

        Usage as an enumeration base class::

            from enum import Enum, member
            from deluxe.enums import Enum as DocEnum
            from deluxe.functional import MaybeCallable

            class Key(MaybeCallable[bytes]):
                def __call__(self, *args: bytes) -> bytes:
                    return self._callable_(*args)

            class KeyStroke(Key[bytes], Enum):
                @staticmethod
                def _join(string: bytes, other: bytes) -> str:
                    return string.decode() + other.decode()

                @member
                @staticmethod
                def Ctrl(key: bytes) -> str:
                    return KeyStroke._join(b"C-", key)

                @member
                @staticmethod
                def Meta(key: bytes) -> str:
                    return KeyStroke._join(b"M-", key)

                Space = b"Space"
                Tab = b"Tab"
                Enter = b"Enter"

            # Plain enum members
            print(KeyStroke.Space)  # b"Space"
            print(KeyStroke.Tab)    # b"Tab"

            # Callable enum members
            print(KeyStroke.Ctrl(b"h"))  # "C-h"
            print(KeyStroke.Meta(b"a"))  # "M-a"

        Another example with byte strings::

            from deluxe.functional import MaybeCallable
            from deluxe.enums import Enum as DocEnum

            class BString(MaybeCallable[bytes]):
                @staticmethod
                def format(value: bytes) -> bytes:
                    return b"".join((b"#{", value, b"}"))

                def map(self, func):
                    return self.pure(func(self.unwrap()))

            class Format(BString, DocEnum):
                @member
                @staticmethod
                def str(string: bytes) -> bytes:
                    return BString(string)

                @member
                @staticmethod
                def var(string: bytes) -> bytes:
                    name = string.decode()
                    return getattr(Enum("Format", ((name, string),), type=BString), name)

                active_window_index = b"active_window_index"
                pane_id = b"pane_id"

            # Plain enum members
            print(Format.active_window_index)  # b"active_window_index"

            # Callable enum members
            print(Format.var(b"opt"))  # creates a new Format member

    Note:
        When using :class:`MaybeCallable` as a base for enumerations, the
        ``__call__`` method should be overridden in the subclass to properly
        handle callable enum members. The ``@member`` decorator from
        :mod:`enum` is used to mark static methods as callable enum members.

    Type Parameters:
        _T: The type of the value that can be either a plain value or
            a callable returning this same type.

    Args:
        value: Either a plain value of type ``_T`` or a callable that
            accepts no arguments and returns a value of type ``_T``.

    See Also:
        - :class:`Lazy`: A monad for lazy evaluation of computations.
        - :class:`Maybe`: A monad representing optional values.
        - :class:`deluxe.enums.Enum`: Enhanced enumeration base class.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_callable_", "_value_")

    def __new__(cls, value: _T | Callable[[_T], _T]) -> Self:  # noqa: D102
        self = object.__new__(cls)
        self._value_ = value
        if callable(value):
            self._callable_ = cast("Callable[[_T], _T]", value)
        else:

            def _u(*_: _T) -> _T:
                msg = f"'{type(value).__name__}' object is not callable"
                raise TypeError(msg)

            self._callable_ = _u
        return self

    def __init__(self, value: _T | Callable[[_T], _T]) -> None:  # noqa: ARG002
        self._callable_: Callable[[_T], _T]
        self._value_: _T | Callable[[_T], _T]

    @classmethod
    def pure(cls, value: _T | Callable[[_T], _T]) -> Self:
        """Returns a plain value wrapped into the monadic context."""
        return cls(value)

    def map(self, func: Callable[[_T | Callable[[_T], _T]], _T]) -> Self:
        """Returns the result of a functorial map."""
        return self.pure(func(self._value_))

    def bind(self, func: Callable[[_T | Callable[[_T], _T]], Self]) -> Self:
        """Returns the result of a monadic bind."""
        return func(self._value_)

    def join(self) -> Self:
        return self.pure(self.unwrap())

    def unwrap(self) -> _T:
        """Returns the plain wrapped value."""
        if callable(self._value_):
            msg = "could only unwrap plain value"
            raise TypeError(msg)
        return self._value_

    def __call__(self, *args: _T) -> _T:
        """Returns a call on the wrapped value."""
        return self._callable_(*args)

    def __repr__(self) -> str:
        if not isinstance(self, MaybeCallable) and callable(  # pyright: ignore[reportUnnecessaryIsInstance]
            self
        ):
            return f"{self.__class__.__name__}"  # Enum's member case
        return f"{self.__class__.__name__}({self})"

    def __str__(self) -> str:
        return str(self._value_) if hasattr(self, "_value_") else self.__repr__()
