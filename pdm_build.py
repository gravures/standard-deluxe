# Copyright (c) 2023 - Gilles Coissac
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
"""Pdm BuildHook module.

Implements pdm.backend.hooks.base.Base interface.

Monorepo Build
    usage: pdm build -C monorepo=<name>

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
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast


if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from pathlib import Path

    from pdm.backend.hooks import Context


logger = logging.getLogger("monorepo")


def get_monorepo(context: Context) -> dict[str, Any]:
    """Return the monorepo table."""
    try:
        monorepo: dict[str, Any] = context.config.data["tool"]["pdm"]["monorepo"]
    except KeyError:
        return {}
    else:
        return monorepo


def get_monorepos_targets(context: Context) -> list[str]:
    """Return the list of monorepo packages defined."""
    return list(get_monorepo(context).get("packages", {}).keys())


def get_monorepo_build_target(context: Context) -> str | None:
    """Return the name of a monorepo target passed to pdm build if exists."""
    cf = context.config_settings
    targets = get_monorepos_targets(context)

    logger.warning("MONOREPO %s", cf)
    logger.warning("MONOREPO Targets: %s", targets)

    if name := cf.get("monorepo"):
        if name in targets:
            return name
        msg = f"No monorepo package named '{name}' was found."
        raise ValueError(msg)
    return None


def deep_merge(
    *,
    target: MutableMapping[Any, Any],
    source: Mapping[Any, Any],
) -> MutableMapping[Any, Any]:
    """Merge the values of source in target."""
    for key, value in source.items():
        if key in target and isinstance(value, list):
            target[key].extend(value)
        elif key in target and isinstance(value, dict):
            _val = cast(Mapping[Any, Any], value)
            deep_merge(target=target[key], source=_val)
        else:
            target[key] = value
    return target


def update_config_for_monorepo(context: Context, package: str) -> None:
    """Update the config to meet settings of the selected monorepo package."""
    monorepo = get_monorepo(context)
    monorepo_conf: dict[str, Any] = monorepo["packages"][package]
    monorepo_metadata = monorepo_conf.pop("project", {})
    using_override = bool(monorepo.get("override", False))
    config = context.config
    build_config = context.config.build_config

    # Override build config
    build_config.update(monorepo_conf)
    logger.warning("MONOREPO build config")
    logger.warning(json.dumps(dict(build_config), indent=2))
    build_config["monorepo_build"] = True

    # Override or merge metadata
    if using_override:
        config.data["project"] = monorepo_metadata
    else:
        deep_merge(target=context.config.metadata, source=monorepo_metadata)
        # dependencies are already merged, restore them
        config.metadata["dependencies"] = monorepo_metadata.get("dependencies", [])
        config.metadata["optional-dependencies"] = monorepo_metadata.get(
            "optional-dependencies", {}
        )

    # removes monorepo table so sdist pyproject.toml
    # don't reference unavailable targets
    config.data["tool"]["pdm"].pop("monorepo")

    config.validate(data=config.data, root=config.root)
    logger.warning("MONOREPO metadata")
    logger.warning(json.dumps(dict(config.metadata), indent=2))


# ###################
# BuildHook interface
def pdm_build_hook_enabled(context: Context) -> bool:  # noqa: ARG001
    """Return True if the hook is enabled for the current build and context."""
    # return bool(get_monorepo(context).get("enabled"))
    return True


def pdm_build_clean(context: Context) -> None:  # noqa: ARG001
    """An optional clean step which will be called before the build starts."""
    return


def pdm_build_initialize(context: Context) -> None:
    """This hook will be called before the build starts.

    any updates to the context object will be seen by the following
    processes. It is recommended to modify the metadata in this hook.
    """
    if bool(context.config.build_config.get("monorepo_build", False)):
        # avoids recursive eecution
        return

    if not (target := get_monorepo_build_target(context)):
        return

    update_config_for_monorepo(context, target)


def pdm_build_update_setup_kwargs(context: Context, kwargs: dict[str, Any]) -> None:  # noqa: ARG001
    """Passed in the setup kwargs for hooks to update.

    Note:
            This hook will be called in the subprocess of running setup.py.
            Any changes made to the context won't be written back.
    """
    return


def pdm_build_update_files(context: Context, files: dict[str, Path]) -> None:  # noqa: ARG001
    """Passed in the current file mapping of {relpath: path} for hooks to update."""
    return


def pdm_build_finalize(context: Context, artifact: Path) -> None:  # noqa: ARG001
    """Called after the build is done, the artifact is the path to the built artifact."""
    return
