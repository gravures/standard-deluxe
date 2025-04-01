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
    ('posix', 'darwin', 'macos', 'cpython').

The returned hints are as much as possible ordered to fit this hierarchy:
    Api: <nt> or <posix>
    Kernel: <win32>, <linux>, <darwin> or the generic <unix> hint
    Os: <macos>, <android>, <windows>, <freebsd>, <aix>, ...
    Implementation: <cpython>, <pypy>, <jython>, ...
    extra: <mobile> is set for ios and android

This classification is certainly not perfect but try to mnimize the ambiguity
poduced by the many sources that developers face to in the python ecosystem (sys.platform,
os.name, platform.system(), ...) and try to mimic the 'Availability' sections found
in the python documentation.

Returned and input hints in function call are all lowercased for disambiguity.

Examples:
@availability(only=('posix',), but=('darwin',))
my_unice_function(a: int, b: int) -> int:
    print("will print on linux but also aix, freebsd, wasi and other")

@availability(only=(), but=('mobile',))
my_desktop_function(a: int, b: int) -> int:
    print("will raise a notImplementedError on ios and android")


This module includes utilities to:

- Get platform hints based on the current system
- Check platform support against inclusion/exclusion rules
- Decorator function for platform availability restrictions
"""

from __future__ import annotations

import functools
import re
import sys
from typing import TYPE_CHECKING, ParamSpec, TypeVar


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


def supported(only: tuple[str, ...], but: tuple[str, ...]) -> bool:
    """Checks if the current platform is supported by specified hints.

    Args:
        only: A tuple of platform hints that the function should be supported on.
        but: A tuple of platform hints that the function should not be supported on.

    Returns:
        bool: True if the platform is supported, False otherwise.
    """
    only_ = tuple(e.lower() for e in only)
    but_ = tuple(e.lower() for e in but)
    id_ = hints()

    include = any(hint in id_ for hint in only_) if only_ else True
    if include:
        for hint in but_:
            if hint in id_:
                include = False
                break
    return include


P = ParamSpec("P")
R = TypeVar("R")


def availability(
    only: tuple[str, ...], but: tuple[str, ...]
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for restrincting function call to platforms availability hints.

    This decorator will raise a NotImplementedError if the decorated function is called
    on a platform that does not fit the specification passed as arguments, otherwise
    it will return seamlessly the decoated function.

    Args:
        only: A tuple of platform hints that the function is supported on.
              An empty tuple means all platforms are supported.
        but: A tuple of platform hints that the function should not be supported on.

    Returns:
        Callable[..., Callable[P, R]]: The decorated function.
    """

    def decorator_(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def implement(*args: P.args, **kwargs: P.kwargs) -> R:
            if not supported(only, but):
                msg = (
                    f"{type(func).__name__} <{func.__name__}> supported on {only or 'all'} "
                    f"platforms{' except on ' if but else ''}{but}."
                )
                raise NotImplementedError(msg)
            return func(*args, **kwargs)

        return implement

    return decorator_
