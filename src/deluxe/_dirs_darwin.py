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
# ruff: noqa: PIE796
from __future__ import annotations

from enum import Enum
from pathlib import Path

from deluxe._dirs_meta import _Meta  # pyright: ignore[reportPrivateUsage]


class Base(Path, Enum, metaclass=_Meta):
    cache = ("Library", "Caches")
    config = ("Library", "Application Support")
    config_local = config
    data = config
    data_local = config
    preference = ("Library", "Preferences")
    state = cache
    runtime = cache


class ProjectPath(Path):
    def __call__(self, name: str) -> Path: ...


class Project(ProjectPath, Enum, metaclass=_Meta): ...


class User(Enum): ...
