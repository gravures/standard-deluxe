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
# ruff: noqa: RUF001
"""Provides platform-specific, user-accessible locations.

:py:mod:`dirs` is a simple module that provides the platform-specific, user-accessible
locations for finding and storing configuration, cache and other data following
the respective conventions on Linux, macOS, BSD and Windows.

This module provides the location of those directories by leveraging the mechanisms defined by:
    - the `XDG base directory <https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_
      and the `XDG user directory <https://www.freedesktop.org/wiki/Software/xdg-user-dirs/>`_
      specifications on Linux,
    - the `Known Folder <https://msdn.microsoft.com/en-us/library/windows/desktop/bb776911(v=vs.85).aspx>`_ system on Windows, and
    - the `Standard Directories <https://developer.apple.com/library/content/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileSystemOverview/FileSystemOverview.html#//apple_ref/doc/uid/TP40010672-CH2-SW6>`_ on macOS.

This module was largely inspired by the eponym rust library `directories.rs <https://codeberg.org/dirs/directories-rs>`_.
"""  # noqa: E501

# NOTE: see platformdirs

from __future__ import annotations

from deluxe._dirs_meta import ProjectPath
from deluxe.availability import supported


if supported(only="linux"):
    from deluxe._dirs_linux import Base, Project
elif supported(only="darwin"):
    from deluxe._dirs_darwin import Base
else:
    from deluxe._dirs_nt import Base, Project

__all__ = ("Base", "Project", "ProjectPath")

Base.__doc__ = """Provides paths of user standard directories.

Following the conventions of the operating system the library is running on.
To compute the location of cache, config or data directories for individual
projects or applications, use :py:class:`Project` instead.
"""

Base.cache.__doc__ = r"""The path to the user's cache directory.
|Platform | Value                               | Example                      |
| ------- | ----------------------------------- | ---------------------------- |
| Linux   | `$XDG_CACHE_HOME` or `$HOME`/.cache | /home/alice/.cache           |
| macOS   | `$HOME`/Library/Caches              | /Users/Alice/Library/Caches  |
| Windows | `{FOLDERID_LocalAppData}`           | C:\Users\Alice\AppData\Local |
"""

Base.config.__doc__ = r"""The path to the user's config directory.

|Platform | Value                                 | Example                                  |
| ------- | ------------------------------------- | ---------------------------------------- |
| Linux   | `$XDG_CONFIG_HOME` or `$HOME`/.config | /home/alice/.config                      |
| macOS   | `$HOME`/Library/Application Support   | /Users/Alice/Library/Application Support |
| Windows | `{FOLDERID_RoamingAppData}`           | C:\Users\Alice\AppData\Roaming           |
"""

Base.config_local.__doc__ = r"""The path to the user's local config directory.

|Platform | Value                                 | Example                                  |
| ------- | ------------------------------------- | ---------------------------------------- |
| Linux   | `$XDG_CONFIG_HOME` or `$HOME`/.config | /home/alice/.config                      |
| macOS   | `$HOME`/Library/Application Support   | /Users/Alice/Library/Application Support |
| Windows | `{FOLDERID_LocalAppData}`             | C:\Users\Alice\AppData\Local             |
"""

Base.data.__doc__ = r"""The path to the user's data directory.

|Platform | Value                                    | Example                                  |
| ------- | ---------------------------------------- | ---------------------------------------- |
| Linux   | `$XDG_DATA_HOME` or `$HOME`/.local/share | /home/alice/.local/share                 |
| macOS   | `$HOME`/Library/Application Support      | /Users/Alice/Library/Application Support |
| Windows | `{FOLDERID_RoamingAppData}`              | C:\Users\Alice\AppData\Roaming           |
"""

Base.data_local.__doc__ = r"""The path to the user's local data directory.

|Platform | Value                                    | Example                                  |
| ------- | ---------------------------------------- | ---------------------------------------- |
| Linux   | `$XDG_DATA_HOME` or `$HOME`/.local/share | /home/alice/.local/share                 |
| macOS   | `$HOME`/Library/Application Support      | /Users/Alice/Library/Application Support |
| Windows | `{FOLDERID_LocalAppData}`                | C:\Users\Alice\AppData\Local             |
"""

Base.preference.__doc__ = r"""The path to the user's preference directory.

|Platform | Value                                 | Example                          |
| ------- | ------------------------------------- | -------------------------------- |
| Linux   | `$XDG_CONFIG_HOME` or `$HOME`/.config | /home/alice/.config              |
| macOS   | `$HOME`/Library/Preferences           | /Users/Alice/Library/Preferences |
| Windows | `{FOLDERID_RoamingAppData}`           | C:\Users\Alice\AppData\Roaming   |
"""

Base.runtime.__doc__ = r"""The path to the user's runtime directory.

|Platform | Value              | Example         |
| ------- | ------------------ | --------------- |
| Linux   | `$XDG_RUNTIME_DIR` | /run/user/1001/ |
| macOS   | –                  | –               |
| Windows | –                  | –               |
"""

Base.state.__doc__ = r"""The path to the user's state directory.

The state directory contains data that should be retained between sessions (unlike the runtime
directory), but may not be important/portable enough to be synchronized across machines (unlike
the config/preferences/data directories).

The returned value depends on the operating system and is either a `Some`, containing
a value from the following table, or a `None`.

|Platform | Value                                     | Example                  |
| ------- | ----------------------------------------- | ------------------------ |
| Linux   | `$XDG_STATE_HOME` or `$HOME`/.local/state | /home/alice/.local/state |
| macOS   | –                                         | –                        |
| Windows | –                                         | –                        |
"""
