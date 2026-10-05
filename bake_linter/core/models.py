# -*- coding: utf-8 -*-
"""
Core data models for the Bake Linter.

This module defines the fundamental data structures used throughout the linter,
including severity levels, lint results, and rule configuration.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import json
import re
from functools import cached_property
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Optional, List, Dict, Set, Tuple


class Severity(IntEnum):
    """
    Severity levels for lint issues.
    
    Ordered by importance (higher value = more severe).
    Used for filtering, sorting, and exit code determination.
    """
    INFO = 1
    WARNING = 2
    ERROR = 3

    def __str__(self) -> str:
        return self.name.lower()

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Parse severity from string (case-insensitive)."""
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Unknown severity: {value}. Valid values: {[s.name for s in cls]}")


class ExitCode(IntEnum):
    """
    Exit codes for the linter CLI.
    
    These codes are designed for CI integration:
    - 0: Success (no issues or only info-level)
    - 1: Warnings found (may or may not fail depending on CI config)
    - 2: Errors found (fail the build)
    - 3: Configuration or runtime error
    """
    SUCCESS = 0
    WARNINGS_FOUND = 1
    ERRORS_FOUND = 2
    RUNTIME_ERROR = 3


def get_rule_docs_path(rule_id: str) -> Optional[Path]:
    """
    Get the local path to the documentation file for a rule.
    
    Args:
        rule_id: The rule identifier (e.g., "DEPRECATED001")
        
    Returns:
        Path to the docs/rules/<rule_id>.md file, or None if not found
    """
    # Get the docs/rules directory relative to this module
    import importlib.resources
    try:
        # Try to find the docs directory in the package
        docs_dir = Path(__file__).parent.parent.parent / "docs" / "rules"
        doc_file = docs_dir / f"{rule_id}.md"
        if doc_file.exists():
            return doc_file
    except Exception:
        pass
    return None


def get_rule_docs_url(rule_id: str) -> str:
    """
    Get the documentation URL for a rule.
    
    This returns a relative path to the documentation file that can be
    used in HTML reports or as a reference in text output.
    
    Args:
        rule_id: The rule identifier (e.g., "DEPRECATED001")
        
    Returns:
        Documentation reference string (relative path to md file)
    """
    return f"docs/rules/{rule_id}.md"


def get_rule_docs_content(rule_id: str) -> Optional[str]:
    """
    Get the documentation content for a rule.
    
    Args:
        rule_id: The rule identifier (e.g., "DEPRECATED001")
        
    Returns:
        The markdown content of the documentation file, or None if not found
    """
    doc_path = get_rule_docs_path(rule_id)
    if doc_path and doc_path.exists():
        try:
            return doc_path.read_text(encoding='utf-8')
        except Exception:
            pass
    return None


@dataclass
class LintResult:
    """
    Represents a single lint issue found in a file.
    
    This is the primary output unit of a lint rule. All lint issues
    are represented as LintResult objects with consistent structure
    for machine-parseable output.
    
    Attributes:
        rule_id: Unique identifier for the rule that generated this result
        file: Path to the file where the issue was found
        line: Line number (1-indexed), or None if file-level issue
        column: Column number (1-indexed), or None if not applicable
        severity: Severity level of the issue
        message: Human-readable description of the issue
        hint: Optional suggestion on how to fix the issue
        context: Optional code snippet or additional context
        rule_name: Human-readable name of the rule
        docs_url: Optional URL to rule documentation (auto-generated if not provided)
    """
    rule_id: str
    file: Path
    severity: Severity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    hint: Optional[str] = None
    context: Optional[str] = None
    rule_name: Optional[str] = None
    docs_url: Optional[str] = None
    
    def __post_init__(self):
        """Auto-generate docs_url if not provided."""
        if self.docs_url is None:
            self.docs_url = get_rule_docs_url(self.rule_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "file": str(self.file),
            "line": self.line,
            "column": self.column,
            "severity": str(self.severity),
            "message": self.message,
            "hint": self.hint,
            "context": self.context,
            "docs_url": self.docs_url,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    def format_location(self) -> str:
        """Format file:line:column location string."""
        loc = str(self.file)
        if self.line:
            loc += f":{self.line}"
            if self.column:
                loc += f":{self.column}"
        return loc

    def __lt__(self, other: "LintResult") -> bool:
        """Enable sorting by file, then line, then severity."""
        if not isinstance(other, LintResult):
            return NotImplemented
        return (str(self.file), self.line or 0, -self.severity) < \
               (str(other.file), other.line or 0, -other.severity)


@dataclass
class RuleConfig:
    """
    Configuration for a single lint rule.
    
    Attributes:
        rule_id: Unique identifier for the rule
        enabled: Whether the rule is active
        severity: Override severity level (None = use rule default)
        options: Rule-specific configuration options
    """
    rule_id: str
    enabled: bool = True
    severity: Optional[Severity] = None
    options: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, rule_id: str, data: Dict[str, Any]) -> "RuleConfig":
        """Create RuleConfig from dictionary (e.g., from YAML config)."""
        severity = None
        if "severity" in data:
            severity = Severity.from_string(data["severity"])
        
        return cls(
            rule_id=rule_id,
            enabled=data.get("enabled", True),
            severity=severity,
            options=data.get("options", {}),
        )


# Inline suppression comment: "# nolint: RULE_ID", "# nolint: RULE1, RULE2"
# or "# nolint: *". The keyword and rule IDs are case-insensitive.
INLINE_SUPPRESSION_PATTERN = re.compile(
    r'#\s*nolint:\s*(?P<rules>(?:\*|[A-Z][A-Z0-9_]*)(?:\s*,\s*(?:\*|[A-Z][A-Z0-9_]*))*)',
    re.IGNORECASE,
)


def parse_inline_suppressions(lines: List[str]) -> Tuple[Dict[int, Set[str]], Set[str]]:
    """
    Find the "# nolint:" comments in *lines*.

    A comment on a line of code applies to that line. A standalone comment
    applies to the next line that is not a comment, so several standalone
    comments can stack above one line. A standalone comment also covers the
    file-level findings of the rules it names: a finding such as a missing
    LICENSE has no line of its own to attach a comment to.

    Returns:
        (per_line, file_level): rule IDs suppressed for each 1-indexed line,
        and rule IDs suppressed for findings that have no line.
    """
    per_line: Dict[int, Set[str]] = {}
    file_level: Set[str] = set()
    pending: Set[str] = set()

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        match = INLINE_SUPPRESSION_PATTERN.search(line)
        rule_ids = set()
        if match:
            rule_ids = {
                r.strip().upper() for r in match.group("rules").split(",") if r.strip()
            }

        if stripped.startswith("#"):
            pending |= rule_ids
            file_level |= rule_ids
            continue

        suppressed = pending | rule_ids
        if suppressed:
            per_line[line_num] = suppressed
        pending = set()

    return per_line, file_level


@dataclass
class FileContext:
    """
    Parsed context for a BitBake recipe file.
    
    Provides parsed information about a recipe file for rules to analyze.
    This avoids re-parsing the file for each rule.
    
    Attributes:
        path: Path to the file
        content: Raw file content
        lines: List of lines (for line-based analysis)
        variables: Extracted variable assignments
        file_type: Type of file (.bb, .bbappend, .inc)
        is_autogenerated: Whether the file appears to be autogenerated
        parse_errors: Any errors encountered during parsing
        inline_suppressions: Map of line number to set of suppressed rule IDs
        file_suppressions: Rule IDs suppressed for findings with no line

    Suppressions are parsed from ``lines`` unless they are passed in.
    """
    path: Path
    content: str
    lines: List[str]
    variables: Dict[str, List["VariableAssignment"]] = field(default_factory=dict)
    file_type: str = ""
    is_autogenerated: bool = False
    parse_errors: List[str] = field(default_factory=list)
    inline_suppressions: Dict[int, Set[str]] = field(default_factory=dict)
    file_suppressions: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Determine file type from extension and parse suppressions."""
        if not self.inline_suppressions and not self.file_suppressions:
            self.inline_suppressions, self.file_suppressions = (
                parse_inline_suppressions(self.lines)
            )

        if self.path.suffix == ".bb":
            self.file_type = "recipe"
        elif self.path.name.endswith(".bbappend"):
            self.file_type = "bbappend"
        elif self.path.suffix == ".inc":
            self.file_type = "include"
        else:
            self.file_type = "unknown"

    # Structure beyond single lines (see bake_linter.core.recipe), computed
    # on first use.

    @cached_property
    def structure(self) -> "RecipeStructure":
        """Line owners, logical assignments, inherits and includes."""
        from bake_linter.core.recipe import parse_structure
        return parse_structure(self.lines)

    def owner(self, line: int) -> str:
        """What a 1-indexed line belongs to: the variable it assigns (also on
        continuation lines), "FUNC:<name>" in a function body, "#" for a
        comment, or ""."""
        return self.structure.owner(line)

    def owner_base(self, line: int) -> str:
        """The owning variable without overrides (RDEPENDS for
        RDEPENDS:${PN}-dev), or the owner as is for functions and comments."""
        owner = self.owner(line)
        if owner.startswith("FUNC:") or owner == "#":
            return owner
        return owner.split(":", 1)[0]

    def assignment_at(self, line: int) -> Optional["Assignment"]:
        """The logical assignment a 1-indexed line is part of (its first line
        or a continuation line), or None."""
        return self.structure.assignment_at(line)

    def function_at(self, line: int) -> Optional["Function"]:
        """The shell or python function a 1-indexed line is part of, header
        and closing brace included, or None."""
        return self.structure.function_at(line)

    def is_top_level_assignment(self, line: int) -> bool:
        """Whether a 1-indexed line starts a BitBake assignment: not a
        continuation line, not a function body, not a comment."""
        assignment = self.assignment_at(line)
        return assignment is not None and assignment.line == line

    @cached_property
    def function_lines(self) -> List["FunctionLine"]:
        """Logical lines of every function body, continuation lines joined,
        each with the name of its function (e.g. "do_install:append")."""
        from bake_linter.core.recipe import function_lines
        return function_lines(self.lines, self.structure)

    @cached_property
    def pn(self) -> str:
        """PN as BitBake derives it from the file name."""
        from bake_linter.core.recipe import recipe_name
        return recipe_name(self.path)

    @cached_property
    def included_files(self) -> Optional[List["IncludedFile"]]:
        """Files this one requires or includes, recursively, or None when any
        of them cannot be found (what they set is then unknown)."""
        from bake_linter.core.recipe import resolve_includes
        if not self.structure.includes:
            return []
        if not self.path.is_file():
            return None
        return resolve_includes(self.path, self.structure)

    @cached_property
    def inherits(self) -> Set[str]:
        """Classes inherited here or in a resolved include."""
        classes = set(self.structure.inherits)
        for included in self.included_files or []:
            classes |= included.structure.inherits
        return classes

    def sets_variable(self, name: str) -> Optional[bool]:
        """Whether this file or one it includes assigns *name* (any override
        or flag). None when an include could not be resolved and the file
        itself does not set it: the answer is then unknown."""
        def assigns(structure) -> bool:
            return any(a.base == name for a in structure.assignments)
        if assigns(self.structure):
            return True
        included = self.included_files
        if included is None:
            return None
        return any(assigns(i.structure) for i in included)

    def is_suppressed(self, rule_id: str, line: Optional[int]) -> bool:
        """Whether a "# nolint:" comment suppresses *rule_id* at *line*.

        A finding with no line is checked against the file-level suppressions.
        """
        suppressed = (
            self.file_suppressions if line is None
            else self.inline_suppressions.get(line, set())
        )
        return rule_id in suppressed or "*" in suppressed


@dataclass
class VariableAssignment:
    """
    Represents a variable assignment in a BitBake recipe.
    
    Attributes:
        name: Variable name (e.g., "LICENSE", "SRC_URI")
        value: Assigned value (may contain variable references)
        line: Line number of the assignment
        operator: Assignment operator (=, ?=, ??=, +=, =+, :=, .=, =.)
        is_override: Whether this uses override syntax (VAR:override)
        override: The override suffix if applicable
    """
    name: str
    value: str
    line: int
    operator: str = "="
    is_override: bool = False
    override: Optional[str] = None


@dataclass
class LintSummary:
    """
    Summary statistics for a lint run.
    
    Attributes:
        files_scanned: Number of files processed
        files_with_issues: Number of files that had at least one issue
        total_issues: Total number of issues found
        errors: Number of error-level issues
        warnings: Number of warning-level issues
        infos: Number of info-level issues
        rules_executed: Number of rules that were run
        skipped_files: Files that were skipped (unreadable, etc.)
    """
    files_scanned: int = 0
    files_with_issues: int = 0
    total_issues: int = 0
    errors: int = 0
    warnings: int = 0
    infos: int = 0
    rules_executed: int = 0
    skipped_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_results(cls, results: List[LintResult], 
                     files_scanned: int,
                     rules_executed: int,
                     skipped_files: Optional[List[str]] = None) -> "LintSummary":
        """Create summary from a list of lint results."""
        files_with_issues = len(set(r.file for r in results))
        errors = sum(1 for r in results if r.severity == Severity.ERROR)
        warnings = sum(1 for r in results if r.severity == Severity.WARNING)
        infos = sum(1 for r in results if r.severity == Severity.INFO)
        
        return cls(
            files_scanned=files_scanned,
            files_with_issues=files_with_issues,
            total_issues=len(results),
            errors=errors,
            warnings=warnings,
            infos=infos,
            rules_executed=rules_executed,
            skipped_files=skipped_files or [],
        )

    def get_exit_code(self) -> ExitCode:
        """Determine appropriate exit code based on results."""
        if self.errors > 0:
            return ExitCode.ERRORS_FOUND
        elif self.warnings > 0:
            return ExitCode.WARNINGS_FOUND
        return ExitCode.SUCCESS
