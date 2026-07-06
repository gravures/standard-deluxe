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
# ruff: noqa: PTH118, PLR6301
from __future__ import annotations

import enum
import os
from pathlib import Path
from typing import Final

from deluxe._dirs_meta import BaseEnum, ProjectEnum


_home: Final[str] = str(Path.home())


class Base(BaseEnum):
    cache = os.getenv("XDG_CACHE_HOME") or os.path.join(_home, ".cache")
    config = os.getenv("XDG_CONFIG_HOME") or os.path.join(_home, ".config")
    config_local = config
    data = os.getenv("XDG_DATA_HOME") or os.path.join(_home, ".local", "share")
    data_local = data
    preference = config
    state = os.getenv("XDG_STATE_HOME") or os.path.join(_home, ".local", "state")
    runtime = os.getenv("XDG_RUNTIME_DIR") or state  # TODO: should warn if not set


class Project(ProjectEnum):
    @enum.member
    def cache(self, name: str) -> str:
        return os.path.join(Base.cache, name)

    @enum.member
    def config(self, name: str) -> str:
        return os.path.join(Base.config, name)

    @enum.member
    def config_local(self, name: str) -> str:
        return os.path.join(Base.config_local, name)

    @enum.member
    def data(self, name: str) -> str:
        return os.path.join(Base.data, name)

    @enum.member
    def data_local(self, name: str) -> str:
        return os.path.join(Base.data_local, name)

    @enum.member
    def preference(self, name: str) -> str:
        return os.path.join(Base.preference, name)

    @enum.member
    def state(self, name: str) -> str:
        return os.path.join(Base.state, name)

    @enum.member
    def runtime(self, name: str) -> str:
        return os.path.join(Base.runtime, name)


# class User(Enum): ...
