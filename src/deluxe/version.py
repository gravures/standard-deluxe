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
from __future__ import annotations

import re
from functools import total_ordering
from sys import maxsize
from typing import NamedTuple


_INF = maxsize
_NEGINF = -maxsize - 1
_VERSION: re.Pattern[str] = re.compile(
    r"""(.*[\s=:_-])?
        (?P<tag>(v)?
        (?:(?P<epoch>[0-9]+)!)?
        (?P<release>
            (?P<major>[0-9]+)(\.(?P<minor>[0-9]+))?(\.(?P<micro>[0-9]+))?
        )
        (?P<pre>[-_\.]?(?P<pre_l>(a(lpha)?|b(eta)?|c|rc|pre(view)?))
            [-_\.]?(?P<pre_n>[0-9]+)?)?
        (?P<post>(?:-(?P<post_n1>[0-9]+))|
            (?:[-_\.]?(?P<post_l>post|r(ev)?)[-_\.]?(?P<post_n2>[0-9]+)?))?
        (?P<dev>[-_\.]?(?P<dev_l>(dev(el)?))[-_\.]?(?P<dev_n>[0-9]+)?)?
        (?P<local>[-_\.]?(?P<local_n>[a-z0-9]+)*))?""",
    re.VERBOSE | re.IGNORECASE,
)


class VersionError(ValueError): ...


@total_ordering
class Version(NamedTuple):
    major: int
    minor: int
    micro: int
    epoch: int = 0
    pre: tuple[str, int] | None = None
    post: tuple[str, int] | None = None
    dev: tuple[str, int] | None = None
    local: str | None = None
    tag: str = ""

    @staticmethod
    def from_string(string: str) -> Version:
        if m_ := _VERSION.fullmatch(string):
            m = m_.groupdict()
            return Version(
                tag=m["tag"],
                epoch=int(m["epoch"] or 0),
                major=int(m["major"] or 0),
                minor=int(m["minor"] or 0),
                micro=int(m["micro"] or 0),
                pre=(m["pre_l"], int(m["pre_n"] or 0)) if m["pre_l"] else None,
                post=(m["post_l"], int(m["post_n1"] or m["post_n2"] or 0))
                if m["post_l"]
                else None,
                dev=(m["dev_l"], int(m["dev_n"] or 0)) if m["dev_l"] else None,
                local=m["local"] or None,
            )
        raise VersionError

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        return self._cmpkey() == value._cmpkey()

    def __gt__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        return self._cmpkey() > value._cmpkey()

    def _cmpkey(self):
        if self.pre is None and self.post is None and self.dev is not None:
            pre = _NEGINF
        else:
            pre = _INF if self.pre is None else self.pre[1]
        post = _NEGINF if self.post is None else self.post[1]
        dev = maxsize if self.dev is None else self.dev[1]

        if self.local is None:
            local = _NEGINF
        else:
            local: tuple[tuple[str | int] | tuple[int, str], ...] | int = tuple(
                (i, "") if isinstance(i, int) else (_NEGINF, i) for i in self.local
            )
        return self.epoch, self.major, self.minor, self.micro, pre, post, dev, local

    def __hash__(self) -> int:
        return hash((
            self.epoch,
            self.major,
            self.minor,
            self.micro,
            self.pre,
            self.post,
            self.dev,
            self.local,
        ))

    def __str__(self) -> str:
        return self.tag.strip("v")
