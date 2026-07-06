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
# ruff: noqa: RUF002
#
# XXX: only for commiting wip
# ruff: noqa: D102

"""Application class utilities."""

from __future__ import annotations

import sys
from typing import ClassVar, Self

from deluxe.syntax import DNS_SEPARATOR, DNSSyntax


class DomainName(tuple[str]):
    """DNS DomainName.

    A domain name consists of one or more parts, technically called labels,
    that are conventionally concatenated, and delimited by dots, such as `example.com`.

    Occasionally it is assumed that the Domain Name System serves only
    the purpose of mapping Internet host names to data, and mapping
    Internet addresses to host names. This is not correct, the DNS
    is a general (if somewhat limited) hierarchical database, and can
    store almost any kind of data, for almost any purpose.

    The DNS itself places only one restriction on the particular labels
    that can be used to identify resource records. That one restriction
    relates to the length of the label.

    The length of any one label is limited to between 1 and 63 octets.
    A full domain name is limited to 255 octets (including the separators).
    The zero length full name is defined as representing the root of the DNS tree,
    and is typically written and displayed as ".". Those restrictions
    aside, any binary string whatever can be used as the label of any
    resource record.

    - The full domain name may not exceed a total length of 253 ASCII
      characters in its textual representation (or 254 with the trailing dot).
    - The tree of subdivisions may have up to 127 levels.
    - Top-level domain names should not be all-numeric.
    - Domain names are interpreted in a case-independent manner.

    see: https://en.wikipedia.org/wiki/Domain_Name_System
         https://datatracker.ietf.org/doc/html/rfc2181#section-11
    """

    __slots__: ClassVar[tuple[str, ...]] = ()

    def __new__(cls, *args: str, syntax: DNSSyntax = DNSSyntax.Default) -> Self:
        if (
            args[-1].isdigit()
            or (len_ := len(args)) > 127
            or sum(len(bytes(s, sys.getdefaultencoding())) for s in args) + len_ - 1 > 253
            or not all(map(syntax.match, args))
        ):
            raise SyntaxError
        return super().__new__(cls, args)

    @classmethod
    def from_string(cls, name: str, syntax: DNSSyntax = DNSSyntax.Default) -> Self:
        return cls(*name.split(sep=DNS_SEPARATOR), syntax=syntax)

    def __str__(self) -> str:
        return DNS_SEPARATOR.join(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(self)})"

    @property
    def tld(self) -> str:
        return self[-1]

    @property
    def sld(self) -> str:
        return self[-2]


class AppID:
    """Reverse DNS style identifiers for applications.

    Reverse domain name notation (or reverse-DNS) is a naming convention for components,
    packages, types or file names used by a programming language, system or framework.
    Reversed DNS identifier strings are used by Java packages, Apple's Uniform Type
    Identifier, Android operating system, Gnome's application, Flatpak packages,
    freedesktop.org Desktop Entry (and more).

    Note:
        Application identifiers are widely used, changing them later can cause problems.
        For this reason, you should choose identifier carefully, with an eye to the future
        of the application.

    Shape of an AppID
    =================

    +------------+--------------+-------------+-------+---------------------------+
    | DomainName | Organization | Application | Type  |       concatenated        |
    +============+==============+=============+=======+===========================+
    |  io.github |   johndoe    |   cowsay    |   .   |  io.github.johndoe.cowsay |
    +------------+--------------+-------------+-------+---------------------------+


    Requierements:
        - an application ID must be composed of two or more parts
          separated by a period (‘.’) character.
        - each part must contain one or more of the alphanumeric characters
          (A-Z, a-z, 0-9) plus underscore (‘_’) and hyphen (‘-’) and must not
          start with a digit.
        - the empty string is not a valid element (ie: an application ID may
          not start or end with a period and it is not valid to have two periods
          in a row)
        - the entire ID must be less than 255 characters in length.

    see: https://en.wikipedia.org/wiki/Domain_name
    """

    __slots__: ClassVar[tuple[str, ...]] = ("_application", "_domains", "_organization", "_type")

    def __init__(
        self,
        domains: DomainName,
        organization: str,
        application: str,
        type: str | None = None,  # noqa: A002
    ) -> None:
        self._domains: DomainName = domains
        self._organization: str = organization
        self._application: str = application
        self._type: str | None = type

    @staticmethod
    def from_id(_id: str) -> AppID: ...


# URL_PATTERN: re.Pattern[str] = re.compile(
#     r"((?:(?<=[^a-zA-Z0-9]){0,}(?:(?:https?\:\/\/){0,1}(?:[a-zA-Z0-9\%]{1,}\:[a-zA-Z0-9\%]{1,}[@]){,1})(?:(?:\w{1,}\.{1}){1,5}(?:(?:[a-zA-Z]){1,})|(?:[a-zA-Z]{1,}\/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{1,4}){1})){1}(?:(?:(?:\/{0,1}(?:[a-zA-Z0-9\-\_\=\-]){1,})*)(?:[?][a-zA-Z0-9\=\%\&\_\-]{1,}){0,1})(?:\.(?:[a-zA-Z0-9]){0,}){0,1})"  # noqa: E501
# )

# # Checks repository url, assuming it is at GitHub.
# VALID_REPO_URL: re.Pattern[str] = re.compile(
#     r"^https:\/\/github\.com\/[A-Za-z0-9]([A-Za-z0-9_]|-(?!-))*[A-Za-z0-9_]"
#     r"\/[A-Za-z0-9_]([A-Za-z0-9_]|-(?!-))*[A-Za-z0-9_]\/?$"
# )

# # A valid name consists only of ASCII letters
# # and numbers, period, underscore and hyphen.
# # It must start and end with a letter or number.
# # https://packaging.python.org/en/latest/specifications/name-normalization/
# VALID_PROJECT_NAME: re.Pattern[str] = re.compile(
#     r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.IGNORECASE
# )

# # Package names must be lower-case letters,
# # numbers, or dashes, but not start with a dash.
# # The regex is from PEP508: https://peps.python.org/pep-0508/#names
# # And, without allowing periods or underscores,
# # as reflected in packaging name normalization:
# # https://peps.python.org/pep-0503/#normalized-names.
# VALID_PACKAGE_NAME: re.Pattern[str] = re.compile(r"^([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")

# INF = sys.maxsize
# _NEGINF = -sys.maxsize - 1
# _VERSION: re.Pattern[str] = re.compile(
#     r"""(.*[\s=:_-])?
#         (?P<tag>(v)?
#         (?:(?P<epoch>[0-9]+)!)?
#         (?P<release>
#             (?P<major>[0-9]+)(\.(?P<minor>[0-9]+))?(\.(?P<micro>[0-9]+))?
#         )
#         (?P<pre>[-_\.]?(?P<pre_l>(a(lpha)?|b(eta)?|c|rc|pre(view)?))
#             [-_\.]?(?P<pre_n>[0-9]+)?)?
#         (?P<post>(?:-(?P<post_n1>[0-9]+))|
#             (?:[-_\.]?(?P<post_l>post|r(ev)?)[-_\.]?(?P<post_n2>[0-9]+)?))?
#         (?P<dev>[-_\.]?(?P<dev_l>(dev(el)?))[-_\.]?(?P<dev_n>[0-9]+)?)?
#         (?P<local>[-_\.]?(?P<local_n>[a-z0-9]+)*))?""",
#     re.VERBOSE | re.IGNORECASE,
# )
