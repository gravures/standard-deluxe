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
# This code was adapted from the "pdm-mina" program, originally
# written by Grey Elaina and publish under the MIT license, see
# <https://github.com/GreyElaina/Mina>.
#
# ruff: noqa: INP001
"""A Pdm BuildHook to export sub-packages as independent distributions.

Namespace pakckage build
------------------------

    usage: pdm build -C namespace=<name>

The `-C` flag can be set multiple times.

Implementation detail
---------------------

Implements the pdm.backend.hooks.base.Base interface.

NOTE: The Context object attributes
    build_dir: The build directory for storing built files
    dist_dir:  The directory to store the built artifacts
    kwargs:    The extra args passed to the build method
    builder:   The builder associated with this build context
    config:    The parsed pyproject.toml as a Config
    root:      The project root directory as Path
    target:    The target to build, one of 'sdist', 'wheel', 'editable'
    config_settings: The config settings passed to the hook as a dict.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, cast


if TYPE_CHECKING:
    from pathlib import Path

    from pdm.backend.hooks import Context


logger = logging.getLogger("namespace-pkg")


def get_namespace_packages(context: Context) -> dict[str, dict[str, object]]:
    """Returns the namespace table.

    Raises:
        TypeError: if user does not defined packages as a dictionary.
    """
    try:
        namespace = context.config.data["tool"]["pdm"]["namespace"]
    except KeyError:
        return {}

    if not isinstance(namespace, dict):
        msg = "tool.pdm.namespace.packages should be a table."
        raise TypeError(msg)

    return cast("dict[str, dict[str, object]]", namespace)


def get_namespace_targets(context: Context) -> list[str]:
    """Returns a list of defined namespace-packages name."""
    packages = get_namespace_packages(context).get("packages", {})
    return list(packages.keys())


def get_namespace_build_target(context: Context) -> str | None:
    """Returns the name of a namespace target passed to pdm build if exists.

    Raises:
        ValueError: if a defined namespace package could not be found.
    """
    cf = context.config_settings
    targets = get_namespace_targets(context)

    logger.warning("NAMESPACE %s", cf)
    logger.warning("NAMESPACE Targets: %s", targets)

    if name := cf.get("namespace"):
        if name in targets:
            return name
        msg = f"No namespace package named '{name}' was found."
        raise ValueError(msg)
    return None


def deep_merge(
    *,
    target: dict[str, object | list[object]],
    source: dict[str, object | list[object]],
) -> dict[str, object | list[object]]:
    """Merge deeply the values of source in target.

    Returns:
        Mapping: the updated target.

    Raises:
        TypeError:
    """
    for key, value in source.items():
        if key in target:
            if isinstance(value, list):
                common = target[key]
                if isinstance(common, list):
                    common = cast("list[object]", common)
                    common += cast("list[object]", value)
                    continue
                break
            if isinstance(value, dict):
                common = target[key]
                if isinstance(common, dict):
                    common = cast("dict[str, object]", common)
                    val_ = cast("dict[str, object]", value)
                    deep_merge(target=common, source=val_)
                    continue
                break
        target[key] = value
    else:
        return target

    msg = f"discrepancy in key `{key}` type between root metadata and namespace metadata."
    raise TypeError(msg)


def update_config_for_namespace_package(context: Context, package: str) -> None:
    """Update the config to meet settings of the selected namespace package.

    Raises:
        TypeError: if user defined properties with wrong type
    """
    namespace = get_namespace_packages(context)

    package_config = namespace["packages"][package]
    if not isinstance(package_config, dict):
        msg = "tool.pdm.namespace.packages.<name> should be a table of metadata."
        raise TypeError(msg)
    package_config = cast("dict[str, object]", package_config)

    package_metadata = package_config.pop("project", {})
    if not isinstance(package_metadata, dict):
        msg = "tool.pdm.namespace.packages.<name>.project should be a table of metadata."
        raise TypeError(msg)
    package_metadata = cast("dict[str, object]", package_metadata)

    use_override = bool(namespace.get("override", False))
    config = context.config
    build_config = context.config.build_config

    # Override build config
    build_config.update(package_config)
    logger.warning("NAMESPACE build config")
    logger.warning(json.dumps(dict(build_config), indent=2))

    # safe-guard property
    build_config["namespace_build"] = True

    # Override or merge metadata
    if use_override:
        config.data["project"] |= package_metadata
    else:
        deep_merge(target=context.config.metadata, source=package_metadata)
        # dependencies are already merged, restore them
        config.metadata["dependencies"] = package_metadata.get("dependencies", [])
        config.metadata["optional-dependencies"] = package_metadata.get(
            "optional-dependencies", {}
        )

    # removes namespace table so sdist pyproject.toml
    # don't reference unavailable targets
    config.data["tool"]["pdm"].pop("namespace")

    # config.validate(data=config.data, root=config.root)
    config.validate()

    logger.warning("NAMESPACE metadata")
    logger.warning(json.dumps(dict(config.metadata), indent=2))


# ###################
# BuildHook interface
def pdm_build_hook_enabled(_context: Context) -> bool:
    """Return True if the hook is enabled for the current build and context."""
    # return bool(get_namespace(context).get("enabled"))
    return True


def pdm_build_clean(_context: Context) -> None:
    """An optional clean step which will be called before the build starts."""
    return


def pdm_build_initialize(context: Context) -> None:
    """This hook will be called before the build starts.

    any updates to the context object will be seen by the following
    processes. It is recommended to modify the metadata in this hook.
    """
    if bool(context.config.build_config.get("namespace_build", False)):
        # avoids recursive eecution
        return

    if not (target := get_namespace_build_target(context)):
        return

    update_config_for_namespace_package(context, target)


def pdm_build_update_setup_kwargs(_context: Context, _kwargs: dict[str, object]) -> None:
    """Passed in the setup kwargs for hooks to update.

    Note:
            This hook will be called in the subprocess of running setup.py.
            Any changes made to the context won't be written back.
    """
    return


def pdm_build_update_files(_context: Context, _files: dict[str, Path]) -> None:
    """Passed in the current file mapping of {relpath: path} for hooks to update."""
    return


def pdm_build_finalize(_context: Context, _artifact: Path) -> None:
    """Called after the build is done, the artifact is the path to the built artifact."""
    return
