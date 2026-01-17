# -*- coding: utf-8 -*-
"""
Core data models for the Bake Linter.

This module defines the fundamental data structures used throughout the linter,
including severity levels, lint results, and rule configuration.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Optional, List, Dict


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
    """
    path: Path
    content: str
    lines: List[str]
    variables: Dict[str, List["VariableAssignment"]] = field(default_factory=dict)
    file_type: str = ""
    is_autogenerated: bool = False
    parse_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Determine file type from extension."""
        if self.path.suffix == ".bb":
            self.file_type = "recipe"
        elif self.path.name.endswith(".bbappend"):
            self.file_type = "bbappend"
        elif self.path.suffix == ".inc":
            self.file_type = "include"
        else:
            self.file_type = "unknown"


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
