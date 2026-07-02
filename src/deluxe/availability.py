# Copyright (c) 2024 - Gilles Coissac
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
"""Check platform compatibility against specific rules defined by platform hints.

This module provides utilities for restricting the availability of functions
and classes to specific platforms through a hint-based system. Platform hints
are normalized identifiers that represent different aspects of the system
(API, kernel, operating system, Python implementation).

Hints are just words such as those returned by :obj:`sys.platform` (eg.,
``win32``, ``darwin``, ``linux``) or those found in the Python documentation
under the ``Availability`` section (see https://docs.python.org/3/library/intro.html).

The :func:`hints` function generates a tuple of hints based on the current system.
For example, on macOS it would return:

    ('posix', 'darwin', 'macos', 'cpython')

The returned hints are ordered according to this hierarchy:

    - **API**: ``nt`` or ``posix``
    - **Kernel**: ``win32``, ``linux``, ``darwin`` or the generic ``unix`` hint
    - **OS**: ``macos``, ``android``, ``windows``, ``freebsd``, ``aix``, ...
    - **Implementation**: ``cpython``, ``pypy``, ``jython``, ...
    - **Extra**: ``mobile`` is set for iOS and Android

This classification while not perfect, minimizes the ambiguity caused by the multiple
sources that developers face in the Python ecosystem (:obj:`sys.platform`, :obj:`os.name`,
:func:`platform.system`, ...) and mimics the ``Availability`` sections found in the Python
documentation.

All returned hints and input hints in function calls are lowercased for disambiguation.

Examples:
    Restrict a function to POSIX systems except macOS:

        >>> @availability(only='posix', but='darwin')
        ... def my_unix_function(a: int, b: int) -> int:
        ...     # Will run on Linux, FreeBSD, WASI, AIX, etc., but not macOS
        ...     return a + b

    Restrict a function to desktop platforms (exclude mobile):

        >>> @availability(only=None, but='mobile')
        ... def my_desktop_function(a: int, b: int) -> int:
        ...     # Will raise AvailabilityError on iOS and Android
        ...     return a * b

This module includes utilities to:

    - Get platform hints based on the current system via :func:`hints`
    - Check platform support against inclusion/exclusion rules via :func:`supported`
    - Decorate functions and classes to restrict usage by platform via :func:`availability`
"""

from __future__ import annotations

import functools
import re
import sys
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast


if TYPE_CHECKING:
    from collections.abc import Callable


__all__ = ("AvailabilityError", "availability", "hints", "supported")


def hints() -> tuple[str, ...]:  # noqa: PLR0911
    """Get a tuple of platform hints based on the current system.

    This function analyzes the current execution environment and returns a
    tuple of normalized platform hints that identify the system's characteristics.
    The hints follow a hierarchical order: API, kernel, operating system,
    implementation, and any additional flags.

    Returns:
        :obj:`tuple` [ :obj:`str` , ... ]: A tuple of platform hints describing
        the current system. All hints are lowercased.
    """
    hint: str = re.split(r"\d", sys.platform)[0].lower()

    if hint == "win":
        return ("nt", "win32", "windows", sys.implementation.name.lower())
    if hint.startswith("java"):  # pragma: no cover
        import importlib  # noqa: PLC0415

        java_lang = importlib.import_module("java.lang")
        if "win" in java_lang.System.getProperty("os.name").lower():
            return ("nt", "win32", "windows", "java")
        return ("posix", "java")
    if hint in {"wasi", "emscripten"}:
        return ("posix", "vm", "wasi", hint, sys.implementation.name)
    if hint == "cygwin":
        return ("posix", "windows", hint, sys.implementation.name)
    if hint == "ios":
        return ("posix", "darwin", hint, sys.implementation.name, "mobile")
    if hint == "android":
        return ("posix", "linux", hint, sys.implementation.name, "mobile")
    if hint == "darwin":
        return ("posix", hint, "macos", sys.implementation.name)
    if hint == "linux":
        import platform  # noqa: PLC0415

        pretty = platform.freedesktop_os_release().get("ID", hint)
        return ("posix", "unix", hint, pretty, sys.implementation.name)
    return ("posix", "unix", hint, sys.implementation.name)


def _parse_hints(
    only: tuple[str, ...] | str | None, but: tuple[str, ...] | str | None = None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(e.lower() for e in only)
        if isinstance(only, tuple)
        else (only.lower(),)
        if isinstance(only, str)
        else (),
        tuple(e.lower() for e in but)
        if isinstance(but, tuple)
        else (but.lower(),)
        if isinstance(but, str)
        else (),
    )


class AvailabilityError(NotImplementedError):
    """Exception raised when attempting to use a function or class on an unsupported platform.

    This exception is raised by the :func:`availability` decorator when the
    decorated function or class is called or instantiated on a platform that
    does not meet the specified inclusion/exclusion criteria.

    Inherits from:
        :exc:`NotImplementedError`: To indicate that the functionality is not
        implemented for the current platform.
    """


def supported(
    only: tuple[str, ...] | str | None, but: tuple[str, ...] | str | None = None
) -> bool:
    """Check if the current platform is supported by the specified hints.

    Evaluates whether the current platform matches the inclusion and exclusion
    criteria defined by the hints. A platform is supported if it matches any
    of the ``only`` hints (if specified) and does not match any of the ``but``
    hints (if specified).

    Args:
        only: A single platform hint, a tuple of platform hints that should be
            supported, or ``None`` to allow all platforms.
        but: A single platform hint, a tuple of platform hints that should not
            be supported, or ``None`` (default) to exclude no platforms.

    Returns:
        :obj:`bool`: ``True`` if the current platform is supported according to
        the rules, ``False`` otherwise.
    """
    only_, but_ = _parse_hints(only, but)
    hints_ = hints()
    include = any(h in hints_ for h in only_) if only_ else True
    if include and but_:
        for hint in but_:
            if hint in hints_:
                include = False
                break
    return include


_P = ParamSpec("_P")
_R = TypeVar("_R")
_C = TypeVar("_C", bound=type)
_T = TypeVar("_T")


def _patch_docstring(
    obj: object, only: tuple[str, ...] | str | None, but: tuple[str, ...] | str | None = None
) -> None:
    if not object.__doc__:  # pragma: no cover
        return
    only_, but_ = _parse_hints(only, but)
    exc = f" except {', '.join(but_).title()}" if but_ else ""
    obj.__doc__ = f"{obj.__doc__}\nAvailability: {', '.join(only_).title()}{exc}.\n"


def availability(
    only: tuple[str, ...] | str | None, but: tuple[str, ...] | str | None = None
) -> Callable[[_T], _T]:  # Callable[[_C], _C] | Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Decorator to restrict the usage of a function or class to specific platforms.

    The decorated callable will raises :exc:`AvailabilityError` if called
    on a platform that does not match the specified platform availability hints.
    Otherwise, it allows the decorated object to be used normally.
    For classes, the ``__new__`` method is modified to raise the error
    at instantiation time. For functions, a wrapper is applied that raises
    the error on each call.

    If the decorated callable has a docstring, an 'Availability:' one liner string
    will be append at its end.

    Args:
        only: A single platform hint, a tuple of platform hints that should
            be supported, or ``None`` to allow all platforms.
        but: A single platform hint, a tuple of platform hints that should
            not be supported, or ``None`` (default) to exclude no platforms.

    Returns:
        The decorated function or class.
    """
    is_supported = supported(only, but)

    def decorator(decorated: _C | Callable[_P, _R]) -> _C | Callable[_P, _R]:
        msg = (
            f"{type(decorated).__name__} <{decorated.__name__}> only supported on {only or 'all'} "
            f"platforms{' except on ' if but else ''}{but or ''}."
        )

        if issubclass(type(decorated), type):
            decorated = cast("_C", decorated)

            def __new__(cls: type, *args: Any, **kwargs: Any) -> _C:  # noqa: ARG001, N807
                raise AvailabilityError(msg)

            if not is_supported:
                decorated.__new__ = __new__
            _patch_docstring(decorated, only, but)
            return decorated

        decorated = cast("Callable[_P, _R]", decorated)

        @functools.wraps(decorated)
        def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            def unsupported(*_args: _P.args, **_kwargs: _P.kwargs) -> _R:
                raise AvailabilityError(msg)

            if not is_supported:
                return unsupported(*args, **kwargs)
            _patch_docstring(decorated, only, but)
            return decorated(*args, **kwargs)

        return wrapped

    return cast("Callable[[_T], _T]", decorator)
