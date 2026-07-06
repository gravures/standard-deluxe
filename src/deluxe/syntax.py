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
# ruff: noqa: B009

# XXX: only for commiting wip
# ruff: noqa: UP035, F401, D101, D102, D103, F841
"""A simple syntax helper module."""

from __future__ import annotations

import re
from enum import unique
from typing import (
    Callable,
    ClassVar,
    Final,
    Generic,
    Literal,
    NamedTuple,
    Never,
    Protocol,
    TypeVar,
)

from deluxe.enums import Enum
from deluxe.functional import Lazy, Maybe
from deluxe.types import Frozen


class Meta(Frozen):
    __frozen__: ClassVar[tuple[str, ...]] = ("value",)

    def __init__(self, value: str) -> None:
        self.value: str = value


class Failure(NamedTuple):
    expected: str
    actual: str


class Result(NamedTuple):
    data: str
    rest: str


class Parser(Protocol):
    def __call__(self, string: str) -> Result | Failure: ...


def integer(string: str):
    pattern = re.compile(r"\d+")
    if m := pattern.match(string):
        return Result(m.group(), string[m.end() :])
    return Failure("integer", string)


def parse(parser: Parser, string: str):
    if isinstance(result := parser(string), Result):
        return result.data
    msg = f"expected {result.expected}, got '{result.actual}'"
    raise SyntaxError(msg)


def text(match: str) -> Parser:
    def text_parser(string: str) -> Result | Failure:
        if string.startswith(match):
            return Result(match, string[len(match) :])
        return Failure(match, string)

    return text_parser


def eof(string: str) -> Result | Failure:
    if string:
        return Failure("end of string", string)
    return Result("", string)


def regex(pattern: re.Pattern[str]) -> Parser:
    def re_parser(string: str) -> Result | Failure:
        if m := pattern.match(string):
            return Result(m.group(), string[m.end() :])
        return Failure(pattern.pattern, string)

    return re_parser


# def apply(func, parsers)


# __all__ = ("Rule", "Grammar", "Syntax", "Os", "DNSSyntax", "DNS_SEPARATOR")


_IDX: Final[str] = "_"


class Rule(NamedTuple):
    """Syntactic Rule type."""

    re: str
    hint: str

    def __call__(self, pos: int) -> str:
        name = getattr(self, "name")
        return f"(?P<{name}{_IDX * pos}>{self.re})"


@unique
class Grammar(Rule, Enum):
    """Syntactic rule enumeration type."""

    def __init_subclass__(cls, **kwds: dict[str, object]):
        for rule in cls.__members__:
            if rule.endswith(_IDX):
                msg = (
                    f"Rule's name in Grammar may not ends with '{_IDX}' -> '{cls.__name__}.{rule}'"
                )
                raise ValueError(msg)

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: object) -> Never:
        msg = "auto() enum's member value assignment unsupported for Grammar."
        raise NotImplementedError(msg)


_G = TypeVar("_G", bound=Grammar)


class Syntax(Generic[_G]):
    """Syntax based on grammar."""

    __slots__: tuple[str, ...] = (
        "_rule_type",
        "ends",
        "flags",
        "inner",
        "length",
        "outer",
        "regex",
        "starts",
    )

    class Violation(NamedTuple):
        word: str
        where: str
        hint: str

    def __init__(
        self,
        starts: _G | None,
        inner: tuple[_G, ...] | None,
        ends: _G | None,
        length: int | None,
        flags: re.RegexFlag,
    ) -> None:
        inner = inner or ()
        if not (len_ := int(bool(starts)) + int(bool(ends)) + (len(inner))):
            msg = "Syntax without any Rules are not permitted."
            raise ValueError(msg)

        idx = iter(range(len_))
        self._rule_type: type[_G] = type(starts or ends or inner[0])  # pyright: ignore[reportGeneralTypeIssues]

        self.flags: re.RegexFlag = flags
        self.length: int | None = length
        self.starts: str | None = f"(?={starts(next(idx))})" if starts else None
        self.inner: str | None = "".join(rule(next(idx)) for rule in inner) if inner else None
        self.inner = f"(?:{self.inner})" if inner else None
        self.ends: str | None = ends(next(idx)) if ends else None
        self.outer: str = f"{{1,{length}}}" if length else "+"
        self.regex: re.Pattern[str] = re.compile(
            f"{self.starts or ''}({self.inner or ''}{self.ends or ''}){self.outer}",
            flags,
        )

    def match(self, string: str) -> bool:
        return bool(self.regex.fullmatch(string))

    def validate(self, string: str) -> Literal[True]:
        if self.match(string):
            return True

        name = getattr(self, "name")
        split = self.regex.split(string)
        groups = {v: k.rstrip(_IDX) for k, v in self.regex.groupindex.items()}
        idxs = sorted(groups.keys())
        rules = [self._rule_type[groups[i]] for i in idxs]
        violations: list[Syntax.Violation] = []

        def check_rule(rule: str, where: str, hint: str) -> None:
            re_ = re.compile(rule, self.flags)
            if not re_.fullmatch(string):
                spl = (s or "" for s in re_.split(string)[::2])
                err = "".join(spl)
                violations.append(Syntax.Violation(err, where, hint))

        if self.starts:
            check_rule(f"^{self.starts}(.*)$", "starts with", rules[0].hint)
        if self.ends:
            check_rule(f"(.*){self.ends}", "ends with", rules[-1].hint)
        if self.inner:
            for rule in rules[1:-2]:
                check_rule(f"({rule.re})+(.*)", "contains", rule.hint)
            check_rule(f"({rules[-2].re})+", "contains", rules[-2].hint)
        if self.length:
            check_rule(
                f".{{1,{self.length}}}", "", f"string may not exceed {self.length} characters"
            )

        msg = "\n".join([
            (
                f" * {self._rule_type.__name__}.{name} rule violation"
                f" in '{string}' string {v.where} '{v.word}' "
                f"where {v.hint}."
            )
            for v in violations
        ])

        raise SyntaxError(msg)


DNS_SEPARATOR: Final = "."


class Ascii(Grammar):
    no_dot = (r"(?a:[^.])", "any ascii char except '.' is required")
    host = (r"(?:a[^\-.])", "any ascii char except '.' and '-' is required")
    alpha = (r"(?a:[a-zA-Z])", "ascii letter is required")
    alnum = (r"(?a:[a-zA-Z0-9])", "ascii letter or digit is required")
    ldh = (r"(?a:[a-zA-Z0-9\-])", "ascii letter, digit or hyphen is required")
    ldu = (r"(?a:[a-zA-Z0-9_])", "ascii letter, digit or underscore is required")
    ldhu = (r"(?a:[a-zA-Z0-9-_])", "ascii letter, digit, hyphen or underscore is required")


class Unicode(Grammar):
    alpha = (r"[a-zA-Z\u0080-\u10FFFF]", "ascii and unicode letter is required")
    alnum = (r"[a-zA-Z0-9\u0080-\u10FFFF]", "ascii and unicode letter or digit is required")
    ldh = (
        r"[a-zA-Z0-9\u0080-\u10ffFF\-]",
        "ascii and unicode letter, digit or hyphen is required",
    )


class Os(Grammar):
    """Set of naming `Rule` related to operating system convention."""

    dbus = (r"(?a:[a-zA-Z_])", "ascii letter, underscore but digits is required")
    free_desktop = (r"(?:a[a-zA-Z-_])", "ascii letter, hyphen, underscore but digits is required")
    win_word = (r"(?!(con|prn|aux|nul|com\d|lpt\d)$)", "windows reserved words are forbidden")
    idna = (r"(?!xn--.*)", "IDNA Ace string is unsupported")


class DNSSyntax(Syntax[Ascii | Unicode | Os], Enum):
    """Syntaxes for DNS labels validation.

    The length of any one label is limited to between 1 and 63 octets.
    The zero length full name is defined as representing the root of the DNS tree,
    and is typically written and displayed as ".". Those restrictions
    aside, any binary string whatever can be used as the label of any
    resource record.

    Note: The limited set of ASCII characters permitted in the DomainName System
          prevents the representation of names and words of many languages.
          User applications could map Unicode strings into the valid DNS character
          set using the python encoding.idna module (see: https://en.wikipedia.org/wiki/Internationalized_domain_name).
    """

    Default = (None, (Ascii.no_dot,), None, 63, re.ASCII | re.IGNORECASE)
    """Default DNS Label Syntax.

    see: https://datatracker.ietf.org/doc/html/rfc2181#section-11
    """

    LDH = (None, (Ascii.ldh,), None, 63, re.ASCII | re.IGNORECASE)
    """The letter, digit, hyphen naming rule.

    This rule defines a subset of the ASCII character set consisting of characters
    a through z, A through Z, digits 0 through 9, and hyphen. It is used notably
    to defined allowed characters in HostName labels."""

    HostName = (Ascii.host, (Ascii.no_dot,), Ascii.host, 63, re.ASCII | re.IGNORECASE)
    """Hostname Labels.

    On the Internet, a hostname is a domain name assigned to a host computer.
    The original specification of hostnames required that labels start with
    an alpha character and not end with a hyphen. However, a subsequent specification
    permitted hostname labels to start with digits:

        - Characters in labels should be part of the ASCII table.
        - Each label may contain from 1 to 63 characters.
        - The null label of length zero is reserved for the root zone.
        - Labels may not start or end with a hyphen.
        - Labels could not contain a dot as it serve as labels separator.

    see: https://en.wikipedia.org/wiki/Hostname
         https://datatracker.ietf.org/doc/html/rfc952
         https://datatracker.ietf.org/doc/html/rfc1123#section-2
         https://datatracker.ietf.org/doc/html/rfc1178
    """

    Safe = (Ascii.alpha, (Ascii.ldh,), Ascii.alnum, 63, re.ASCII | re.IGNORECASE)
    """Safe Labels.

    The following syntax proposed by the RFC_1035 will result in fewer problems
    with many applications that use domain names (e.g., mail, TELNET).

    The labels must follow the rules for ARPANET host names:
        - must start with a letter
        - have as interior characters only letters, digits or hyphen
        - end with a letter or digit
        - Labels must be 63 characters or less.

    Note that while upper and lower case letters are allowed in domain
    names, no significance is attached to the case.

    see: https://datatracker.ietf.org/doc/html/rfc1035#section-2.3.1
    """

    Dbus = (Os.dbus, (Ascii.ldu,), None, 255, re.ASCII)
    """Dbus.

    Rule used in Linux operating system by the dbus Api:
        - must only contain the ASCII characters set '[A-Z][a-z][0-9]_'
        - must not begin with a digit.
        - must contain at least one character.

    see: https://dbus.freedesktop.org/doc/dbus-specification.html#message-protocol-names
    """

    FreeDesktop = (Os.free_desktop, (Unicode.ldh,), None, 255, re.ASCII)
    """FreeDesktop.

    Encompass the rules used in different places of a Linux operating system
    like in .desktop file, appstream metadata or flatpak package among other:
        - must only contain the ASCII characters set '[A-Z][a-z][0-9]-_'
        - must not begin with a digit.
        - must contain at least one character.

    Notes: Dbus have a specific rule where hyphen should be replaced by underscore,
           so the recommandation is to use the more restrictive Dbus Syntax.

    see: https://specifications.freedesktop.org/desktop-entry-spec/latest/file-naming.html
         https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#sect-Metadata-GenericComponent
    """

    WindowsPackage = (
        None,
        (Os.idna, Os.win_word, Ascii.ldh),
        None,
        None,
        re.ASCII | re.IGNORECASE,
    )
    """Windows Package Identity.

    A label in a package string allows the following characters:
        - Uppercase letters (U+0041 thru U+005A)
        - Lowercase letters (U+0061 thru U+007A)
        - Numbers (U+0030 thru U+0039)
        - Dash (U+002D)
        - cannot equal: ".", "..", "con", "prn", "aux", "nul", "com1", "com2", "com3",
          "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3",
          "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
        - cannot begin with "xn--" (IDNA string)

    see: https://learn.microsoft.com/en-us/windows/apps/desktop/modernize/package-identity-overview
    """

    AppleUTI = (
        Unicode.alpha,
        (Unicode.ldh,),
        Unicode.alnum,
        63,
        re.IGNORECASE,
    )  # FIXME: char counting is done with unicode char but should be done in bytes.
    """Apple's Uniform Type Identifier.

       UTI is based on DNS name restrictions, set forth in RFC 1035:
           - UTI may also contain any of the Unicode characters greater than U+007F.
           - Colons and slashes are prohibited
           - UTIs support multiple inheritance, allowing names be identified
             with any number of relevant types
           - UTIs are case-insensitive.

       see: https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_conc/understand_utis_conc.html#//apple_ref/doc/uid/TP40001319-CH202-CHDHIJDE
    """

    UniversalApp = (
        Ascii.alpha,
        (Os.idna, Os.win_word, Ascii.ldh),
        Ascii.alnum,
        63,
        re.IGNORECASE | re.ASCII,
    )
    """Universal Application Identifier.

        - must only contain the ASCII characters set '[A-Z][a-z][0-9]-'
        - must not begin with a digit
        - must not ends with an hyphen
        - must contain at least one character
        - are case insensitive
        - cannot be an IDNA string
        - cannot equal windows reserved word: con", "prn", "aux", "nul", "com1", "com2", "com3",
          "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3",
          "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
        - should not exceed 63 characters
    """
