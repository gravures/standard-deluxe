# Copyright (c) 2025 - Gilles Coissac
#
# pdm_build is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# pdm_build is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pdm_build. If not, see <https://www.gnu.org/licenses/>
#
"""A Pdm BuildHook to build cython extension modules.

Namespace package build
------------------------

    usage: pdm build


Implementation detail
=====================

Implements the `pdm.backend.hooks.base.Bases` Protocol (BuildHookInterface):
    * pdm_build_hook_enabled(context)
    * pdm_build_clean(context)
    * pdm_build_initialize(context)
    * pdm_build_update_setup_kwargs(context, kwargs)
    * pdm_build_update_files(context, files)
    * pdm_build_finalize(context, artifact)


Pdm Backend Context Content
===========================

The Context object attributes
    build_dir: The build directory for storing built files
    dist_dir:  The directory to store the built artifacts
    kwargs:    The extra args passed to the build method
    builder:   The builder associated with this build context
    config:    The parsed pyproject.toml as a Config object
    root:      The project root directory as Path
    target:    The target to build, one of 'sdist', 'wheel', 'editable'
    config_settings: The config settings passed to the hook as a dict

The Context.config attributes
    data: pyproject.toml parsed as a mapping
    metadata: the project metadata from the project table
    build_config: the build config from the tool.pdm.build table

Te Context.config.BuildConfig (The [tool.pdm.build] table)
    custom_hook property:  The relative path to the custom hook or None
                           if not exists
    editable_backend property: Currently only two backends are supported:
        - editables: Proxy modules via editables
        - path: the legacy .pth file method(default)

    excludes property: the excludes setting
    includes property: the includes setting
    is_purelib property: if not explicitly set, the project is considered
                         to be non-pure if build exists.
    package_dir property: directory that will be used to looking for packages.
    run_setuptools property: whether to run setuptools
    source_includes: the source-includes setting
    wheel_data property: the wheel data configuration
"""

from __future__ import annotations

import io
import json
import logging
import multiprocessing
import shutil
import subprocess as sp
import sys
from contextlib import redirect_stderr
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never, TypeVar, cast

from Cython.Build import cythonize  # pyright: ignore[reportUnknownVariableType]
from Cython.Build.Dependencies import (
    create_extension_list,  # pyright: ignore[reportUnknownVariableType]
)
from Cython.Compiler import Options
from Cython.Compiler.Errors import CompileError
from pdm.backend.config import Config  # noqa: F401
from setuptools import Extension


if TYPE_CHECKING:
    from collections.abc import Mapping

    from pdm.backend.hooks import Context


if __name__ == "_local":
    # Hacks to overcome pdm-backend not registering us as a module
    # making dataclasses creation broken
    from importlib import util

    sys.modules[__name__] = util.module_from_spec(__spec__)


logger = logging.getLogger("pdm-build-cython")


def color(color: int) -> str:  # noqa: D103
    return f"\x1b[{color}m"


def reset() -> str:  # noqa: D103
    return "\x1b[0m"


def info(msg: str, *args: Any) -> None:  # noqa: D103
    msg = f"[{color(32)}pdm-build-cython{reset()}]: {msg}"
    logger.warning(msg, *args)


_T = TypeVar("_T")


def lookup(path: str, namespace: Mapping[str, object], default: _T) -> _T:
    """Lookup recursively for property in a namespace given a dotted path.

    Returns:
        the found property annotated as `default` argument's type
        or `default` itself if property is not defined.

    Raises:
        LookupError: if any parts of `path` (excluding the last one) do not exists.
    """
    key = None
    parts = path.split(".")

    try:
        for key in parts[:-1]:
            namespace = namespace[key]  # pyright: ignore[reportAssignmentType]
    except KeyError as err:
        msg = f"pyproject does not contain a <{key}> section."
        raise LookupError(msg) from err
    else:
        try:
            result = namespace[parts[-1]]
        except LookupError:
            result = default
    return cast("_T", result)


def get_pkg_lib(library: str) -> str:  # noqa: D103
    args = ["pkg-config", "--short-errors", "--libs-only-l", library]
    try:
        cp = sp.run(args, shell=False, check=True, text=True, capture_output=True)  # noqa: S603
    except sp.CalledProcessError as e:
        print(f"pkg-config error: {e.stderr}")  # noqa: T201
        name = ""
    else:
        name = cp.stdout.replace("-l", "").strip()
    logger.info("pkg-config lib:%s", name)
    return name


@dataclass
class ExtensionParams:
    """Parameters for `distutils.Extension`.

    * include_dirs: list of directories to search for C/C++ header files
      (in Unix form for portability)

    * define_macros: list of macros to define; each macro is defined using a 2-tuple:
      the first item corresponding to the name of the macro and the second
      item either a string with its value or None to define it without
      a particular value (equivalent of "#define FOO" in source or -DFOO
      on Unix C compiler command line)

    * undef_macros: list of macros to undefined explicitly

    * library_dirs: list of directories to search for C/C++ libraries at link time

    * libraries: list of library names (not filenames or paths) to link against

    * runtime_library_dirs: list of directories to search for C/C++
      libraries at run time (for shared extensions, this is when the extension
      is loaded). Setting this will cause an exception during build on Windows
      platforms.

    * extra_objects: list of extra files to link with
      (eg. object files not implied by 'sources', static library that
      must be explicitly specified, binary resource files, etc.)

    * extra_compile_args: any extra platform- and compiler-specific
      information to use when compiling the source files in 'sources'.
      For platforms and compilers where "command line" makes sense,
      this is typically a list of command-line arguments, but for other
      platforms it could be anything.

    * extra_link_args: any extra platform- and compiler-specific information
      to use when linking object files together to create the extension
      (or to create a new static Python interpreter). Similar
      interpretation as for 'extra_compile_args'.

    * export_symbols:
      list of symbols to be exported from a shared extension.  Not
      used on all platforms, and not generally necessary for Python
      extensions, which typically export exactly one symbol: "init" +
      extension_name.

    * swig_opts: any extra options to pass to SWIG if a source file has the .i
      extension.

    * depends: list of files that the extension depends on

    * language: extension language (i.e. "c", "c++", "objc"). Will be detected
      from the source extensions if not provided.

    * optional: specifies that a build failure in the extension should
      not abort the build process, but simply not install the failing extension.

    * py_limited_api: opt-in flag for the usage of `Python's limited API`
    """

    include_dirs: list[str] = field(default_factory=list)
    define_macros: list[tuple[str, str]] = field(default_factory=list)
    undef_macros: list[str] = field(default_factory=list)
    library_dirs: list[str] = field(default_factory=list)
    librairies: list[str] = field(default_factory=list)
    runtime_library_dirs: list[str] = field(default_factory=list)
    extra_objects: list[str] = field(default_factory=list)
    extra_compile_args: list[str] = field(default_factory=list)
    extra_links_args: list[str] = field(default_factory=list)
    export_symbols: list[str] = field(default_factory=list)
    swig_opts: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    language: str | None = None
    optional: bool = False
    py_limited_api: bool = False

    def __post_init__(self) -> None:
        new_define_macros: list[tuple[str, str]] = []
        for macro in self.define_macros:
            new_define_macros.append((macro[0], macro[1]))  # noqa: PERF401
        self.define_macros = new_define_macros


@dataclass
class _Extension:
    name: str
    sources: list[str]


@dataclass
class CythonExtensionParams(ExtensionParams, _Extension):
    """Interface for `tool.cython.cythonize.extensions` list of table and `distutils.Extension`.

    * name: the full name of the extension, including any packages -- ie.
      *not* a filename or pathname, but Python dotted name

    * sources: list of source filenames, relative to the distribution root
      (where the setup script lives), in Unix form (slash-separated)
      for portability.  Source files may be C, C++, SWIG (.i),
      platform-specific resource files, or whatever else is recognized
      by the "build_ext" command as source for a Python extension.
    """


def path_from_str(path: str):  # noqa: D103
    # TODO: do we want to handle `./src` location here?
    return Path(path)


def cython_extensions_params_from_patterns(  # noqa: D103
    patterns: list[str],
    exclude: list[str] | None,
) -> list[CythonExtensionParams]:
    # NOTE: Lets cython resolved patterns string to name and sources
    extensions, _metadata = cast(
        "tuple[list[Extension], dict[str, object]]",
        create_extension_list(
            patterns,
            exclude=exclude,
            ctx=None,
            aliases=None,
            quiet=True,
            language=None,
            exclude_failures=False,
        ),
    )
    result: list[CythonExtensionParams] = []
    for ext in extensions:
        result.append(CythonExtensionParams(ext.name, ext.sources))  # noqa: PERF401
    return result


def parse_extensions(extensions: Any, exclude: list[str]) -> list[CythonExtensionParams]:
    """Returns a list of CythonBuildExtensions.

    Parsed parameters should come from `tool.cython.cythonize.extensions` property.

    Raises: `ValueError` for invalid parameter.
    """
    logger.debug("Extensions: %s", json.dumps(extensions, indent=2))

    def raise_value_error(hint: str = "") -> Never:
        msg = (
            "'tool.cython.cythonize.extensions' should either be a string, a list of string"
            f" or a list of table(dict) with 'distutils.Extension valid parameters`{hint}"
        )
        raise ValueError(msg)

    if isinstance(extensions, str):
        return cython_extensions_params_from_patterns([extensions], exclude)

    if not isinstance(extensions, list):
        raise_value_error(f", got `{type(extensions).__name__}`")

    result: list[CythonExtensionParams] = []
    exts = cast("list[object]", extensions)
    for ext in exts:
        if isinstance(ext, str):
            result.extend(cython_extensions_params_from_patterns([ext], exclude))
        elif isinstance(ext, dict):
            try:
                result.append(CythonExtensionParams(**ext))  # pyright: ignore[reportUnknownArgumentType]
            except TypeError as err:
                raise_value_error(f", {err!s}")
        else:
            raise_value_error(f", got `{ext}`")
    return result


def get_distutils_extensions(context: Context) -> list[Extension]:
    """Returns a list of distutils.Extension.

    Parameters are merged from global `tool.cython.build` table
    and each extensions item itself.
    """
    data = context.config.data
    return [
        Extension(
            **(
                asdict(
                    ExtensionParams(
                        **lookup("tool.cython.build", data, {}),
                    )
                )
                | asdict(ext)
            )
        )
        for ext in parse_extensions(
            lookup("tool.cython.cythonize.extensions", data, []),
            lookup("tool.cython.cythonize.exclude", data, []),
        )
    ]


def cythonize_extensions(context: Context) -> list[Extension]:
    """Cythonize extensions sources files.

    Returns:
        A list of `distutils.Extensions`.

    Raises:
        CompileError: if transpilation failed.
    """
    tool: dict[str, object] = lookup("tool", context.config.data, {})

    # copy the cythonize table to not mutate the context
    settings = deepcopy(
        lookup("tool.cython.cythonize", context.config.data, {}),
    )

    # return fast if no extensions were defined
    if "extensions" not in settings or not settings.pop("extensions"):
        return []

    # extension handling
    extensions = get_distutils_extensions(context)

    # multi-threading
    nthreads = int(settings.pop("nthreads", 0))
    cores = multiprocessing.cpu_count() - 1
    nthreads = cores if nthreads < 1 else min(cores, nthreads)

    # compiler directives
    settings.pop("compiler_directives", None)
    directives = lookup("cython.compiler.directives", tool, {})
    logger.debug("Compiler Directives: %s", json.dumps(directives, indent=2))

    # setup cython.Options
    for key, value in lookup("options", tool, {}).items():
        setattr(Options, key, value)

    # Optional redirection of cython compilation errors in file
    log_errors = lookup("cython.log_errors", tool, "")
    redirect = io.StringIO()

    with redirect_stderr(redirect):
        try:
            cythonize(
                module_list=extensions,
                nthreads=nthreads,
                compiler_directives=directives,
                **settings,
            )
        except CompileError:
            # hint = ""
            errors = redirect.getvalue()
            if log_errors:
                Path(log_errors).write_text(errors, encoding="UTF-8")

            raise CompileError(message=errors) from None

    return extensions


#########################
# BuildHookinterface
#
def pdm_build_hook_enabled(context: Context) -> bool:
    """Return True if the hook is enabled for the current build and context."""
    return lookup("tool.cython.enabled", context.config.data, default=False)


def pdm_build_clean(_context: Context) -> None:
    """An optional clean step which will be called before the build starts."""
    return


def pdm_build_initialize(context: Context) -> None:
    """This hook will be called before the build starts.

    any updates to the context object will be seen by the following
    processes. It is recommended to modify the metadata in this hook.
    """
    build_target = context.target
    info("build target -> %s", build_target)

    if context.target == "wheel":
        return  # avoids multiple executions

    info("cythonizing extensions...")
    if not (extensions := cythonize_extensions(context)):
        info("no extension found, nothing to do")
        return

    info("cythonized extensions -> %s", [ext.name for ext in extensions])

    # update the [pdm.build] table
    build_config = context.config.build_config
    build_config["is-purelib"] = False
    build_config["run-setuptools"] = True
    if context.config_settings.get("in-place"):
        build_config["editable_root"] = str(context.root)
    context.config.validate()


def pdm_build_update_setup_kwargs(context: Context, setup_kwargs: dict[str, object]) -> None:
    """Passed in the setup kwargs for hooks to update.

    Note:
            This hook will be called in the subprocess of running setup.py.
            Any changes made to the context won't be written back.
    """
    if extensions := get_distutils_extensions(context):
        info("building cython extensions....")
        setup_kwargs.update(ext_modules=extensions)


def pdm_build_update_files(context: Context, _files: dict[str, Path]) -> None:
    """Passed in the current file mapping of {relpath: path} for hooks to update."""
    if context.target != "wheel" or context.config_settings.get("in-place") is None:
        return

    src = Path(
        context.config.build_config["editable_root"], context.config.build_config.package_dir
    )
    objects = list(Path(context.build_dir).glob("**/*.so"))

    for obj in objects:
        dest = src / obj.relative_to(context.build_dir)
        info("copying extension in-place to '%s'", dest)
        shutil.copy(obj, dest)


def pdm_build_finalize(_context: Context, _artifact: Path) -> None:
    """Called after the build is done, the artifact is the path to the built artifact."""
    return
