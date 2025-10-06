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
from __future__ import annotations

import contextlib
import copy
import os
import sys
from collections.abc import (
    Callable,
    ItemsView,
    Iterator,
    KeysView,
    Mapping,
    MutableMapping,
    ValuesView,
)
from operator import add, mul, sub
from pathlib import Path
from typing import IO, ClassVar, Generic, Literal, TypeVar, cast, final

from deluxe.sequences import dedup_list
from deluxe.types import Unset


__all__ = ("EnvValue", "EnvValue", "Operator", "Separator", "envvar")


EnvValue = str | int | float | bool | Path | list[str] | list[Path]
Separator = Literal[";", ":", ",", " "]
SEPARATOR: Separator = ":"


class Environment(MutableMapping[str, EnvValue]):
    """A Mapping for environment variables.

    Environment provides a way to defined and manipulate environment variables
    with various python types. When needed get a dict[str, str] with its `env`
    property and passed it for example to `subprocess.run()` function.
    """

    __slots__: ClassVar[tuple[str, ...]] = ("__dict__", "_kwargs", "_lock", "_protected")
    __list_separator: ClassVar[dict[str, Separator]] = {}
    __hash__: ClassVar[None]

    def __init__(self, **kwargs: EnvValue) -> None:
        self._kwargs: Mapping[str, EnvValue] = kwargs
        self._protected: set[str] = set()
        self._lock: bool = True

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
        default: EnvValue = "",
    ) -> EnvValue:
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

    def items(self) -> ItemsView[str, EnvValue]:
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

    def values(self) -> ValuesView[EnvValue]:
        """Returns a view of the values in this Mapping.

        Returns:
            A ValuesView that provides a dynamic view on
            this Mapping's values.
        """
        return self.__dict__.values()

    def copy(self) -> Environment:
        """Creates a deep copy of this mapping.

        Returns:
            EnvMapping: A new EnvMapping object that is a deep
            copy of the original.
        """
        dup = self.__class__(**self._kwargs)
        for k, v in self.items():
            dup.__dict__[k] = copy.copy(v)
        return dup

    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, other: Environment | Mapping[str, EnvValue], clear: list[str] | None = None
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

    def pop(self, name: str, default: object | None = None) -> EnvValue:
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

    def popitem(self) -> tuple[str, EnvValue]:
        """Removes and returns a name-value pair from the mapping.

        Returns:
            tuple[str, Any]: A name-value pair from the mapping.

        Raises:
            KeyError: If the mapping is empty.
        """
        return self.__dict__.popitem()

    def setdefault(self, name: str, default: EnvValue = Unset) -> EnvValue:
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
        for _cls in self.__class__.__mro__:  # __slots__ case
            if _cls is not object and name in getattr(_cls, "__slots__", ()):
                object.__setattr__(self, name, value)
                return

        if name in self._protected and self._lock:  # protected attributes
            msg = f"{name} is a protected attribute and can't be set by assignment."
            raise AttributeError(msg)

        if isinstance(value, list):  # normal attributes
            value = cast("list[object]", value)
            self._append_list(name, value)
        else:
            self.__dict__[name] = value

    def _append_list(self, key: str, values_list: list[object]) -> None:
        if key in self.__dict__:
            self.__dict__[key] = dedup_list(self.__dict__[key] + values_list)
        else:
            self.__dict__[key] = dedup_list(values_list)

    @staticmethod
    def env_hook(env: dict[str, EnvValue]) -> dict[str, EnvValue]:
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
            elif not str(v) or v is Unset:
                continue
            else:
                env_[k] = str(v)
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

    def __getitem__(self, key: str) -> EnvValue:
        return self.__dict__[key]

    def __setitem__(self, key: str, value: EnvValue) -> None:
        self.__setattr__(key, value)

    def __delitem__(self, key: str) -> None:
        if key not in self._protected:
            del self.__dict__[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def __contains__(self, key: object) -> bool:
        return key in self.__dict__

    def __bool__(self) -> bool:
        return any(self.__dict__.values())

    def __str__(self) -> str:
        return str(self.__dict__)

    def __or__(self, other: Environment | dict[str, EnvValue]) -> Environment:
        res = self.copy()
        res.update(other)
        return res

    def __ior__(self, other: Environment | dict[str, EnvValue]) -> None:  # noqa: PYI034
        self.update(other)

    def __eq__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ == other

    def __ne__(self, other: object) -> bool:
        other = other.__dict__ if isinstance(other, Environment) else other
        return self.__dict__ != other


_T = TypeVar("_T", bound=EnvValue)
_TDIV = TypeVar("_TDIV", bound=int | float | Path)
_TNUM = TypeVar("_TNUM", bound=int | float)

Operator = Callable[[_T, _T], _T]


def _abs(value: _TDIV, _operand: _TDIV) -> _TDIV:
    return Path.absolute(value) if isinstance(value, Path) else cast("_TDIV", abs(value))


def _truediv(value: _TDIV, operand: _TDIV) -> _TDIV:
    return cast("_TDIV", value / operand)  # pyright: ignore[reportOperatorIssue]  # type[ignore]


@final
class envvar(Generic[_T]):  # noqa: N801
    """Declare an enum member as environment variable.

    Example:
        from deluxe.enums import Enum

        class Environ(Enum):
            SOMETHING = "a_normal_string"
            USER = envvar()
            SHELL = envvar(default="bash")
            HISTCONTROL = envvar(defaut=["ignorespace"], separator=":")
            FOLDER = envvar(default=Path())
            SUB_FOLDER = FOLDER / SOMETHING

        if Environ.USER.value.unwrap() is Unset:
            print("no system user is defined")

        folder = Environ.SUB_FOLDER.value.unwrap()
        if not folder.exist():
            folder.mkdir(parents=True)

    """

    __slots__ = (
        "__objclass__",
        "_default",
        "_name_",
        "_operand",
        "_operator",
        "_reference",
        "_separator",
        "_truthy",
        "_type",
    )

    def __init__(
        self,
        default: _T | envvar[_T] = Unset,
        *,
        truthy: tuple[str, ...] = ("true", "1", "on"),
        separator: Separator = SEPARATOR,
    ) -> None:
        self._default: _T | envvar[_T] = default

        self._type: type[_T] = default.type if isinstance(default, envvar) else type(default)
        self._truthy: tuple[str, ...] = truthy
        self._separator: Separator = separator

        self._name_: str
        self.__objclass__: type[_T]
        self._reference: envvar[_T] = Unset
        self._operator: Operator[_T]
        self._operand: _T | envvar[_T]

    def __set_name__(self, owner: type, name: str) -> None:
        self.__objclass__ = owner
        self._name_ = name

    def _resolve_default(self) -> _T:
        if isinstance(self._default, envvar):
            return self._default._resolve_default()
        return self._default

    def _is_list_of_path(self) -> bool:
        if isinstance(dft := self._resolve_default(), list) and len(dft):
            return isinstance(dft[0], Path)
        return False

    def __call__(
        self, operator: Operator[_T], operand: _T | envvar[_T], default: _T | envvar[_T] = Unset
    ) -> envvar[_T]:
        """Returns a new Env build upon self."""
        env = envvar(default)
        env._reference = self
        env._operator = operator
        env._operand = operand
        return env

    def __abs__(self: envvar[_TDIV]) -> envvar[_TDIV]:
        if self.type in {Path, int, float}:
            return self.__call__(
                _abs,
                self,
                self._default,
            )
        raise NotImplementedError

    def __truediv__(self: envvar[_TDIV], other: _TDIV | envvar[_TDIV]) -> envvar[_TDIV]:
        if self.type in {Path, int, float}:
            return self.__call__(
                _truediv,
                other,
                self._default,
            )
        raise NotImplementedError

    def __mul__(self: envvar[_TNUM], other: _TNUM | envvar[_TNUM]) -> envvar[_TNUM]:
        if self.type in {int, float}:
            return self.__call__(mul, other, self._default)
        raise NotImplementedError

    def __add__(self: envvar[_TNUM], other: _TNUM | envvar[_TNUM]) -> envvar[_TNUM]:
        if self.type in {int, float}:
            return self.__call__(add, other, self._default)
        raise NotImplementedError

    def __sub__(self: envvar[_TNUM], other: _TNUM | envvar[_TNUM]) -> envvar[_TNUM]:
        if self.type in {int, float}:
            return self.__call__(sub, other, self._default)
        raise NotImplementedError

    def unwrap(self) -> _T:
        """Returns the variable in environment or the set default."""
        value = (
            os.getenv(self._name_, Unset)
            if self._reference is Unset
            else self._operator(
                self._reference.unwrap(),
                self._operand.unwrap() if isinstance(self._operand, envvar) else self._operand,
            )
        )

        if value is not Unset:
            with contextlib.suppress(ValueError):
                if self._type is bool:
                    return cast("_T", self._to_bool(value))
                if self.type is list:
                    return cast("_T", self._to_list(value))
                return self._type(value)
        return self._default.unwrap() if isinstance(self._default, envvar) else self._default

    @property
    def type(self) -> type[_T]:
        """Returns the type held by self."""
        return self._type

    def _to_bool(self, value: str) -> bool:
        """Returns a str valued as a bool."""
        return value.lower() in self._truthy

    def _to_list(self, value: str) -> list[str] | list[Path]:
        ret = value.split(self._separator)
        return [Path(p) for p in ret] if self._is_list_of_path() else ret

    def __repr__(self) -> str:
        # TODO: set arg for list
        hints = (
            ("NullType", "Null")
            if self._default is Unset
            else (self._type.__name__, repr(self._default))
        )
        return f"{self.__class__.__name__}[{hints[0]}](default={hints[1]})"
