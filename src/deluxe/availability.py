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
"""Availability module.

This module provides functions for checking the platform compatibility
against specific rules defined as tuple of hints (for inclusion and exclusion).

Hints are simple word as such returned by sys.platform (eg: win32, darwin, linux, ...)
or those found in the python documentation under the 'Availability' section
(see: https://docs.python.org/3/library/intro.html).

The hints function in this module will composed a tuple of hints based on the current
system, for example on MacOs it could returned:

    ('posix', 'darwin', 'macos', 'cpython')

The returned hints are as much as possible ordered to fit this hierarchy:

    Api: <nt> or <posix>
    Kernel: <win32>, <linux>, <darwin> or the generic <unix> hint
    Os: <macos>, <android>, <windows>, <freebsd>, <aix>, ...
    Implementation: <cpython>, <pypy>, <jython>, ...
    extra: <mobile> is set for ios and android

This classification is certainly not perfect but try to mnimize the ambiguity
produced by the many sources that developers face to in the python ecosystem (sys.platform,
os.name, platform.system(), ...) and try to mimic the 'Availability' sections found
in the python documentation.

Returned and input hints in function call are all lowercased for disambiguity.

Examples::

    @availability(only='posix', but='darwin')
    my_unice_function(a: int, b: int) -> int:
        print("will print on linux but also aix, freebsd, wasi and other")

    @availability(only=None, but='mobile')
    my_desktop_function(a: int, b: int) -> int:
        print("will raise a notImplementedError on ios and android")


This module includes utilities to:

    - Get platform hints based on the current system
    - Check platform support against inclusion/exclusion rules
    - Decorator for function and class to restrict usage following platform availability hints
"""

from __future__ import annotations

import functools
import re
import sys
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast


if TYPE_CHECKING:
    from collections.abc import Callable


def hints() -> tuple[str, ...]:  # noqa: PLR0911
    """Returns a tuple of platform hints based on the current system.

    Returns:
        tuple[str, ...]: A tuple of platform hints.
    """
    hint: str = re.split(r"\d", sys.platform)[0].lower()

    if hint == "win":
        return ("nt", "win32", "windows", sys.implementation.name.lower())
    if hint.startswith("java"):
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


def supported(
    only: tuple[str, ...] | str | None, but: tuple[str, ...] | str | None = None
) -> bool:
    """Checks if the current platform is supported by the specified hints.

    Args:
        only: A single hint, a tuple of platform hints that should be supported or None.
        but: A single hint, a tuple of platform hints that should not be supported or None,
             default to None.

    Returns:
        bool: True if the platform is supported, False otherwise.
    """
    if isinstance(only, tuple):
        only = tuple(e.lower() for e in only)
    elif isinstance(only, str):
        only = (only.lower(),)

    if isinstance(but, tuple):
        but = tuple(e.lower() for e in but)
    elif isinstance(but, str):
        but = (but.lower(),)
    hints_ = hints()

    include = any(h in hints_ for h in only) if only else True
    if include and but:
        for hint in but:
            if hint in hints_:
                include = False
                break
    return include


_P = ParamSpec("_P")
_R = TypeVar("_R")
_C = TypeVar("_C", bound=type)
_T = TypeVar("_T")


def availability(
    only: tuple[str, ...] | str | None, but: tuple[str, ...] | str | None = None
) -> Callable[[_T], _T]:  # Callable[[_C], _C] | Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Decorator restrincting call to function or class defined by platforms availability hints.

    This decorator will raise a NotImplementedError if the decorated function or class
    is called on a platform that does not fit the specification passed as arguments,
    otherwise it will return seamlessly the decorated function or class.

    Args:
        only: A single hint, a tuple of platform hints that should be supported or None.
        but: A single hint, a tuple of platform hints that should not be supported or None,
             default to None.

    Returns:
        Callable[..., Callable[P, R]]: The decorated function or class.
    """
    is_supported = supported(only, but)

    def decorator(decorated: _C | Callable[_P, _R]) -> _C | Callable[_P, _R]:
        msg = (
            f"{type(decorated).__name__} <{decorated.__name__}> only supported on {only or 'all'} "
            f"platforms{' except on ' if but else ''}{but}."
        )

        if issubclass(type(decorated), type):
            decorated = cast("_C", decorated)

            def __new__(cls: type, *args: Any, **kwargs: Any) -> _C:  # noqa: N807
                raise NotImplementedError(msg)

            if not is_supported:
                decorated.__new__ = __new__
            return decorated

        decorated = cast("Callable[_P, _R]", decorated)

        @functools.wraps(decorated)
        def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            def unsupported(*_args: _P.args, **_kwargs: _P.kwargs) -> _R:
                raise NotImplementedError(msg)

            if not is_supported:
                return unsupported(*args, **kwargs)
            return decorated(*args, **kwargs)

        return wrapped

    return cast("Callable[[_T], _T]", decorator)
