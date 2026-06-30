#!/usr/bin/env python3
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
# ruff: noqa: D100, D101, D103, T201, PLR0914, PLR0915
from __future__ import annotations

import json
import re
import shutil
import sys
from enum import Enum
from subprocess import run
from typing import Any, TypedDict, cast


class Position(TypedDict):
    line: int
    character: int


class Range(TypedDict):
    start: Position
    end: Position


class Diagnostic(TypedDict):
    file: str
    severity: str
    message: str
    range: Range


class Symbol(TypedDict):
    category: str
    name: str
    referenceCount: int
    isExported: bool
    isTypeKnown: bool
    isTypeAmbiguous: bool
    diagnostics: list[Diagnostic]


class SymbolCounts(TypedDict):
    withKnownType: int
    withAmbiguousType: int
    withUnknownType: int


class TypeCompleteness(TypedDict):
    packageName: str
    packageRootDirectory: str
    moduleName: str
    mooduleRootDirectory: str
    exportedSymbolCounts: SymbolCounts
    otherSymbolCounts: SymbolCounts
    missingFunctionDocStringCount: int
    missingClassDocStringCount: int
    missingDefaultParamCount: int
    completenessScore: float
    modules: list[dict[str, str]]
    symbols: list[Symbol]


class SymbolReport(TypedDict):
    type: str
    name: str
    severity: str
    hint: str
    message: str


class ModuleReport(TypedDict):
    symbols: int
    errors: int
    warnings: int
    score: float
    modules: list[SymbolReport]


class Synth(TypedDict):
    python_version: str
    package_name: str
    exported_symbols: int
    private_symbols: int
    unknown_type: int
    missing_function_docstring: int
    missing_class_docstring: int
    score: float
    modules: dict[str, ModuleReport]


class TypingError(Enum):
    Unkwown = "UnkwownType"
    Ambiguous = "AmbiguousType"


def parse_report(report: dict[str, object]) -> Synth:
    type_completness = cast("TypeCompleteness", report.get("typeCompleteness", {}))
    modules = type_completness.get("modules", {})
    modules = {name for m in modules if (name := m.get("name", ""))}
    symbols = type_completness.get("symbols", [])

    synth: Synth = {
        "python_version": "",
        "package_name": type_completness["packageName"],
        "exported_symbols": type_completness["exportedSymbolCounts"]["withKnownType"]
        + type_completness["exportedSymbolCounts"]["withUnknownType"],
        "private_symbols": type_completness["otherSymbolCounts"]["withKnownType"]
        + type_completness["otherSymbolCounts"]["withUnknownType"],
        "unknown_type": type_completness["exportedSymbolCounts"]["withUnknownType"]
        + type_completness["otherSymbolCounts"]["withUnknownType"],
        "missing_class_docstring": type_completness["missingClassDocStringCount"],
        "missing_function_docstring": type_completness["missingFunctionDocStringCount"],
        "score": type_completness["completenessScore"],
        "modules": {},
    }

    for symbol in symbols:
        module, name = split_name(symbol["name"], modules)
        mod_report = synth["modules"].setdefault(
            module, {"symbols": 0, "errors": 0, "score": 1.0, "warnings": 0, "modules": []}
        )
        mod_report["symbols"] += 1
        # diagnostics = filter_diagnostics(symbol["diagnostics"])
        diagnostics = symbol["diagnostics"]
        typing = (
            TypingError.Ambiguous
            if symbol["isTypeAmbiguous"]
            else TypingError.Unkwown
            if not symbol["isTypeKnown"]
            else None
        )

        if typing or diagnostics:
            hint = typing.value if typing else "-"
            severity = diagnostics[0]["severity"] if diagnostics else "-"
            message = diagnostics[0]["message"] if diagnostics else "-"

            if severity == "warning":
                mod_report["warnings"] += 1
            else:
                mod_report["errors"] += 1

            mod_report["modules"].append({
                "type": abbr_type(symbol["category"]),
                "name": name,
                "hint": hint,
                "severity": severity,
                "message": message,
            })

        mod_report["score"] = 1.0 - (mod_report["errors"] / mod_report["symbols"])

    return synth


def main() -> int:
    # try:
    #     with Path("./.pyright_report").open("r") as file:
    #         str_report = file.read()
    # except OSError:

    if not (argv := sys.argv[1:]):
        argv = ["deluxe"]

    cp = run(  # noqa: S603
        (  # noqa: S607
            "basedpyright",
            "--verifytypes",
            *argv,
            "--ignoreexternal",
            "--outputjson",
        ),
        text=True,
        shell=False,
        capture_output=True,
        check=False,
    )

    if cp.stderr:
        sys.stderr.write(cp.stderr)
        return cp.returncode

    str_report = cp.stdout

    # with Path("./.pyright_report").open("w") as file:
    #     file.write(str_report)

    report: dict[str, object] = json.loads(str_report)
    synth = parse_report(report)
    print_table(synth)

    return 0


def print_table(diagnostic: Synth) -> None:
    width = shutil.get_terminal_size().columns - 2
    corners = ("┌", "┐", "└", "┘")
    verts = ("├", "┤", "┼", "│")
    horiz = "─"
    tab = " " * 3
    split = f"{verts[0]}{horiz * (width - 2)}{verts[1]}"
    blank = f"{verts[3]}{' ' * (width - 2)}{verts[3]}"
    open_ = f"{corners[0]}{horiz * (width - 2)}{corners[1]}"
    close = f"{corners[2]}{horiz * (width - 2)}{corners[3]}"
    global_score = modules_count = symbols_count = 0

    def color(color: int) -> str:
        return f"\x1b[{color}m"

    def reset() -> str:
        return "\x1b[0m"

    def score_color(score: float):
        if score >= 1.0:
            return 32  # Green
        if score > 0.8:  # noqa: PLR2004
            return 33  # Yellow
        return 31  # Red

    def inline(line: str) -> str:
        pad = width - len(strip_esc(line)) - 1
        if pad < 0:
            line = line[: pad - 1]
            pad = 0
        return f"{verts[3]}{line}{verts[3]:>{pad}}"

    print(open_)
    print(inline(" Type completeness:"))
    print(inline(f"{tab}python target: {diagnostic['python_version']}"))
    print(inline(f"{tab}package: {diagnostic['package_name']}"))
    print(inline(f"{tab}exported symbols: {diagnostic['exported_symbols']}"))
    print(inline(f"{tab}private symbols: {diagnostic['private_symbols']}"))
    score = diagnostic["score"]
    print(inline(f"{tab}completeness score: {color(score_color(score))}{score:.1%}{reset()}"))
    print(inline(f"{tab}missing class docstring: {diagnostic['missing_class_docstring']}"))
    print(inline(f"{tab}missing function docstring: {diagnostic['missing_function_docstring']}"))
    print(blank)

    for module, report in diagnostic["modules"].items():
        modules_count += 1
        score = report["score"]
        global_score += score
        errors = report["errors"]
        warnings = report["warnings"]
        symbols = report["symbols"]
        symbols_count += symbols

        abstract = f" {module} ({symbols} symbols) "
        score_str = f" Score: {color(score_color(score))}{score:.1%}{reset()} "
        err_warn_str = f" Errors: {errors} / Warnings: {warnings} "
        padding = width - len(abstract) - len(score_str) - len(err_warn_str)

        header = (
            f"\x1b[1m{abstract}{reset()}{' ' * padding}\x1b[1m{score_str}{reset()} {err_warn_str}"
        )

        print(split)
        print(inline(header))

        if report["modules"]:
            # Determine column widths
            type_w = max(len(m["type"]) for m in report["modules"]) + 2
            name_w = max(len(m["name"]) for m in report["modules"]) + 2
            hint_w = max(len(m["hint"]) for m in report["modules"]) + 2
            sevr_w = max(len(m["severity"]) for m in report["modules"]) + 2

            # Print table header
            line = (
                f"{tab}\x1b[4m{'Type':<{type_w}}{'Symbol':<{name_w}}"
                f"{'Hint':<{hint_w}}{'Severity':<{sevr_w}}{reset()}"
            )
            print(blank)
            print(inline(line))

            # Print table rows
            for m in report["modules"]:
                line = (
                    f"{tab}{m['type']:<{type_w}}{m['name']:<{name_w}}"
                    f"{m['hint']:<{hint_w}}{m['severity']:<{sevr_w}}"
                )
                print(inline(line))
            print(blank)
    print(close)
    print(f"completeness: {global_score / modules_count:.1%} for {symbols_count} symbols")


def filter_diagnostics(diag: list[Diagnostic]) -> tuple[Diagnostic, ...]:
    return tuple(filter(lambda d: "docstring" not in d["message"], diag))


def split_name(name: str, modules: set[str]) -> tuple[str, str]:
    _s = name
    symbol = name
    left = module = ""

    while name:
        module, _, symbol = name.rpartition(".")
        if module in modules:
            break
        name = module
        left = symbol

    return module, f"{symbol}.{left}".rstrip(".")


def abbr_type(symbol: str) -> str:
    return {"class": "class", "method": "meth", "function": "func", "variable": "var"}.get(
        symbol, symbol
    )


_STRIP_ESC = re.compile(
    r"""
    (?:\x1b[\[\]])      # escape code
    (?:\d+;)*           # |
    (\.*)               # params
    (?:;)?              # |
    (?:(\d+[JKm])|(\a)) # command
    """,
    flags=re.VERBOSE,
)


def strip_esc(string: str) -> str:
    """Strips ANSI escape sequences.

    Returns:
        str: the given string with OSC/CSI escape sequences removed.
    """

    def text(match: Any) -> str:
        return match.groups()[0] if match else string

    return re.sub(_STRIP_ESC, text, string)


if __name__ == "__main__":
    sys.exit(main())
