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
# This code was inspired from pyright-python node module:
#   https://github.com/RobertCraigie/pyright-python
#   Copyright 2021 Robert Craigie <https://github.com/RobertCraigie>
#   licensed under the MIT License
#
# ruff: noqa: D102, DOC201, DOC502, S603, PLR6301, PLW1510, RET505
"""Nodejs module.

Node module for managing Node.js environments and executing Node.js commands.

This module provides functionality to handle Node.js binaries, including
installation and version management, as well as executing commands in a
Node.js context. It supports different strategies for resolving Node.js
binaries, such as using global installations, nodeenv, or the nodejs_wheel
package.

Key Features:
- Manage Node.js and npm binaries.
- Install and configure nodeenv for isolated environments.
- Check and retrieve versions of Node.js packages.
- Provide a context manager for managing Node.js execution environments.

Exceptions:
- NodeError: Base class for all node-related exceptions.
- BinaryNotFoundError: Raised when a specified Node.js binary cannot be found.
- NodeInstallError: Raised when the installation of Node.js fails.
- VersionCheckFailedError: Raised when a version check for a target fails.

Usage:
To use this module, create an instance of the NodeContext class and
configure it as needed before running Node.js commands.

Example:
    with NodeContext() as ctx:
        ctx.target = Target.NPM
        result = ctx.run("your-package", "your-command")
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import platform
import re
import shutil
import subprocess as sp
import sys
from contextvars import Context, ContextVar, copy_context
from enum import Enum, unique
from functools import cache, lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, cast, final, overload

from deluxe.types import FilePath


if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import ModuleType, TracebackType

__all__ = (
    "BinaryNotFoundError",
    "NodeContext",
    "NodeError",
    "NodeInstallError",
    "Target",
    "VersionCheckFailedError",
    "get_pkg_version",
    "latest",
    "run",
    "version",
)

log: logging.Logger = logging.getLogger(__name__)


##
# Types and Exceptions
#
class NodeError(Exception):
    """Base Exception class for all node related errors."""

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BinaryNotFoundError(NodeError):
    """Raised when a node target cannot be found."""

    def __init__(self, target: Target, path: Path) -> None:
        super().__init__(
            f"Expected {target} binary to exist at {path} but was not found.",
        )
        self.path: Path = path
        self.target: Target = target


class NodeInstallError(NodeError):
    """Raised if node installation failed."""


class VersionCheckFailedError(NodeError):
    """Raised when a target's version cannot be checked."""


class _GlobalStrategy(NamedTuple):
    type: Literal["global"]
    path: Path


class _NodeJSWheelStrategy(NamedTuple):
    type: Literal["nodejs_wheel"]


class _NodeenvStrategy(NamedTuple):
    type: Literal["nodeenv"]
    path: Path


_Strategy = _GlobalStrategy | _NodeJSWheelStrategy | _NodeenvStrategy


@unique
class Target(Enum):
    """Enumeration of valid node targets."""

    NODE = "node"
    NPM = "npm"
    NPX = "npx"


##
#  utility functions
#
def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def get_usr_cache_dir() -> Path:
    # FIXME: use dirs module instead
    """Locate a user's cache directory.

    respects the XDG environment if present, otherwise defaults to `~/.cache`.
    """
    if xdg := os.environ.get("XDG_CACHE_HOME"):
        return Path(xdg)
    return Path.home() / ".cache"


def _postfix_for_target() -> str:
    if not _is_windows():
        return ""
    return ".exe" if _node_target.get() is Target.NODE else ".cmd"


def _maybe_decode(data: str | bytes) -> str:
    if isinstance(data, bytes):
        return data.decode(sys.getdefaultencoding())
    return data


@lru_cache(maxsize=1)
def _import_nodejs_wheel() -> ModuleType:
    if not importlib.util.find_spec(name="nodejs_wheel"):
        msg = "could not find nodejs_wheel module in system"
        log.critical(msg)
        raise ImportError(msg)

    from importlib import metadata  # noqa: PLC0415

    # NOTE: quick and dirty version check
    # require nodejs_wheel >= v20.13.1 for return_completed_process arg
    installed = [int(p) for p in metadata.version("nodejs_wheel").split(".")] + [0] * 3
    installed = tuple[int, int, int](installed[:3])
    if installed < (20, 13, 1):
        msg = f"require nodejs_wheel version (20,13,1), found {installed}"
        raise ImportError(msg)

    return importlib.import_module(name="nodejs_wheel")


##
# nodeenv functions
#
def _get_nodeenv_dir() -> Path:
    """Returns the directory that contains the nodeenv.

    It will be specified first respects the `cache_dir` argument
    if set and delegates to the system cache directory otherwise.
    """
    return Path(str(_node_cache_dir.get())) / "nodeenv"


def _ensure_nodeenv() -> Path:
    log.debug("Checking for nodeenv %s binary", _node_target.get())

    path = _get_nodeenv_path()
    log.debug("Using %s path for binary", path)

    if path.exists() and _node_version.get() is None:
        log.debug("Binary at %s exists, skipping nodeenv installation", path)
    else:
        log.debug("Installing nodeenv because a binary at %s could not be found", path)
        _install_nodeenv()

    if not path.exists():
        raise BinaryNotFoundError(path=path, target=_node_target.get())
    return path


def _get_nodeenv_path() -> Path:
    env_dir = Path(str(_nodeenv_dir.get()))
    bin_dir = env_dir / "Scripts" if _is_windows() else env_dir / "bin"
    target = str(_node_target.get())
    return bin_dir.joinpath(target + _postfix_for_target())


def _get_nodeenv_variables() -> dict[str, Any]:
    """Return the environment variables that should be passed to a binary."""
    # NOTE: I do not actually know if these result in the intended behaviour
    #       I simply copied them from bin/shim in nodeenv
    env_dir = Path(str(_nodeenv_dir.get()))
    return {
        "NODE_PATH": str(env_dir / "lib" / "node_modules"),
        "NPM_CONFIG_PREFIX": str(env_dir),
        "npm_config_prefix": str(env_dir),
    }


def _install_nodeenv() -> None:
    env_dir = _nodeenv_dir.get()
    log.debug("Installing nodeenv to %s", env_dir)
    args = [sys.executable, "-m", "nodeenv"]

    if version := _node_version.get():
        log.debug("Using user specified node version: %s", version)
        args += ["--node", version, "--force"]

    args.append(str(env_dir))
    log.debug("Running command with args: %s", args)

    try:
        sp.run(args, check=True)
    except sp.CalledProcessError as exc:
        msg = "nodeenv installation failed."
        raise NodeInstallError(msg) from exc


def _update_path_env(
    *, env: Mapping[str, str] | None, target_bin: Path, sep: str = os.pathsep
) -> str:
    """Returns a modified version of the `PATH` environment variable.

    It has been updated to include the location of the downloaded Node binaries.
    """  # noqa: DOC501
    if env is None:
        env = dict(os.environ)

    log.debug("Attempting to prepend %s to the PATH", target_bin)
    if not target_bin.exists():
        msg = f"Target directory {target_bin} does not exist"
        raise AttributeError(msg)

    path = env.get("PATH", "") or os.environ.get("PATH", "")
    if path:
        log.debug("Found PATH contents: %s", path)

        # handle the case where the PATH already starts
        # with the separator (this probably shouldn't happen)
        if path.startswith(sep):
            path = f"{target_bin.absolute()}{path}"
        else:
            path = f"{target_bin.absolute()}{sep}{path}"
    else:
        # handle the case where there is no PATH
        # set (unlikely / impossible to actually happen?)
        path = str(target_bin.absolute())

    log.debug("Using PATH environment variable: %s", path)
    return path


##
# Other strategy functions
#
def _get_global_binary() -> Path | None:
    log.debug("Checking for global target binary: %s", _node_target.get())

    path = _node_target.get().value + _postfix_for_target()

    which = shutil.which(path)
    if which is not None:
        log.debug("Found global binary at: %s", which)

        path = Path(which)
        if path.exists():
            log.debug("Global binary exists at: %s", which)
            return path

    log.debug("Global target binary: %s not found", _node_target.get().value)
    return None


def _resolve_strategy() -> _Strategy:
    if _node_use_nodejs_wheel.get() and importlib.util.find_spec("nodejs_wheel") is not None:
        log.debug("Using nodejs_wheel package for resolving binaries")
        return _NodeJSWheelStrategy(type="nodejs_wheel")

    if _node_use_global.get():
        path = _get_global_binary()
        if path is not None:
            log.debug("Using global %s binary", _node_target.get().value)
            return _GlobalStrategy(type="global", path=path)

    log.debug("Installing binaries using nodeenv")
    return _NodeenvStrategy(
        type="nodeenv",
        path=_ensure_nodeenv(),
    )


##
# Node Context Manager
#
_node_target = ContextVar[Target]("node_target", default=Target.NODE)
_node_cache_dir = ContextVar[FilePath[str]]("node_cache_dir", default=str(get_usr_cache_dir()))
_node_version = ContextVar[str | None]("node_version", default=None)
_node_use_nodejs_wheel = ContextVar[bool]("node_use_nodejs_wheel", default=True)
_node_use_global = ContextVar[bool]("node_use_global", default=True)
_nodeenv_dir = ContextVar[FilePath[str]]("nodeenv_dir", default=str(_get_nodeenv_dir()))


@final
class NodeContext:
    """Node Context manager.

    This class provides a context manager for Node.js execution environments.
    It allows configuration of various parameters such as the target Node.js version,
    the use of global installations, and the directory for nodeenv.

    Execution Strategies:
    - **Global**: Uses a globally installed Node.js binary if available.
    - **nodejs_wheel**: Utilizes the `nodejs_wheel <https://github.com/njzjz/nodejs-wheel/tree/master>`_
      package if installed, which provides a way to manage Node.js binaries as Python wheels,
      simplifying installation and usage.
    - **nodeenv**: Creates an isolated Node.js environment using the `nodeenv <https://github.com/ekalinin/nodeenv>`_
      package, which allows for the installation of Node.js and npm in a separate directory,
      avoiding conflicts with other Node.js installations on the system.

    Example:
        To use a global strategy you can configure the context as needed:

        >>> with NodeContext() as ctx:
        >>>    ctx.target = Target.NPM
        >>>    ctx.use_nodejs_wheel = False
        >>>    result = ctx.run("your-package", "your-command")


    Attributes:
        target (Target): The node target to use with this context.
        nodeenv_dir (PathLike): The nodeenv directory to use with this context.
        cache_dir (PathLike): The node cache directory to use with this context.
        use_version (str | None): The node version to use with this context.
        use_global (bool): Opt-in for system global node usage with this context.
        use_nodejs_wheel (bool): Opt-in for nodejs_wheel usage if installed with this context.

    Methods:
        run(*args: str, **kwargs: Any) -> sp.CompletedProcess[str | bytes]:
            Executes a command in the Node.js context.

        version() -> tuple[int, ...]:
            Returns the Node.js version within the current context target.

        latest(pkg: str) -> str:
            Returns the latest version for the given package within the current context.
    """

    def __init__(self) -> None:
        self._context: Context = copy_context()
        self.context: Context

    def __enter__(self) -> NodeContext:
        self.context = self.context.copy()
        return self

    def __exit__(
        self, t: type[BaseException] | None, i: BaseException | None, tb: TracebackType | None
    ) -> None:
        return

    @property
    def target(self) -> Target:
        """The node target to use with this context.

        Either Target.NODE or Target.NPM, default to Target.NODE.
        """
        return _node_target.get()

    @target.setter
    def target(self, val: Target) -> None:
        _node_target.set(val)

    @property
    def nodeenv_dir(self) -> FilePath[str]:
        """The nodeenv directory to use with this context.

        Only used if opt'in for a nodeenv strategy, default
        to <user_cache_directory/nodeenv>.
        """
        return _nodeenv_dir.get()

    @nodeenv_dir.setter
    def nodeenv_dir(self, val: FilePath[str]) -> None:
        if val:
            _nodeenv_dir.set(val)

    @property
    def cache_dir(self) -> FilePath[str]:
        """The node cache directory to use with this context.

        Default to XDG environment if present otherwise defaults to `~/.cache`.
        """
        return _node_cache_dir.get()

    @cache_dir.setter
    def cache_dir(self, val: FilePath[str]) -> None:
        _node_cache_dir.set(val)

    @property
    def use_version(self) -> str | None:
        """The node version to use with this context."""
        return _node_version.get()

    @use_version.setter
    def use_version(self, val: str | None) -> None:
        _node_version.set(val)

    @property
    def use_global(self) -> bool:
        """Opt'in for system global node usage with this context.

        Default to True if not explicitly set.
        """
        return _node_use_global.get()

    @use_global.setter
    def use_global(self, val: bool) -> None:
        _node_use_global.set(val)

    @property
    def use_nodejs_wheel(self) -> bool:
        """Opt'in for nodejs_wheel usage if installed with this context.

        If nodejs_wheel is not available, context execution will use
        the global node environment if NodeContext.use_global is set
        to True. In last ressort a nodeenv strategy will be used.

        Default to True if not explicitly set.
        """
        return _node_use_nodejs_wheel.get()

    @use_nodejs_wheel.setter
    def use_nodejs_wheel(self, val: bool) -> None:
        _node_use_nodejs_wheel.set(val)

    @overload
    def run(
        self,
        *args: str,
        input: bytes | None = None,
        text: Literal[False],
        **kwds: Any,
    ) -> sp.CompletedProcess[bytes]: ...
    @overload
    def run(
        self,
        *args: str,
        input: str | None = None,
        text: Literal[True] = True,
        **kwds: Any,
    ) -> sp.CompletedProcess[str]: ...
    def run(
        self,
        *args: str,
        input: str | bytes | None = None,  # noqa: A002
        text: bool = True,
        **kwds: Any,
    ) -> sp.CompletedProcess[str] | sp.CompletedProcess[bytes]:
        return run(*args, input=input, text=text, **kwds)  # pyright: ignore[reportCallIssue, reportUnknownVariableType, reportArgumentType]

    def version(self) -> tuple[int, ...]:
        return self.context.run(version)

    def latest(self, pkg: str) -> str:
        return self.context.run(latest, pkg)


##
# Module API
#
@overload
def run(
    *args: str,
    input: bytes | None = None,
    text: Literal[False],
    **kwds: Any,
) -> sp.CompletedProcess[bytes]: ...
@overload
def run(
    *args: str,
    input: str | None = None,
    text: Literal[True] = True,
    **kwds: Any,
) -> sp.CompletedProcess[str]: ...
def run(
    *args: str,
    input: str | bytes | None = None,  # noqa: A002
    text: bool = True,
    **kwds: Any,
) -> sp.CompletedProcess[str] | sp.CompletedProcess[bytes]:
    """Run a nodejs command with arguments and return a CompletedProcess instance.

    The current :py:class:`NodeContext` is used to choose the execution method.
    Parameters are the same as the :py:func:`subprocess.run` function.

    Raises:
        BinaryNotFoundError: if a nodeenv binary could not be found
                      for the specified target and env_dir.
        NodeInstallError: if nodeenv failed to install a node.js binary
                      in regard of env_dir, cache_dir and NODE_VERSION
        ImportError: if nodejs_wheel strategy is requested an the module
                     is not on the path.
    """
    strategy = _resolve_strategy()

    if strategy.type == "global":
        node_args = [str(strategy.path), *args]
        log.debug("Running global node command with args: %s", node_args)
        cp: sp.CompletedProcess[str] | sp.CompletedProcess[bytes] = sp.run(
            node_args, input=input, text=text, **kwds
        )
        return cp

    elif strategy.type == "nodejs_wheel":
        nodejs_wheel = _import_nodejs_wheel()
        match _node_target.get():
            case Target.NODE:
                cp = nodejs_wheel.node(
                    args, return_completed_process=True, input=input, text=text, **kwds
                )
            case Target.NPM:
                cp = nodejs_wheel.npm(
                    args, return_completed_process=True, input=input, text=text, **kwds
                )
            case Target.NPX:
                cp = nodejs_wheel.npx(
                    args, return_completed_process=True, input=input, text=text, **kwds
                )
        return cp

    else:  # strategy.type == "nodeenv"
        env = kwds.pop("env", None) or os.environ.copy()
        env.update(_get_nodeenv_variables())

        # If we're using `nodeenv` to resolve the node binary then we also need
        # to ensure that `node` is in the PATH so that any install scripts that
        # assume it is present will work.
        try:
            env.update(PATH=_update_path_env(env=env, target_bin=strategy.path.parent))
        except AttributeError as err:
            raise BinaryNotFoundError(_node_target.get(), strategy.path) from err

        node_args = [str(strategy.path), *args]
        log.debug("Running nodeenv command with args: %s", node_args)
        return cast(
            "sp.CompletedProcess[str] | sp.CompletedProcess[bytes]",
            sp.run(node_args, env=env, input=input, text=text, **kwds),
        )


_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def version() -> tuple[int, ...]:
    """Returns the node versions within the current context target.

    Raises:
        VersionCheckFailedError: if the node version could not be found.
    """
    proc = run("--version", stdout=sp.PIPE, stderr=sp.STDOUT)
    output = _maybe_decode(proc.stdout)
    match = _VERSION_RE.search(output)
    if not match:
        sys.stderr.write(output)
        msg = (
            f"Could not find version from `{_node_target.get().value} --version`, see output above"
        )
        raise VersionCheckFailedError(msg)

    info = tuple(int(value) for value in match.group(0).split("."))
    log.debug("Version check for %s returning %s", _node_target.get().value, info)
    return info


@cache
def latest(pkg: str) -> str:
    """Return the latest version for the given package within the current context.

    Raises:
        VersionCheckFailedError: if the pkg version could not be found.
    """
    token = _node_target.set(Target.NPM)
    proc = run("info", pkg, "version", stdout=sp.PIPE, stderr=sp.STDOUT)
    _node_target.reset(token)
    stdout = _maybe_decode(proc.stdout)

    if proc.returncode != 0:
        sys.stderr.write(stdout)
        msg = f"Version check for {pkg} failed, see output above."
        raise VersionCheckFailedError(msg)

    match = _VERSION_RE.search(stdout)
    if not match:
        sys.stderr.write(stdout)
        msg = f"Could not find version for {pkg}, see output above"
        raise VersionCheckFailedError(msg)

    value = match.group(0)
    log.debug("Version check for %s returning %s", pkg, value)
    return value


def get_pkg_version(pkg: Path) -> str | None:
    """Given a path to a `package.json` file, parse it and returns the `version` property.

    Returns:
        `None` if the version could not be resolved for any reason.
    """
    if not pkg.exists():
        return None

    try:
        data = json.loads(pkg.read_text(encoding=sys.getdefaultencoding()))
    except OSError:
        # TODO: test this
        log.debug("Ignoring error while reading/parsing the %s file", pkg, exc_info=True)
        return None
    return data.get("version")
