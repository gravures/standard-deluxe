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
"""Version parsing, normalization, and comparison.

This module provides a comprehensive version handling system that follows
`PEP 440`_ conventions. It includes:

- Regular expressions for parsing version strings.
- Type aliases for version component literals.
- A :class:`Version` class with full ordering semantics.
- An abstract :class:`BaseVersion` base class for version-like objects.
- Constants used in version string formatting.

.. _PEP 440:
    https://peps.python.org/pep-0440/
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Flag, auto
from sys import maxsize
from typing import ClassVar, Literal

from deluxe.types import Frozen, Unset


__all__ = (
    "DEV_PREFIX",
    "DEV_PREFIX_SYNONYMS",
    "EPOCH_SUFFIX",
    "EXT_SEP",
    "LOCAL_PREFIX",
    "LOCAL_RE",
    "LOCAL_SEGMENT_SEP",
    "POST_PREFIX",
    "POST_PREFIX_SYNONYMS",
    "PRE_SYMOBOLS",
    "SEGMENT_SEP",
    "VERSION_RE",
    "BaseVersion",
    "Release",
    "Version",
    "VersionError",
)


_INF = maxsize
_NEGINF = -maxsize - 1


EPOCH_SUFFIX = "!"
"""``"!"`` used to separate epoch from release number."""

POST_PREFIX = "post"
"""``"post"`` prefix used to denote post-release versions."""

POST_PREFIX_SYNONYMS = Literal[POST_PREFIX, "r", "rev"]
"""Type alias for post-release prefixes: ``"post"``, ``"r"``, or ``"rev"``."""

PRE_SYMOBOLS = Literal["a", "alpha", "b", "beta", "pre", "preview", "c", "rc"]
"""Type alias for pre-release symbols.

Recognized symbols: ``"a"`` / ``"alpha"``, ``"b"`` / ``"beta"``,
``"pre"`` / ``"preview"`` / ``"c"`` / ``"rc"``.
"""

DEV_PREFIX = "dev"
"""``"dev"`` prefix used to denote development versions."""

DEV_PREFIX_SYNONYMS = Literal[DEV_PREFIX, "devel"]
"""Type alias for development prefixes: ``"dev"`` or ``"devel"``."""

LOCAL_PREFIX = "+"
"""``"+"`` used to separate public from local version."""

SEGMENT_SEP = "."
"""``"."`` used to separate version segments (major, minor, micro)."""

EXT_SEP = rf"[-_\{SEGMENT_SEP}]"
"""Extended separator pattern matching ``-``, ``_``, or ``."""

LOCAL_SEGMENT_SEP = Literal[SEGMENT_SEP, "-", "_"]
"""Type alias for local segment separators: ``"."``, ``"-"``, or ``"_"``."""

LOCAL_RE = re.compile(
    rf"(?P<local_n>[a-zA-Z0-9]+(?:{EXT_SEP}[a-zA-Z0-9]+)*)",
    re.IGNORECASE,
)
"""Compiled regex for matching local version strings.

Matches one or more alphanumeric segments separated by ``-``, ``_``, or ``.``.
"""


_SEMANTIC_VERSION_RE = re.compile(
    r"""
    ^
        (?P<major>0|[1-9]\d*)
        \.(?P<minor>0|[1-9]\d*)
        \.(?P<micro>0|[1-9]\d*)
        (?:-
            (?P<pre>
                (?:
                    0
                    |
                    [1-9]\d*
                    |
                    \d*[a-zA-Z-][0-9a-zA-Z-]*
                )
                (?:
                    \.
                    (?:
                        0
                        |
                        [1-9]\d*
                        |
                        \d*[a-zA-Z-][0-9a-zA-Z-]*
                    )
                )*
            )
        )?
        (?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?
    $
""",
    re.IGNORECASE | re.VERBOSE,
)

VERSION_RE = re.compile(
    rf"""
    (?P<tag>(v)?
        (?:(?P<epoch>[0-9]+)!)?
        (?P<release>
            (?P<major>[0-9]+)
            (\.(?P<minor>[0-9]+))?
            (\.(?P<micro>[0-9]+))?
        )
        (?P<pre>
            {EXT_SEP}?
            (?P<pre_l>(a(lpha)?|b(eta)?|pre(view)?|c|rc))
            {EXT_SEP}?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>
            (?:
                -
                (?P<post_n1>[0-9]+)
            )
            |
            (?:
                {EXT_SEP}?
                (?P<post_l>post|r(ev)?)
                {EXT_SEP}?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>
            {EXT_SEP}?
            (?P<dev_l>(dev(el)?))
            {EXT_SEP}?
            (?P<dev_n>[0-9]+)?
        )?
        (?P<local>
            [-_\.+]
            {LOCAL_RE.pattern}
        )?
    )
""",
    re.IGNORECASE | re.VERBOSE,
)
"""Compiled regex for parsing version strings.

Supports:

- An optional ``v`` prefix and numeric epoch.
- Major, minor, and micro release segments.
- Pre-release labels (``a``, ``alpha``, ``b``, ``beta``, ``pre``, ``preview``, ``c``, ``rc``).
- Post-release labels (``post``, ``r``, ``rev``).
- Development labels (``dev``, ``devel``).
- Local version segments.

Examples::

    >>> VERSION_RE.fullmatch("1.0.0")
    <re.Match object; ...>
    >>> VERSION_RE.fullmatch("2.1.0a1")
    <re.Match object; ...>
    >>> VERSION_RE.fullmatch("3.0.0.dev12")
    <re.Match object; ...>
"""


_pre_normalized = {
    "a": "a",
    "alpha": "a",
    "b": "b",
    "beta": "b",
    "pre": "rc",
    "preview": "rc",
    "c": "rc",
    "rc": "rc",
}
_pre_order = {"a": 0, "b": 1, "rc": 2}


class VersionError(ValueError):
    """Raised when a version string cannot be parsed or is invalid."""


class Release(Flag):
    """Flags indicating the release type of a version.

    Attributes:
        Final: A stable release with no pre-release or dev markers.
        Pre: A pre-release version (e.g., ``a``, ``b``, ``rc``).
        Post: A post-release version.
        Development: A development version (e.g., ``dev1``).

    Examples::

        >>> Release.Final
        <Release.Final: 1>
        >>> Release.Pre | Release.Development
        <Release.Pre|Development: 5>
    """

    Final = auto()
    Pre = auto()
    Post = auto()
    Development = auto()


class BaseVersion(Frozen, ABC):
    """Abstract base class for version objects.

    Provides common parsing, stringification, and caching infrastructure
    for version-like objects. Subclasses must implement :meth:`_parse`,
    :meth:`_cmpkey`, and :meth:`_stringify`.

    Attributes:
        major (int): The major version number.
        minor (int): The minor version number.
        micro (int): The micro (patch) version number.
        pre (tuple[str, int] | None): Pre-release label and number, or ``None``.

    Examples::

        >>> v = Version.from_string("1.2.3a1")
        >>> v.major
        1
        >>> v.pre
        ('a', 1)
    """

    __frozen__: ClassVar[tuple[str, ...]] = ("major", "minor", "micro", "pre")
    __slots__: ClassVar[tuple[str, ...]] = ("_key_cache", "_tag")  # pyright: ignore[reportUnannotatedClassAttribute, reportIncompatibleUnannotatedOverride]

    @staticmethod
    @abstractmethod
    def _parse(string: str, *, strict: bool = True) -> Version:
        """Parse a version string into a :class:`Version` object.

        Args:
            string: The version string to parse.
            strict: If ``True``, use fullmatch; otherwise use search.

        Returns:
            A :class:`Version` instance.

        Raises:
            :exc:`VersionError`: If the string cannot be parsed.
        """
        raise NotImplementedError

    @abstractmethod
    def _cmpkey(self) -> tuple[tuple[int | tuple[int, int], ...], tuple[str | int, ...]]:
        """Return a comparable key tuple for ordering.

        Returns:
            A tuple of ``(release_key, local_key)`` for ordering comparisons.
        """
        raise NotImplementedError

    @abstractmethod
    def _stringify(self, *, public: bool) -> str:
        """Return a string representation of the version.

        Args:
            public: If ``True``, omit the local version segment.

        Returns:
            The normalized version string.
        """
        raise NotImplementedError

    @classmethod
    def from_string(cls, string: str) -> Version:
        """Parse a version string strictly.

        Args:
            string: A full version string to parse.

        Returns:
            A :class:`Version` instance.

        Raises:
            :exc:`VersionError`: If the string is not a valid version.

        Examples::

            >>> BaseVersion.from_string("1.0.0")
            <Version 1.0.0>
        """
        return cls._parse(string, strict=True)

    @classmethod
    def search(cls, string: str) -> Version:
        """Search for a version within a string.

        Unlike :meth:`from_string`, this allows the version to be
        embedded within a larger string.

        Args:
            string: A string potentially containing a version.

        Returns:
            A :class:`Version` instance.

        Raises:
            :exc:`VersionError`: If no version is found.

        Examples::

            >>> BaseVersion.search("package-2.0.0.tar.gz")
            <Version 2.0.0>
        """
        return cls._parse(string, strict=False)

    def __str__(self) -> str:
        """Return the full version string."""
        return self._stringify(public=False)

    @property
    def tag(self) -> str:
        """The version string, lazily computed and cached.

        Returns:
            The full version string.
        """
        if self._tag is Unset:
            self._tag: str = str(self)
        return self._tag

    @property
    def public(self) -> str:
        """The public version string (without local segment).

        Returns:
            The version string excluding the local component.
        """
        return self._stringify(public=True)


# class SemVersion(BaseVersion):
#     __frozen__: ClassVar[set[str]] = {"build"}
#     __slots__: ClassVar[tuple[str, ...]] = ()

#     def __init__(
#         self,
#         major: int,
#         minor: int,
#         micro: int,
#         *,
#         pre: str | None = None,
#         build: str | None = None,
#     ) -> None:
#         try:
#             assert all(x >= 0 for x in (major, minor, micro))
#         except (AssertionError, TypeError):
#             msg = "all numeric components must be non-negative integers"
#             raise ValueError(msg) from None

#         self.major: int = major
#         self.minor: int = minor
#         self.micro: int = micro
#         self.pre: tuple[str | int, ...] | None = self.split_local(local) if local else None
#         self.build: tuple[str | int, ...] | None = self.split_local(local) if local else None
#         self._tag: str = Unset
#         self._key_cache: tuple[tuple[int | tuple[int, int], ...], tuple[str | int, ...]] = Unset

#     # @staticmethod
#     # def _parse(string: str, *, strict: bool = True) -> Version:
#     #     raise NotImplementedError

#     # def _cmpkey(self) -> tuple[tuple[int | tuple[int, int], ...], tuple[str | int, ...]]:
#     #     raise NotImplementedError

#     # def _stringify(self, *, public: bool) -> str:
#     #     raise NotImplementedError


class Version(BaseVersion):
    """A PEP 440 compliant version object.

    Supports full version semantics including epoch, pre-release, post-release,
    development, and local version identifiers.

    Args:
        major: The major version number (must be non-negative).
        minor: The minor version number (must be non-negative).
        micro: The micro version number (must be non-negative).
        epoch: The epoch number. Default: ``0``.
        pre: A ``(symbol, number)`` tuple for pre-release, or ``None``.
        post: The post-release number, or ``None``.
        dev: The development release number, or ``None``.
        local: A local version string (e.g., ``"build.123"``), or ``None``.

    Raises:
        :exc:`ValueError`: If any numeric component is negative or ``pre``
            has an invalid structure.
        :exc:`VersionError`: If the constructed version is not valid.

    Examples::

        >>> Version(1, 2, 3)
        <Version 1.2.3>
        >>> Version(1, 0, 0, pre=("a", 1))
        <Version 1.0.0a1>
        >>> Version(2, 1, 0, epoch=1)
        <Version 1!2.1.0>

    Comparison
    ----------

    Versions implement rich comparison via :meth:`__eq__`, :meth:`__lt__`,
    :meth:`__gt__`, :meth:`__le__`, and :meth:`__ge__`. Ordering follows
    PEP 440 semantics:

    - Release segments compare lexicographically (epoch, major, minor, micro).
    - Pre-release versions sort before their final counterparts.
    - Post-release versions sort after their final counterparts.
    - Development versions sort before pre-release versions.
    - Local version segments are compared only when public keys are equal.

    Examples::

        >>> Version(1, 0, 0) < Version(1, 0, 1)
        True
        >>> Version(1, 0, 0, pre=("a", 1)) < Version(1, 0, 0)
        True
        >>> Version(1, 0, 0) < Version(1, 0, 0, post=1)
        True
    """

    __frozen__: ClassVar[tuple[str, ...]] = ("epoch", "post", "dev", "local")
    __slots__: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        major: int,
        minor: int,
        micro: int,
        *,
        epoch: int = 0,
        pre: tuple[PRE_SYMOBOLS, int] | None = None,
        post: int | None = None,
        dev: int | None = None,
        local: str | None = None,
    ) -> None:
        try:
            assert all(  # noqa: S101
                x >= 0
                for x in (
                    epoch,
                    major,
                    minor,
                    micro,
                    pre[1] if pre else 0,
                    post or 0,
                    dev or 0,
                )
            )
        except (AssertionError, TypeError):
            msg = "all numeric components must be non-negative integers"
            raise ValueError(msg) from None
        except IndexError:
            msg = "pre tuple should have two components: str and int"
            raise ValueError(msg) from None

        if pre and pre[0] not in PRE_SYMOBOLS.__args__:
            msg = (
                f"invalid symbol '{pre[0]}' for 'pre' argument tuple, "
                f"should be one of {PRE_SYMOBOLS}"
            )
            raise ValueError(msg)

        self.epoch: int = epoch
        self.major: int = major
        self.minor: int = minor
        self.micro: int = micro
        self.pre: tuple[str, int] | None = (pre[0], int(pre[1])) if pre else None
        self.post: int | None = post or None
        self.dev: int | None = dev or None
        self.local: tuple[str | int, ...] | None = self.split_local(local) if local else None
        self._tag: str = Unset
        self._key_cache: tuple[tuple[int | tuple[int, int], ...], tuple[str | int, ...]] = Unset

        if not ((m_ := VERSION_RE.fullmatch(str(self))) and any(m_.groupdict().values())):
            raise VersionError

    @staticmethod
    def _parse(string: str, *, strict: bool = True) -> Version:
        find = VERSION_RE.fullmatch if strict else VERSION_RE.search
        if m_ := find(string):
            m = m_.groupdict()
            if any(m.values()):
                version = Version.__new__(Version)
                version.epoch = int(m["epoch"] or 0)
                version.major = int(m["major"] or 0)
                version.minor = int(m["minor"] or 0)
                version.micro = int(m["micro"] or 0)
                version.pre = (m["pre_l"], int(m["pre_n"] or 0)) if m["pre_l"] else None
                version.post = (
                    int(m["post_n1"])
                    if m["post_n1"]
                    else int(m["post_n2"] or 0)
                    if m["post_l"]
                    else None
                )
                version.dev = (int(m["dev_n"] or 0)) if m["dev_l"] else None
                version.local = Version.split_local(m["local_n"]) if m["local_n"] else None
                version._tag = m["tag"]
                version._key_cache = Unset
                return version
        raise VersionError

    @staticmethod
    def split_local(local: str) -> tuple[str | int, ...]:
        """Split a local version string into its components.

        Local segments separated by ``.``, ``-``, or ``_`` are split.
        Numeric segments are converted to :class:`int`; string segments
        are lowercased.

        Args:
            local: The local version string (without the leading ``+``).

        Returns:
            A tuple of :class:`str` and :class:`int` components.

        Raises:
            ValueError: If the local string does not match :data:`LOCAL_RE`.

        Examples::

            >>> Version.split_local("build.42")
            ('build', 42)
            >>> Version.split_local("abc-def")
            ('abc', 'def')
        """
        if LOCAL_RE.fullmatch(local) is None:
            msg = f"invalid local version labels, '{local}' do not match {LOCAL_RE.pattern}"
            raise ValueError(msg)

        return tuple(
            int(part) if part.isdigit() else part.lower()
            for part in re.split(rf"{EXT_SEP}", local)
        )

    def _stringify(self, *, public: bool) -> str:
        return "".join(
            filter(
                None,
                (
                    f"{self.epoch}{EPOCH_SUFFIX}" if self.epoch else "",
                    f"{self.major}",
                    f"{SEGMENT_SEP}{self.minor}",
                    f"{SEGMENT_SEP}{self.micro}" if self.micro else "",
                    f"{_pre_normalized[self.pre[0].lower()]}{self.pre[1]}" if self.pre else "",
                    f"{SEGMENT_SEP}{POST_PREFIX}{self.post}" if self.post is not None else "",
                    f"{SEGMENT_SEP}{DEV_PREFIX}{self.dev}" if self.dev is not None else "",
                    f"{LOCAL_PREFIX}{SEGMENT_SEP.join(str(s) for s in self.local)}"
                    if (self.local and not public)
                    else "",
                ),
            )
        )

    def _cmpkey(self) -> tuple[tuple[int | tuple[int, int], ...], tuple[str | int, ...]]:
        if not self._key_cache:
            pre = (
                (_NEGINF, _NEGINF)
                if not self.pre and not self.post and self.dev
                else (_pre_order[_pre_normalized[self.pre[0]].lower()], self.pre[1])
                if self.pre
                else (_INF, _INF)
            )
            post = self.post or _NEGINF
            dev = self.dev or _INF
            self._key_cache = (
                (self.epoch, self.major, self.minor, self.micro, pre, post, dev),
                self.local or (),
            )
        return self._key_cache

    @staticmethod
    def _cmp_local(left: tuple[str | int, ...], right: tuple[str | int, ...]) -> int:
        def cmp(a: str | int, b: str | int) -> int:
            if (a_type := type(a)) is type(b):
                return 0 if a == b else 1 if a > b else -1  # pyright: ignore[reportOperatorIssue]
            return 1 if a_type is int else -1

        state = 0
        for a, b in zip(left, right, strict=False):
            if (state := cmp(a, b)) != 0:
                break

        if (i := len(left) - len(right)) != 0 and state == 0:
            return 1 if i > 0 else -1

        return state

    def __hash__(self) -> int:
        return Frozen.__hash__(self)

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        a, a_ = self._cmpkey()
        b, b_ = value._cmpkey()
        return a == b and self._cmp_local(a_, b_) == 0

    def __gt__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        a, a_ = self._cmpkey()
        b, b_ = value._cmpkey()
        return a > b or (a == b and self._cmp_local(a_, b_) == 1)

    def __ge__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        return self > value or self == value

    def __lt__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        a, a_ = self._cmpkey()
        b, b_ = value._cmpkey()
        return a < b or (a == b and self._cmp_local(a_, b_) == -1)

    def __le__(self, value: object, /) -> bool:
        if not isinstance(value, Version):
            return NotImplemented
        return self < value or self == value

    @property
    def type(self) -> Release:
        """The release type of this version.

        Determines the release type based on the presence of pre-release,
        post-release, and development markers. Epoch and local components
        do not affect the release type.

        Returns:
            A :class:`Release` flag combination indicating the release type.
        """
        # epoch and local do not affect version semantic
        state = None
        if self.dev is not None:
            state = Release.Pre | Release.Development
        if self.post is not None:
            if state:
                state |= Release.Post
            else:
                state = Release.Post
        if self.pre is not None:
            if state:
                state |= Release.Pre
            else:
                state = Release.Pre
        return state or Release.Final
