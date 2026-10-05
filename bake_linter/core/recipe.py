# -*- coding: utf-8 -*-
"""
Structure of a BitBake file beyond single lines.

Rules mostly read a file line by line, which cannot tell which variable a
continuation line belongs to, whether a line sits in a function body, which
classes are inherited, or what a required .inc file sets. This module works
that out once per file:

- each line's owner: the variable it assigns (including continuation lines),
  the function it is part of, or a comment;
- logical assignments, with continuation lines joined;
- inherited classes and require/include directives;
- the files a recipe includes, resolved the way BitBake searches for them
  (next to the recipe, then from the root of the layer).

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

# VAR, VAR:override:append, VAR[flag], export VAR, followed by an operator
ASSIGNMENT_PATTERN = re.compile(
    r'^\s*(?:export\s+)?'
    r'(?P<name>[A-Za-z_${}][\w${}/+.-]*(?::[\w${}+.-]+)*)'
    r'(?P<flag>\[[^\]]*\])?'
    r'\s*(?P<op>\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)'
    r'\s*(?P<value>.*)$'
)

# do_install() {, python do_foo() {, fakeroot do_x:append() {, pkg_postinst:${PN}() {
FUNCTION_PATTERN = re.compile(
    r'^\s*(?:(?:python|fakeroot)\s+)*(?P<name>[\w${}.+-]+(?::[\w${}.+-]+)*)?\s*\(\s*\)\s*\{'
)
PYTHON_DEF_PATTERN = re.compile(r'^def\s+(?P<name>\w+)\s*\(')

INHERIT_PATTERN = re.compile(r'^\s*inherit(?:_defer)?\s+(?P<classes>.+)$')
INCLUDE_PATTERN = re.compile(r'^\s*(?P<kind>require|include|include_all)\s+(?P<path>\S+)')

COMMENT = "#"
FUNCTION_PREFIX = "FUNC:"


@dataclass
class Assignment:
    """One logical assignment, continuation lines joined."""
    name: str            # full name, e.g. "RDEPENDS:${PN}-dev"
    flag: Optional[str]  # "sha256sum" for SRC_URI[sha256sum]
    op: str
    value: str           # unquoted value, continuation lines joined
    line: int            # first line (1-indexed)
    end_line: int        # last line

    @property
    def base(self) -> str:
        """Variable name without overrides: RDEPENDS for RDEPENDS:${PN}-dev."""
        return self.name.split(":", 1)[0]

    @property
    def overrides(self) -> List[str]:
        """Overrides after the base name, e.g. ["${PN}-dev", "append"]."""
        return self.name.split(":")[1:]


@dataclass
class RecipeStructure:
    owners: List[str] = field(default_factory=list)
    assignments: List[Assignment] = field(default_factory=list)
    inherits: Set[str] = field(default_factory=set)
    includes: List[str] = field(default_factory=list)

    def owner(self, line: int) -> str:
        """Owner of a 1-indexed line: a variable name, "FUNC:<name>", "#" or ""."""
        if 1 <= line <= len(self.owners):
            return self.owners[line - 1]
        return ""


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _inherited_classes(text: str) -> Set[str]:
    """Class names in an inherit statement, including those named inside an
    inline expression such as ${@bb.utils.contains(..., 'systemd', '', d)}."""
    classes = set()
    for token in re.findall(r"[\w.+-]+", text.replace("${@", " ")):
        if not token.startswith("$"):
            classes.add(token)
    return classes


def parse_structure(lines: List[str]) -> RecipeStructure:
    """Work out owners, logical assignments, inherits and includes."""
    structure = RecipeStructure()
    owners = structure.owners
    current: Optional[Assignment] = None
    parts: List[str] = []
    function: Optional[str] = None
    python_def = False

    for line_num, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()

        if function is not None:
            owners.append(FUNCTION_PREFIX + function)
            if line.startswith("}"):
                function = None
            continue

        if python_def:
            if stripped and not line[:1].isspace():
                python_def = False
            else:
                owners.append(FUNCTION_PREFIX + "def")
                continue

        if current is not None:
            owners.append(current.name)
            parts.append(stripped[:-1] if stripped.endswith("\\") else stripped)
            if not stripped.endswith("\\"):
                current.value = _unquote(" ".join(p for p in parts if p))
                current.end_line = line_num
                current = None
            continue

        if stripped.startswith("#"):
            owners.append(COMMENT)
            continue

        function_match = FUNCTION_PATTERN.match(line)
        if function_match:
            function = function_match.group("name") or "anonymous"
            owners.append(FUNCTION_PREFIX + function)
            if stripped.endswith("}") and stripped.count("{") == stripped.count("}"):
                function = None
            continue

        if PYTHON_DEF_PATTERN.match(line):
            python_def = True
            owners.append(FUNCTION_PREFIX + "def")
            continue

        inherit_match = INHERIT_PATTERN.match(line)
        if inherit_match:
            structure.inherits |= _inherited_classes(inherit_match.group("classes"))
            owners.append("")
            continue

        include_match = INCLUDE_PATTERN.match(line)
        if include_match:
            structure.includes.append(include_match.group("path"))
            owners.append("")
            continue

        match = ASSIGNMENT_PATTERN.match(line)
        if match:
            flag = match.group("flag")
            assignment = Assignment(
                name=match.group("name"),
                flag=flag[1:-1] if flag else None,
                op=match.group("op"),
                value="",
                line=line_num,
                end_line=line_num,
            )
            structure.assignments.append(assignment)
            owners.append(assignment.name)
            value = match.group("value").strip()
            if value.endswith("\\"):
                current = assignment
                parts = [value[:-1].strip()]
            else:
                assignment.value = _unquote(value)
            continue

        owners.append("")

    if current is not None:
        current.value = _unquote(" ".join(p for p in parts if p))
        current.end_line = len(lines)

    return structure


@dataclass
class FunctionLine:
    """One logical line of a function body, continuation lines joined."""
    function: str  # function name, e.g. "do_install:append"
    text: str      # stripped, continuation lines joined
    line: int      # first line (1-indexed)
    end_line: int  # last line


def function_lines(lines: List[str], structure: RecipeStructure) -> List[FunctionLine]:
    """The body lines of every function, with lines ending in a backslash
    joined to the next one. The header line (do_install() {) is left out."""
    found: List[FunctionLine] = []
    current: Optional[FunctionLine] = None
    previous_owner = ""
    closed = False
    for line_num, raw in enumerate(lines, start=1):
        owner = structure.owner(line_num)
        if not owner.startswith(FUNCTION_PREFIX):
            current, previous_owner = None, owner
            continue
        name = owner[len(FUNCTION_PREFIX):]
        stripped = raw.rstrip("\n").strip()
        # A new function starts where the owner changes or right after the
        # closing brace of one with the same name
        header = (owner != previous_owner or closed) and FUNCTION_PATTERN.match(raw)
        previous_owner = owner
        closed = raw.startswith("}")
        if header:
            current = None
            continue
        continued = stripped.endswith("\\")
        part = stripped[:-1].rstrip() if continued else stripped
        if current is not None:
            current.text = (current.text + " " + part).strip()
            current.end_line = line_num
        else:
            current = FunctionLine(name, part, line_num, line_num)
            found.append(current)
        if not continued:
            current = None
    return found


def recipe_name(path: Path) -> str:
    """PN as BitBake derives it from the file name: foo_1.0.bb -> foo."""
    name = path.name
    for suffix in (".bbappend", ".bb", ".inc"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name.split("_", 1)[0]


def _layer_roots(path: Path) -> List[Path]:
    """Directories above *path* that hold a conf/layer.conf."""
    return [p for p in path.parents if (p / "conf" / "layer.conf").is_file()]


def resolve_include(including: Path, target: str) -> Optional[Path]:
    """Find the file a require/include names, as BitBake would: relative to
    the including file, then relative to the layer root. Returns None when it
    is not found here (it may live in another layer) or the path contains a
    variable."""
    if "${" in target:
        return None
    candidate = Path(target)
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    for base in [including.parent] + _layer_roots(including):
        if (base / candidate).is_file():
            return base / candidate
    return None


@dataclass
class IncludedFile:
    path: Path
    structure: RecipeStructure


def resolve_includes(path: Path, structure: RecipeStructure,
                     _seen: Optional[Set[Path]] = None) -> Optional[List[IncludedFile]]:
    """All files *structure* includes, recursively. Returns None when any of
    them cannot be found, because then what they set is unknown."""
    seen = _seen if _seen is not None else {path.resolve()}
    found: List[IncludedFile] = []
    for target in structure.includes:
        resolved = resolve_include(path, target)
        if resolved is None:
            return None
        key = resolved.resolve()
        if key in seen:
            continue
        seen.add(key)
        try:
            lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None
        child = parse_structure(lines)
        found.append(IncludedFile(resolved, child))
        nested = resolve_includes(resolved, child, seen)
        if nested is None:
            return None
        found.extend(nested)
    return found
