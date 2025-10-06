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
#
# Parts of this module are borrowed to the code from Python 3.13
# test.support.import_helper module, which is not guaranted
# to be present in all python distribution and could be removed without
# notice between release of Python.
# Copyright (C) 2006 Python Software Foundation.
# vendored under the PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
#
"""Module loading and import utilities.

This module provides tools for dynamic module loading, fresh imports that
bypass :data:`sys.modules`, monkey patching, and context managers for
isolating import side-effects.

.. note::

    Parts of this module are derived from the Python ``test.support.import_helper``
    module (Copyright (C) 2006 Python Software Foundation, licensed under
    the `PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2`_). That module is part
    of CPython's test suite and is not guaranteed to be available in all Python
    distributions or to remain stable between releases (actually it is already
    absent from some standalone Python build).
    Those vendored portions have been adapted to fit `standard-deluxe` public API:
    :class:`CleanImport`, :class:`DirsOnSysPath`, :func:`forget_module`, :func:`frozen_modules`,
    :func:`import_fresh_module`.

.. _PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2:
    https://docs.python.org/3/license.html#psf-license
"""

from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import logging
import os
import sys
import time
import warnings
from _imp import (
    _override_frozen_modules_for_tests,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]
)
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, ClassVar, Self, final

from deluxe.types import AnyFilePath, Unset


if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType, TracebackType


__all__ = (
    "CleanImport",
    "DirsOnSysPath",
    "Module",
    "Patch",
    "Patchable",
    "forget_module",
    "frozen_modules",
    "import_fresh_module",
    "loads_module",
    "monkey",
)


__all__ = ("Module", "Patch", "Patchable", "loads_module", "monkey")


logger = logging.getLogger(__name__)

Patchable = object
"""Type alias for objects that can be the target of a monkey patch."""

Patch = Callable[..., object]
"""Type alias for monkey patch callables."""


def _waitfor(
    func: Callable[..., Any], pathname: AnyFilePath, waitall: bool = False
) -> None:  # pragma: no cover
    # Perform the operation
    func(pathname)
    # Now setup the wait loop
    if waitall:
        name = ""
        dirname = pathname
    else:
        dirname, name = os.path.split(pathname)
        dirname = dirname or "."
    # Check for `pathname` to be removed from the filesystem.
    # The exponential backoff of the timeout amounts to a total
    # of ~1 second after which the deletion is probably an error
    # anyway.
    # Testing on an i7@4.3GHz shows that usually only 1 iteration is
    # required when contention occurs.
    timeout = 0.001
    while timeout < 1.0:
        # Note we are only testing for the existence of the file(s) in
        # the contents of the directory regardless of any security or
        # access rights. If we have made it this far, we have sufficient
        # permissions to do that much using Python's equivalent of the
        # Windows API FindFirstFile.
        # Other Windows APIs can fail or give incorrect results when
        # dealing with files that are pending deletion.
        l_ = os.listdir(dirname)  # noqa: PTH208
        if not (l_ if waitall else name in l_):
            return
        # Increase the timeout and try again
        time.sleep(timeout)
        timeout *= 2


def _unlink(filename: AnyFilePath) -> None:  # pragma: no cover
    with contextlib.suppress(FileNotFoundError, NotADirectoryError):
        if sys.platform.startswith("win"):
            _waitfor(os.unlink, filename)
        else:
            os.unlink(filename)  # noqa: PTH108


@contextlib.contextmanager
def _ignore_deprecated_imports(ignore: bool = True):  # pragma: no cover
    """Context manager to suppress package and module deprecation warnings when importing them.

    If ignore is False, this context manager has no effect.
    """
    if ignore:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                ".+ (module|package)",
                DeprecationWarning,
            )
            yield
    else:
        yield


def _unload(name: str) -> None:  # pragma: no cover
    with contextlib.suppress(KeyError):
        del sys.modules[name]


def loads_module(name: str, where: Path) -> ModuleType | None:
    """Load a Python module or package from a filesystem path.

    This is a convenience wrapper around :class:`Module` that resolves
    and loads the module in a single call.

    Args:
        name (:obj:`str`): The fully qualified module name to load.
        where (:class:`~pathlib.Path`): The directory to search for the
            module in.

    Returns:
        :class:`~types.ModuleType` | ``None``: The loaded module if found
        and successfully imported, ``None`` otherwise.

    Raises:
        :exc:`ModuleNotFoundError`: If the module cannot be found at
            the given path.
        :exc:`ImportError`: If loading the module fails.
    """
    mod = Module(name=name, where=where)
    mod.load()
    return mod.module


def _save_and_remove_modules(names: Iterable[str]):  # pragma: no cover
    orig_modules: dict[str, ModuleType] = {}
    prefixes = tuple(name + "." for name in names)
    for modname in list(sys.modules):
        if modname in names or modname.startswith(prefixes):
            orig_modules[modname] = sys.modules.pop(modname)
    return orig_modules


def forget_module(name: str) -> None:  # pragma: no cover
    """Forget a module was ever imported.

    This removes the module from :data:`sys.modules` and deletes any
    PEP 3147/488 or legacy ``.pyc`` cached bytecode files found along
    :data:`sys.path`.

    Args:
        name (:obj:`str`): The fully qualified module name to forget.
    """
    _unload(name)
    for dirname in sys.path:
        source = os.path.join(dirname, name + ".py")  # noqa: PTH118
        # It doesn't matter if they exist or not, unlink all possible
        # combinations of PEP 3147/488 and legacy pyc files.
        _unlink(source + "c")
        for opt in ("", 1, 2):
            _unlink(importlib.util.cache_from_source(source, optimization=opt))


def import_fresh_module(
    name: str,
    fresh: Iterable[str] = (),
    blocked: Iterable[str] = (),
    *,
    deprecated: bool = False,
    usefrozen: bool = False,
) -> ModuleType | None:  # pragma: no cover
    """Import and return a module, deliberately bypassing :data:`sys.modules`.

    This function imports and returns a fresh copy of the named Python module
    by removing the named module from :data:`sys.modules` before doing the
    import. Note that unlike :func:`importlib.reload`, the original module is
    not affected by this operation.

    The named module and any modules named in the *fresh* and *blocked*
    parameters are saved before starting the import and then reinserted into
    :data:`sys.modules` when the fresh import is complete.

    Args:
        name (:obj:`str`): The fully qualified module name to import.
        fresh (Iterable[:obj:`str`]): Additional module names that are also
            removed from the :data:`sys.modules` cache before the import.
            If one of these modules cannot be imported, ``None`` is returned.
            Default: ``()``.
        blocked (Iterable[:obj:`str`]): Module names that are replaced with
            ``None`` in the module cache during the import to ensure that
            attempts to import them raise :exc:`ImportError`.
            Default: ``()``.
        deprecated (:obj:`bool`): If ``True``, module and package
            deprecation messages are suppressed during this import.
            Default: ``False``.
        usefrozen (:obj:`bool`): If ``False`` (the default), the frozen
            importer is disabled (except for essential modules like
            ``importlib._bootstrap``). Default: ``False``.

    Returns:
        :class:`~types.ModuleType` | ``None``: The freshly imported module,
        or ``None`` if one of the *fresh* modules could not be imported.

    Raises:
        ImportError: If the named module cannot be imported.
    """  # noqa: DOC502
    # NOTE: test_heapq, test_json and test_warnings include extra sanity checks
    # to make sure that this utility function is working as expected
    with _ignore_deprecated_imports(deprecated):
        # Keep track of modules saved for later restoration as well
        # as those which just need a blocking entry removed
        fresh = list(fresh)
        blocked = list(blocked)
        names = {name, *fresh, *blocked}
        orig_modules = _save_and_remove_modules(names)
        for modname in blocked:
            sys.modules[modname] = None  # pyright: ignore[reportArgumentType]

        try:
            with frozen_modules(usefrozen):
                # Return None when one of the "fresh" modules can not be imported.
                try:
                    for modname in fresh:
                        __import__(modname)
                except ImportError:
                    return None
                return importlib.import_module(name)
        finally:
            _save_and_remove_modules(names)
            sys.modules.update(orig_modules)


@contextlib.contextmanager
def frozen_modules(enabled: bool = True):  # pragma: no cover
    """Force frozen modules to be used (or not).

    This context manager controls whether the Python importer uses
    precompiled frozen modules. When disabled, the standard source-based
    import machinery is used instead.

    This only applies to modules that haven't been imported yet.
    Some essential modules (e.g. ``importlib._bootstrap``) will always be
    imported frozen regardless of this setting.

    Args:
        enabled (:obj:`bool`): If ``True``, frozen modules are enabled.
            If ``False``, frozen modules are disabled. Default: ``True``.

    Yields:
        ``None``: This context manager yields nothing.
    """
    _override_frozen_modules_for_tests(1 if enabled else -1)
    try:
        yield
    finally:
        _override_frozen_modules_for_tests(0)


class CleanImport:  # pragma: no cover
    """Context manager to force import to return a new module reference.

    This is useful for testing module-level behaviors, such as
    the emission of a :exc:`DeprecationWarning` on import.

    When entered, the named modules are removed from :data:`sys.modules`
    so that subsequent imports return fresh references. On exit, the
    original :data:`sys.modules` state is restored.

    Args:
        *module_names (:obj:`str`): One or more fully qualified module
            names to remove from :data:`sys.modules`.
        usefrozen (:obj:`bool`): If ``False`` (the default), the frozen
            importer is disabled (except for essential modules like
            ``importlib._bootstrap``). Default: ``False``.

    Examples::

        with CleanImport("foo"):
            importlib.import_module("foo")  # fresh import
    """

    def __init__(self, *module_names: str, usefrozen: bool = False) -> None:
        self.original_modules: dict[str, ModuleType] = sys.modules.copy()
        for module_name in module_names:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # It is possible that module_name is just an alias for
                # another module (e.g. stub for modules renamed in 3.x).
                # In that case, we also need delete the real module to clear
                # the import cache.
                if module.__name__ != module_name:
                    del sys.modules[module.__name__]
                del sys.modules[module_name]
        self._frozen_modules = frozen_modules(usefrozen)  # pyright: ignore[reportUnannotatedClassAttribute]

    def __enter__(self) -> Self:
        self._frozen_modules.__enter__()
        return self

    def __exit__(
        self, t: type[BaseException] | None, i: BaseException | None, tb: TracebackType | None
    ) -> None:
        sys.modules.update(self.original_modules)
        self._frozen_modules.__exit__(t, i, tb)


class DirsOnSysPath:  # pragma: no cover
    """Context manager to temporarily add directories to :data:`sys.path`.

    This makes a copy of :data:`sys.path`, appends any directories given
    as positional arguments, then reverts :data:`sys.path` to the copied
    settings when the context ends.

    Note that *all* :data:`sys.path` modifications in the body of the
    context manager, including replacement of the object, will be
    reverted at the end of the block.

    Args:
        *paths (:obj:`str`): Directory paths to temporarily add to
            :data:`sys.path`.

    Examples::

        with DirsOnSysPath("/tmp/my_modules"):
            import my_module
    """

    def __init__(self, *paths: str) -> None:
        self.original_value: list[str] = sys.path[:]
        self.original_object: list[str] = sys.path
        sys.path.extend(paths)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, t: type[BaseException] | None, i: BaseException | None, tb: TracebackType | None
    ) -> None:
        sys.path = self.original_object
        sys.path[:] = self.original_value


class Module:
    """Utility class for dynamic loading of a Python module.

    This class wraps the :mod:`importlib` machinery to resolve a module
    specification and load it from an explicit filesystem location or
    the default search path. It tracks the module's package hierarchy
    and provides helper methods for comparing module names.

    Args:
        name (:obj:`str`): The module name to resolve. Can be a
            relative name (e.g. ``"foo"``) which is resolved against
            *package*.
        package (:obj:`str`): The package context for resolving relative
            module names. Default: ``""``.
        where (:class:`~pathlib.Path` | ``None``): An explicit directory
            to search for the module. If ``None``, the standard
            :func:`importlib.util.find_spec` search is used.
            Default: ``None``.

    Raises:
        :exc:`ModuleNotFoundError`: If the module cannot be found.

    Examples::

        mod = Module("my_package.my_module")
        mod.load()
        print(mod.full_name)  # "my_package.my_module"
    """

    __slots__: tuple[str, ...] = ("_is_pkg", "_is_root", "_name", "_pkg", "_spec")

    def __init__(self, name: str, *, package: str = "", where: Path | None = None) -> None:
        abs_name = importlib.util.resolve_name(name, package)

        self._spec: importlib.machinery.ModuleSpec = self._find_spec(abs_name, where)
        self._is_pkg: bool = self._spec.submodule_search_locations is not None
        self._pkg: str
        self._name: str
        self._pkg, _, self._name = abs_name.rpartition(".")
        self._is_root: bool = self._is_pkg and not self._pkg

    @staticmethod
    def _find_spec(name: str, where: Path | None) -> importlib.machinery.ModuleSpec:
        if where is None:
            spec = importlib.util.find_spec(name=name)
        else:
            loader_details = [
                (importlib.machinery.SourceFileLoader, importlib.machinery.SOURCE_SUFFIXES),
                (importlib.machinery.SourcelessFileLoader, importlib.machinery.BYTECODE_SUFFIXES),
                (importlib.machinery.ExtensionFileLoader, importlib.machinery.EXTENSION_SUFFIXES),
            ]
            finder = importlib.machinery.FileFinder(str(where), *loader_details)
            spec = finder.find_spec(name)
            logger.debug("loading module '%s' from '%s'", name, where)

        if not spec:
            raise ModuleNotFoundError
        return spec

    def load(self) -> None:
        """Load this module if not already loaded.

        The module is executed and registered in :data:`sys.modules`.
        If the module is a submodule, it is also set as an attribute on
        its parent package.

        Raises:
            ModuleNotFoundError: If the module specification
                cannot be found.
            ImportError: If loading the module fails.
        """
        if self.module:
            return
        if (module := importlib.util.module_from_spec(self._spec)) and self._spec.loader:
            try:
                sys.modules[str(self)] = module
                self._spec.loader.exec_module(module)
                if self._spec.parent:
                    setattr(sys.modules[self._spec.parent], self._name, module)
            except FileNotFoundError as e:
                raise ModuleNotFoundError from e
            else:
                return
        raise ImportError

    @property
    def pkg(self) -> str:
        """Returns the package name this module belongs to."""
        return self._pkg

    @property
    def root(self) -> str:
        """Returns the top package name this module belongs to."""
        return self._name if self._is_root else self._pkg.split(".")[0]

    @property
    def name(self) -> str:
        """Returns the name of this module without any prefixes."""
        return self._name

    @property
    def full_name(self) -> str:
        """Returns the full name of this module."""
        return f"{self._pkg}.{self.name}" if self._pkg else self.name

    @property
    def module(self) -> ModuleType | None:
        """Return the actual Module if loaded or None otherwise."""
        return sys.modules.get(str(self), None)

    @property
    def is_package(self) -> bool:
        """Returns True if this module is also a package."""
        return self._is_pkg

    @property
    def is_root(self) -> bool:
        """Returns True if this module is a top package."""
        return self._is_root

    def prefix_of(self, other: str) -> bool:
        """Check if this module is a package prefix of another module name.

        Returns ``True`` only if this module is a package and *other*
        is a direct submodule of it (not the package itself).

        Args:
            other (:obj:`str`): The module name to test against.

        Returns:
            :obj:`bool`: ``True`` if *other* is a submodule of this
            package.
        """
        prefix = f"{self!s}."
        return other != prefix and other.startswith(prefix) if self._is_pkg else False

    def share_root(self, other: str) -> bool:
        """Check if this module and another name share a common root package.

        Two module names share a root if their first dotted component
        is the same and nonempty.

        Args:
            other (:obj:`str`): The module name to compare against.

        Returns:
            :obj:`bool`: ``True`` if both names share the same top-level
            package prefix.
        """
        return other.split(".", maxsplit=1)[0] == self.root if self.root else False

    def __str__(self) -> str:
        return self.full_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self!s})"

    def __hash__(self) -> int:
        return hash((self.pkg, self.name))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and hash(other) == hash(self)


@final
class monkey:  # noqa: N801
    """Decorator-based monkey patcher for module attributes.

    This class provides a declarative way to register monkey patches.
    Each patch is defined by decorating a replacement function with a
    :class:`monkey` instance. Patches are stored globally and applied
    together via :meth:`apply_all`.

    When a patch is applied, the original attribute value is saved and
    can be retrieved later via :meth:`target`. Already-loaded modules
    that depend on the patched module are automatically marked for
    reload.

    Protected modules (``sys``, ``builtins``, ``importlib``,
    ``importlib.util``, ``__main__``) cannot be patched or reloaded.

    Args:
        module (:obj:`str`): The fully qualified name of the module
            containing the attribute to patch.
        target (:obj:`str`): The name of the attribute to replace.

    Examples::

        @monkey(module="os.path", target="join")
        def patched_join(*args):
            return "patched"

        monkey.apply_all()
    """

    _protected: ClassVar[set[str]] = {"sys", "builtins", "importlib", "importlib.util", "__main__"}
    _to_reload: ClassVar[set[str]] = set()
    _patches: ClassVar[dict[str, monkey]] = {}

    __slots__ = ("_module", "_origin", "_patch", "_target")

    def __init__(self, *, module: str, target: str):
        self._module: Module = Module(module)
        self._target: str = target
        self._patch: Patch = monkey._null_patch
        self._origin: Patchable = Unset
        monkey._patches[str(self)] = self

    def __call__(self, patch: Patch) -> Patch:  # noqa: D102
        self._patch = patch
        self._mark_modules()
        return patch

    def __str__(self) -> str:
        return f"{self._module}.{self._target}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self!s})"

    @classmethod
    def patches(cls) -> list[str]:
        """Return a list of all registered patched target names.

        Each name has the format ``"module.target"``.

        Returns:
            list[:obj:`str`]: The registered patch target names.
        """
        return [str(k) for k in monkey._patches]

    @classmethod
    def apply_all(cls) -> None:
        """Apply all registered patches and reload affected modules.

        Each patch is applied at most once. After all patches are
        applied, any modules marked for reload are re-imported.

        Raises:
            :exc:`RuntimeError`: If a protected module is encountered
                during the reload phase.
        """
        for patch in monkey._patches.values():
            if patch._origin is Unset:
                patch._apply()
        monkey._reload_modules()

    @classmethod
    def target(cls, name: str) -> Patchable:
        """Return the original unpatched target of a registered patch.

        Args:
            name (:obj:`str`): The patch target name in the format ``"module.target"``.

        Returns:
            :class:`Patchable`: The original attribute value before
            patching.

        Raises:
            RuntimeError: If called before any patch was applied.
            KeyError: If *name* is not a registered patch.
        """
        try:
            patch = monkey._patches[name]
        except KeyError as e:
            msg = f"{name} is not a known monkey patch."
            raise KeyError(msg) from e
        else:
            if patch._origin is Unset:
                msg = f"target for {patch!r} is not yet available, call monkey.apply_all() before."
                raise RuntimeError(msg)
            return patch._origin

    @classmethod
    def marks_modules(cls, *modules: str) -> None:
        """Mark module names for explicit reload during :meth:`apply_all`.

        This is useful when a module's behavior depends on a patched
        dependency but is not automatically detected by the patching
        mechanism.

        Args:
            *modules (:obj:`str`): Fully qualified module names to mark.

        Raises:
            ValueError: If a module is in the protected list (``sys``, ``builtins``,
                        ``importlib``, ``importlib.util``, or ``__main__``).
        """
        for mod in modules:
            if mod in monkey._protected:
                msg = f"{mod} belongs to protected module list, can't mark it"
                raise ValueError(msg)
            cls._to_reload.add(mod)

    def _apply(self) -> None:
        self._module.load()
        self._origin = getattr(self._module.module, self._target)
        setattr(self._module.module, self._target, self._patch)

    def _mark_modules(self) -> None:
        for mod_name in sys.modules:
            if mod_name == self._module.full_name:
                continue
            if self._module.prefix_of(mod_name) or self._module.share_root(mod_name):
                monkey._to_reload.add(mod_name)

    @classmethod
    def _reload_modules(cls) -> None:
        while monkey._to_reload:
            module = monkey._to_reload.pop()
            if module in monkey._protected:
                monkey._to_reload.clear()
                msg = f"{module} belongs to protected module list, can't reload it"
                raise RuntimeError(msg)
            importlib.reload(sys.modules[module])

    @staticmethod
    def _null_patch(*_a: Any, **_k: Any) -> Any:
        raise NotImplementedError
