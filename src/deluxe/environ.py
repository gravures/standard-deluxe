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
#
# ruff: noqa: PLR0904, DOC502
"""Environment variable utilities management.

This module provides a flexible system for defining and managing environment
variables with automatic type conversion and validation. It implements a
approach where class attributes can be bound to environment variables and
automatically resolved when accessed.

The module includes two main components:

* :class:`evar` — A type that binds class attributes to environment
  variables with automatic type conversion and default value support.
* :class:`Environment` — A mutable mapping that provides a namespace for
  organizing and managing multiple environment variables with support for
  merging, serialization, and subprocess integration.

Key features:

* Automatic type conversion for Python's built-in types (:obj:`str`, :obj:`int`,
  :obj:`float`, :obj:`bool`, :obj:`~pathlib.Path`, and lists of these types).
* Arithmetic operations for creating derived environment variables.
* Support for boolean conversion with configurable truthy values.
* List parsing with configurable separators.
* Dictionary-like interface for managing environment variables.
* Automatic conversion to string dictionaries for subprocess execution.
* Protected attributes that cannot be modified after initialization.

Examples::

    from deluxe import Environment, evar
    from pathlib import Path

    class Config(Environment):
        DEBUG = evar(default=False, truthy=("yes", "1", "true"))
        PORT = evar(default=8080)
        FOLDER = evar(default=Path("/tmp/data"))
        PATHS = evar(default=["/usr/bin"], separator=":")

    # Create and use environment configuration
    env = Config(DEBUG="yes", PORT=9000, FOLDER=Path("/home/user"))
    print(env.DEBUG)  # True
    print(env.PORT)   # 9000

    # Export for subprocess execution
    env_dict = env.env  # Converts all values to strings

    # Arithmetic operations for derived values
    HALF_PORT = Config.PORT / 2  # Creates new evar that divides PORT by 2
"""

from __future__ import annotations

import contextlib
import copy
import os
import sys
from collections.abc import (
    Callable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    MutableMapping,
    ValuesView,
)
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    ClassVar,
    Literal,
    Protocol,
    Self,
    TypeVar,
    cast,
    no_type_check,
)

from deluxe.functional import Lazy
from deluxe.sequences import dedup_list
from deluxe.types import Unset, UnsetType


__all__ = ("SEPARATOR", "EnvValue", "Environment", "Operator", "Separator", "evar")


if TYPE_CHECKING:

    class _SupportsKeysAndGetItem(Protocol):
        def keys(self) -> Iterable[str]: ...
        def __getitem__(self, key: str, /) -> EnvValue | evar[EnvValue]: ...

    from types import SimpleNamespace

else:

    class SimpleNamespace:
        __slots__ = ()


EnvValue = str | int | float | bool | Path | list[str] | list[Path]
"""Type alias representing supported environment variable value types.

This union type includes all Python types that can be used as environment
variable values in the :class:`Environment` class. It supports:

* :obj:`str` — String values (most common for environment variables)
* :obj:`int` — Integer values
* :obj:`float` — Floating-point values
* :obj:`bool` — Boolean values (converted from strings like "true", "1", "on")
* :obj:`~pathlib.Path` — File system paths
* :obj:`list` [ :obj:`str` ] — Lists of strings (parsed from separated values)
* :obj:`list` [ :obj:`~pathlib.Path` ] — Lists of paths (parsed from separated values)
"""

Separator = Literal[";", ":", ",", " "]
"""Type alias representing supported separator characters for list values.

This literal type defines the allowed separator characters used when
parsing environment variable strings into lists. Supported separators are:

* ``";"`` — Semicolon
* ``":"`` — Colon (default)
* ``","`` — Comma
* ``" "`` — Space
"""

SEPARATOR: Separator = ":"
"""Default separator character for parsing list values from environment variables.

This constant defines the default separator used when converting environment
variable strings to lists. It can be overridden per-attribute using the
``separator`` argument in :class:`evar` or via :meth:`Environment.add_list_separator`.
"""

_E = TypeVar("_E", bound=EnvValue)
_T = TypeVar("_T")
_TDIV = TypeVar("_TDIV", bound=int | float | Path)
_TNUM = TypeVar("_TNUM", bound=int | float)

Operator = Callable[[_T, _T], _T]
"""Type alias representing binary operators for environment variable arithmetic.

This callable type represents binary operations that can be performed on
:class:`evar` instances to create derived environment variables. The operator
takes two values of the same type and returns a value of that type.

Examples include addition, subtraction, multiplication, division, and
path concatenation operations.
"""


class evar(Lazy[_E]):  # noqa: N801
    """Declare a class variable to be bind to an environment variable of the same name.

    The :class:`evar` class binds a class attribute to an environment variable.
    When the attribute is accessed via :meth:`unwrap`, it retrieves the value
    from the environment, converts it to the `type` of `default` argument,
    and returns it. If the environment variable is not set, the default value is returned.

    The :class:`evar` instance `type` is taken from the given `default` argument
    and is :class:`Unset` by default.

    This class supports various Python types including :obj:`str`, :obj:`int`,
    :obj:`float`, :obj:`bool`, :obj:`~pathlib.Path`, and lists of these types.
    Boolean and list conversions are configurable via the ``truthy`` and
    ``separator`` arguments.

    The class also supports arithmetic operations to create derived environment
    variables. Available operations depends on the `type` of the :class:`evar` instance.
    For example, ``FOLDER / "subdir"`` creates a new :class:`evar` that resolves
    to the concatenation of ``FOLDER`` and ``"subdir"``.

    Examples:
        Simple string variable::

            class Config:
                USER = evar(default="guest")

            # If USER env var is not set, returns "guest"
            username = Config.USER.unwrap()

        Numeric operations::

            class Config:
                PORT = evar(default=8080)
                # Creates a new evar augmenting PORT by 1
                ALT_PORT = PORT + 1

        Path operations::

            class Config:
                FOLDER = evar(default=Path("/tmp"))
                SUB_FOLDER = FOLDER / "data"

        Boolean conversion::

            class Config:
                DEBUG = evar(default=False, truthy=("yes", "1", "true"))

            # If DEBUG="yes", returns True
            is_debug = Config.DEBUG.unwrap()

        List parsing::

            class Config:
                PATHS = evar(default=["/usr/bin"], separator=":")

            # If PATHS="/bin:/usr/bin", returns ["/bin", "/usr/bin"]
            paths = Config.PATHS.unwrap()

    Args:
        default: Default value for the environment variable. If another
            :class:`evar` is provided, it will be resolved recursively.
            If :attr:`~deluxe.types.Unset`, the environment variable is
            required.
        truthy: Tuple of string values considered as :obj:`True` for boolean
            type conversion. Defaults to ``("true", "1", "on")``.
        separator: Separator character for parsing list values from strings.
            Defaults to ``":"``.

    Attributes:
        type: The Python type that this :class:`evar` resolves to.

    Raises:
        NotImplementedError: When using arithmetic operations on unsupported
            types (e.g., ``abs()`` on a string).

    Unwraping :class:`evar`:
        Resolve and return the environment variable value.

        Retrieves the environment variable corresponding to this :class:`evar`'s
        name. If found, the value is converted to the specified type. If not
        found or conversion fails, returns the default value.

        For arithmetic-derived :class:`evar` instances, applies the stored
        operator to resolve the final value.

        If no default value was provided (self.type is :class:`Unset`) and a value
        is found in the environment, value will be evaluated as a :class:`str`,
        otherwise :class:`Unset` is return.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_default", "_separator", "_truthy")

    def __new__(  # noqa: D102
        cls,
        default: _E | evar[_E] = Unset,
        *,
        truthy: tuple[str, ...] = ("true", "1", "on"),
        separator: Separator = SEPARATOR,
    ) -> Self:
        self = super().__new__(cls, Unset, UnsetType)
        self._default = default
        self._type = default._type if isinstance(default, evar) else type(default)
        self._value = self._resolve
        self._truthy = tuple(v.casefold() for v in truthy)
        self._separator = separator
        return self

    def __init__(
        self,
        default: _E | evar[_E] = Unset,  # noqa: ARG002
        *,
        truthy: tuple[str, ...] = ("true", "1", "on"),  # noqa: ARG002
        separator: Separator = SEPARATOR,  # noqa: ARG002
    ) -> None:
        self._default: _E | evar[_E]
        self._truthy: tuple[str, ...]
        self._separator: Separator

        # super().__init__(self._resolve)

    def _resolve(self) -> _E:
        value = os.getenv(self._name_, Unset)
        if value is not Unset:
            with contextlib.suppress(ValueError):
                if self._type is bool:
                    return cast("_E", self._to_bool(value))
                if self._type is list:
                    return cast("_E", self._to_list(value))
                if self._type is UnsetType:
                    return str(value)  # pyright: ignore[reportReturnType]
                return self._type(value)
        return self._default.unwrap() if isinstance(self._default, evar) else self._default

    def _is_list_of_path(self) -> bool:  # pragma: no cover
        dft = self._default.unwrap() if isinstance(self._default, evar) else self._default
        if isinstance(dft, list) and len(dft):
            return isinstance(dft[0], Path)
        return False

    def _to_bool(self, value: str) -> bool:
        """Convert a string value to a boolean."""  # noqa: DOC201
        return value.casefold() in self._truthy

    def _to_list(self, value: str) -> list[str] | list[Path]:
        """Convert a string to a list using the configured separator."""  # noqa: DOC201
        ret = list(filter(None, value.split(self._separator)))
        return [Path(p) for p in ret] if self._is_list_of_path() else ret

    def __abs__(self: evar[_TDIV]) -> Lazy[_TDIV]:
        def abs_(value: _TDIV) -> _TDIV:
            return Path.absolute(value) if isinstance(value, Path) else cast("_TDIV", abs(value))

        if issubclass(self.type, (Path, int, float)):  # pyright: ignore[reportUnnecessaryIsInstance]
            return self.map(abs_, self.type)
        raise NotImplementedError

    def __truediv__(self: evar[_TDIV], other: _TDIV | evar[_TDIV]) -> Lazy[_TDIV]:
        @no_type_check
        def truediv(value: _TDIV) -> _TDIV:
            op = other.unwrap() if isinstance(other, Lazy) else other
            return cast("_TDIV", self.type(value / op))

        if issubclass(self.type, (Path, int, float)):  # pyright: ignore[reportUnnecessaryIsInstance]
            type_ = other.type if isinstance(other, Lazy) else type(other)
            return self.map(truediv, type_)  # pyright: ignore[reportUnknownArgumentType]
        raise NotImplementedError

    def __mul__(self: evar[_TNUM], other: _TNUM | evar[_TNUM]) -> Lazy[_TNUM]:
        def mul(value: _TNUM) -> _TNUM:
            op = other.unwrap() if isinstance(other, Lazy) else other
            return cast("_TNUM", value * op)

        if issubclass(self.type, (int, float)):  # pyright: ignore[reportUnnecessaryIsInstance]
            type_ = other.type if isinstance(other, Lazy) else type(other)
            return self.map(mul, type_)
        raise NotImplementedError

    def __add__(self: evar[_TNUM], other: _TNUM | evar[_TNUM]) -> Lazy[_TNUM]:
        def add(value: _TNUM) -> _TNUM:
            op = other.unwrap() if isinstance(other, Lazy) else other
            return cast("_TNUM", value + op)

        if issubclass(self.type, (int, float)):  # pyright: ignore[reportUnnecessaryIsInstance]
            type_ = other.type if isinstance(other, Lazy) else type(other)
            return self.map(add, type_)
        raise NotImplementedError

    def __sub__(self: evar[_TNUM], other: _TNUM | evar[_TNUM]) -> Lazy[_TNUM]:
        def sub(value: _TNUM) -> _TNUM:
            op = other.unwrap() if isinstance(other, Lazy) else other
            return cast("_TNUM", value - op)

        if issubclass(self.type, (int, float)):  # pyright: ignore[reportUnnecessaryIsInstance]
            type_ = other.type if isinstance(other, Lazy) else type(other)
            return self.map(sub, type_)
        raise NotImplementedError

    def __repr__(self) -> str:
        hints = (
            ("UnsetType", "Unset")
            if self._default is Unset
            else (self._type.__name__, repr(self._default))
        )
        return f"{self.__class__.__name__}[{hints[0]}](default={hints[1]})"


# NOTE: inherit from SimpleNamespace to stop type checkers complaining
#       when setting or getting attributes from an Environment
class Environment(MutableMapping[str, EnvValue | evar[EnvValue]], SimpleNamespace):
    """A mutable mapping for environment variables.

    The :class:`Environment` class provides a way to define and manipulate
    environment variables with various Python types. It implements the
    :class:`~collections.abc.MutableMapping` abc, making it compatible
    with standard dictionary operations and other mapping abstractions.

    Instances acts either as a regular `MutableMapping` or a :class:`SimpleNamespace`,
    so setting instance attribute with 'instance.a = value' is equivalent
    to 'instance[name] = value'.

    This class supports storing environment variables as native Python types
    such as :obj:`str`, :obj:`int`, :obj:`float`, :obj:`bool`,
    :obj:`~pathlib.Path`, and lists of these types. When exporting to a
    dictionary for use with subprocesses or other system calls, use the
    :attr:`env` property which converts all values to strings.

    The :attr:`env` property also automatically resolves any :class:`evar` defined
    in the class hierarchy or set as an instance's attribute and includes them
    in the exported dictionary.

    Basic Usage
    -----------

    Creating an Environment instance::

        from deluxe import Environment, evar
        from pathlib import Path

        class Config(Environment):
            DEBUG = evar(default=False, truthy=("yes", "1", "true"))
            PORT = evar(default=8080)
            FOLDER = evar(default=Path("/tmp/data"))

        # Instantiate and populate
        env = Config(DEBUG="yes", PORT=9000, FOLDER=Path("/home/user"))
        print(env.DEBUG)  # True
        print(env.PORT)   # 9000

    Using the env property for subprocess::

        import subprocess
        env_dict = env.env  # Converts all values to str
        subprocess.run(["my_command"], env=env_dict)

    Merging environments::

        base = Config(DEBUG=False)
        overrides = {"DEBUG": "true", "PORT": "3000"}
        merged = base | overrides


    List Deduplication
    ------------------

    When setting a list value, duplicates are automatically removed while
    preserving order. The first occurrence of each element is kept.
    This deduplication applies whenever a list value is provided to the
    environment: at instantiation, via :meth:`update`, or by direct
    attribute assignment.

    Deduplication at instantiation::

        env = Environment(PATHS=["/usr/bin", "/bin", "/usr/bin"])
        # env.PATHS is now ["/usr/bin", "/bin"]

    Deduplication via update::

        env = Environment(PATHS=["/usr/bin"])
        env.update({"PATHS": ["/bin", "/usr/bin"]})
        # env.PATHS is now ["/usr/bin", "/bin"]

    Deduplication on attribute assignment::

        env = Environment()
        env.PATHS = ["/usr/bin", "/bin", "/usr/bin"]
        # env.PATHS is now ["/usr/bin", "/bin"]

    Assigning to an existing list attribute appends new values and
    deduplicates the combined result::

        env = Environment()
        env.PATHS = ["/usr/bin"]
        env.PATHS = ["/bin", "/usr/bin"]
        # env.PATHS is now ["/usr/bin", "/bin"]

    This append-on-assign behavior means list assignment is not idempotent.
    Use :meth:`clear` or :meth:`pop` to replace a list entirely::

        env.clear()
        env.PATHS = ["/usr/bin", "/bin"]

    See Also:
        - :class:`evar`: Type for binding class attributes to environment variables.

    """

    __slots__: ClassVar[tuple[str, ...]] = ("__dict__", "_lock", "_protected")
    __list_separator: ClassVar[dict[str, Separator]] = {}
    __hash__: ClassVar[None] = None
    __reversed__: ClassVar[None] = None

    def __new__(  # noqa: D102
        cls,
        other: _SupportsKeysAndGetItem | Iterable[tuple[str, EnvValue | evar[EnvValue]]] = (),
        /,
        **kwargs: EnvValue,  # noqa: ARG004
    ) -> Self:
        self = object.__new__(cls)
        self.__dict__ = {}  # dict(other)
        self._protected = set()
        self._lock = True
        self.update(dict(other))
        return self

    def __init__(
        self,
        other: _SupportsKeysAndGetItem | Iterable[tuple[str, EnvValue | evar[EnvValue]]] = (),  # noqa: ARG002
        /,
        **kwargs: EnvValue,  # noqa: ARG002
    ) -> None:
        self._protected: set[str]
        self._lock: bool

    @staticmethod
    def add_list_separator(attribute: str, separator: Separator) -> None:
        """Adds a list separator for a specific attribute.

        Args:
            attribute (str): The attribute to add the separator for.
            separator (str): The separator character.
        """
        Environment.__list_separator[attribute] = separator

    def get(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        name: str,
        default: EnvValue | evar[EnvValue] = "",
    ) -> EnvValue | evar[EnvValue]:
        """Retrieve the value associated with a name.

        Retrieve the value associated with the given name.

        Args:
            name (str): The name to retrieve the value for.
            default (EnvValue, optional): The default value to return
            if name is not found. Defaults to an empty string.

        Returns:
            EnvValue: The value associated with name if found,
            otherwise the default value.
        """
        return self.__dict__.get(name, default)

    def items(self) -> ItemsView[str, EnvValue | evar[EnvValue]]:
        """Returns a view of the name-value pairs of this Mapping.

        Returns:
            An ItemsView that provides a dynamic view on this Mapping.
        """
        return self.__dict__.items()

    def keys(self) -> KeysView[str]:
        """Returns a view of the keys this Mapping.

        Returns:
            A KeysView that provides a dynamic view on this Mapping's keys.
        """
        return self.__dict__.keys()

    def values(self) -> ValuesView[EnvValue | evar[EnvValue]]:
        """Returns a view of the values in this Mapping.

        Returns:
            A ValuesView that provides a dynamic view on
            this Mapping's values.
        """
        return self.__dict__.values()

    def copy(self) -> Environment:
        """Creates a shallow copy of this mapping.

        Returns:
            EnvMapping: A new EnvMapping object that is a deep
            copy of the original.
        """
        return copy.copy(self)

    def __reduce__(self) -> tuple[object, ...]:
        return (self.__class__.__new__, (self.__class__,), self.__dict__)

    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        other: Environment | Mapping[str, EnvValue | evar[EnvValue]],
        clear: list[str] | None = None,
    ) -> None:
        """Update this Mapping.

        Update this Mapping with the values from another Mapping.

        Parameters:
            other (EnvMapping | dict[str, Any]): The object or mapping
            containing the values to update the EnvMapping with.
            clear (list[str], optional): A list of names to set as empty lists
            in the EnvMapping. Defaults to an empty list.
        """
        clear = clear or []

        if isinstance(other, Environment):
            other = other.__dict__
        for key, value in other.items():
            if key not in self._protected:
                if (key in clear) and (isinstance(self.__dict__[key], list)):
                    self.__dict__[key] = []
                setattr(self, key, value)

    def clear(self) -> None:
        """Clears all attributes."""
        self.__dict__.clear()

    def pop(self, name: str, default: object | None = None) -> EnvValue | evar[EnvValue]:
        """Removes and returns the value associated with a name.

        If name is in the mapping, remove it and return its value,
        else return default. If default is not given and name is not
        in the mapping, a KeyError is raised..

        Args:
            name (str): The name of the attribute to remove.
            default (str): A default value to return.

        Returns:
            Any: The value associated with the name.

        Raises:
            KeyError: If the name is not found.
        """
        return self.__dict__.pop(name, default)

    def popitem(self) -> tuple[str, EnvValue | evar[EnvValue]]:
        """Removes and returns a name-value pair from the mapping.

        Returns:
            tuple[str, Any]: A name-value pair from the mapping.

        Raises:
            KeyError: If the mapping is empty.
        """
        return self.__dict__.popitem()

    def setdefault(
        self, name: str, default: EnvValue | evar[EnvValue] = Unset
    ) -> EnvValue | evar[EnvValue]:
        """Sets the value associated with a name.

        If name is defined in the mapping, return its value.
        If not, defined it with a value of default and return default.
        default defaults to None.

        Args:
            name (str): The name of the attribute to set.
            default (Any, optional): The default value to set if name is not found.

        Returns:
            Any: The value associated with name.
        """
        if name in self.__dict__:
            return self.__dict__[name]
        setattr(self, name, default)
        return default

    def __setattr__(self, name: str, value: object) -> None:
        for cls_ in self.__class__.__mro__:  # __slots__ case
            if cls_ is not object and name in getattr(cls_, "__slots__", ()):
                object.__setattr__(self, name, value)
                return

        if name in self._protected and self._lock:  # protected attributes  # pragma: no cover
            msg = f"{name} is a protected attribute and can't be set by assignment."
            raise AttributeError(msg)

        if isinstance(value, list):  # normal attributes
            value = cast("list[object]", value)
            self._set_list_attr(name, value)
        elif isinstance(value, evar):
            tmp = copy.copy(value)  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            tmp.__set_name__(self.__class__, name)
            self.__dict__[name] = tmp
        else:
            self.__dict__[name] = value

    def _set_list_attr(self, key: str, list_: list[object]) -> None:
        if (attr := self.__dict__.get(key)) and isinstance(attr, list):
            self.__dict__[key] = dedup_list(attr + list_)  # pyright: ignore[reportUnknownArgumentType]
        else:
            self.__dict__[key] = dedup_list(list_)

    @staticmethod
    def env_hook(
        env: dict[str, EnvValue | evar[EnvValue]],
    ) -> dict[str, EnvValue | evar[EnvValue]]:
        """Called by the env property getter function.

        Does nothing by default. Subclasses can override this method.
        This method is called by the env property getter function,
        just before beginning to return the environment variables.
        A working dictionary is passed to this method, so subclass
        can manipulate it before returning it.

        Returns:
            dict[str, EnvValue]: the altered mapping.
        """
        return env

    def _get_evar_classes(self) -> list[evar[EnvValue]]:
        r: list[evar[EnvValue]] = []
        for cls in self.__class__.__mro__:
            r.extend(v for v in cls.__dict__.values() if isinstance(v, evar))  # pyright: ignore[reportUnknownArgumentType]
        return r

    @property
    def env(self) -> dict[str, str]:
        """Returns self as a dict with all values converted to str.

        Returns:
            dict[str, str]: A dictionary containing the environment variables.
        """
        env_: dict[str, str] = {}
        for k, v in self.env_hook(dict(self.__dict__)).items():
            if isinstance(v, list):
                separator = Environment.__list_separator.get(k, SEPARATOR)
                env_[k] = separator.join([str(p) for p in v])
            elif isinstance(v, bool):
                env_[k] = str(int(v))
            elif isinstance(v, evar):
                if tmp := v.unwrap():
                    env_[k] = str(tmp)
            elif not str(v) or v is Unset:
                continue
            else:
                env_[k] = str(v)

        for e in self._get_evar_classes():
            if tmp := e.unwrap():
                env_.setdefault(e._name_, str(tmp))  # pyright: ignore[reportPrivateUsage]
        return env_

    def dump(self, file: IO[str] = sys.stdout) -> None:
        """Dump the environment variables to a file.

        Args:
            file (IO[str], optional): The file to write the environment
            variables to. Defaults to sys.stdout.
        """
        dump = "".join(f"{k} = {v}\n" for k, v in self.env.items())
        file.write(dump)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __getitem__(self, key: str) -> EnvValue | evar[EnvValue]:
        return self.__dict__[key]

    def __setitem__(self, key: str, value: EnvValue | evar[EnvValue]) -> None:
        self.__setattr__(key, value)

    def __delitem__(self, key: str) -> None:
        if key not in self._protected:  # pragma: no cover
            del self.__dict__[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def __contains__(self, key: object) -> bool:
        return key in self.__dict__

    def __bool__(self) -> bool:
        return any(self.__dict__.values())

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        cls = {e._name_: e for e in self._get_evar_classes()}  # pyright: ignore[reportPrivateUsage]
        return f"{self.__class__.__name__}({cls | self.__dict__})"

    def __or__(self, other: Environment | Mapping[str, EnvValue | evar[EnvValue]]) -> Environment:
        res = self.copy()
        res.update(other)
        return res

    def __ior__(self, other: Environment | Mapping[str, EnvValue | evar[EnvValue]]) -> Self:
        self.update(other)
        return self

    def __eq__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ == other

    def __ne__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ != other
