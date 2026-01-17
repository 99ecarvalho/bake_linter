"""
Code quality and style rules for Yocto recipes.

These rules check for general code quality issues and style violations.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class TrailingWhitespaceRule(BaseRule):
    """
    Check for trailing whitespace in recipe files.
    """
    
    rule_id = "STYLE001"
    name = "Trailing Whitespace"
    description = "Check for trailing whitespace"
    default_severity = Severity.INFO
    groups = ["style", "whitespace"]
    enabled_by_default = False  # Can be noisy
    hint = "Remove trailing whitespace"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            if line.rstrip() != line.rstrip("\n\r"):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Line has trailing whitespace",
                ))
        
        return results


class LongLineRule(BaseRule):
    """
    Check for excessively long lines.
    """
    
    rule_id = "STYLE002"
    name = "Long Lines"
    description = "Check for lines exceeding maximum length"
    default_severity = Severity.INFO
    groups = ["style"]
    enabled_by_default = False
    hint = "Consider breaking long lines using backslash continuation"

    # Default max line length
    DEFAULT_MAX_LENGTH = 120

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        max_length = self.get_option("max_length", self.DEFAULT_MAX_LENGTH)
        
        for line_num, line in enumerate(context.lines, start=1):
            if len(line.rstrip()) > max_length:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"Line exceeds {max_length} characters ({len(line.rstrip())} chars)",
                ))
        
        return results


class HardcodedPathsRule(BaseRule):
    """
    Check for hardcoded paths that should use variables.
    """
    
    rule_id = "STYLE003"
    name = "Hardcoded Paths"
    description = "Detect hardcoded paths that should use BitBake variables"
    default_severity = Severity.WARNING
    groups = ["style", "portability"]

    # Patterns for hardcoded paths and their suggested replacements
    HARDCODED_PATTERNS = [
        (re.compile(r'/usr/lib(?![a-z])'), "Use ${libdir} instead of /usr/lib"),
        (re.compile(r'/usr/bin(?![a-z])'), "Use ${bindir} instead of /usr/bin"),
        (re.compile(r'/usr/include(?![a-z])'), "Use ${includedir} instead of /usr/include"),
        (re.compile(r'/usr/share(?![a-z])'), "Use ${datadir} instead of /usr/share"),
        (re.compile(r'/etc(?![a-z])'), "Use ${sysconfdir} instead of /etc"),
        (re.compile(r'/var(?![a-z])'), "Use ${localstatedir} instead of /var"),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Skip SRC_URI lines (URLs legitimately contain paths)
            if "SRC_URI" in line:
                continue
            
            for pattern, message in self.HARDCODED_PATTERNS:
                if pattern.search(line):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=message,
                        context=stripped[:60],
                    ))
                    break  # One warning per line is enough
        
        return results


class TodoFixmeRule(BaseRule):
    """
    Flag TODO, FIXME, and XXX comments.
    """
    
    rule_id = "STYLE004"
    name = "TODO/FIXME Detection"
    description = "Flag TODO, FIXME, and XXX comments"
    default_severity = Severity.INFO
    groups = ["style", "todo"]
    enabled_by_default = False

    TODO_PATTERN = re.compile(r'#.*\b(TODO|FIXME|XXX|HACK)\b', re.IGNORECASE)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            match = self.TODO_PATTERN.search(line)
            if match:
                marker = match.group(1).upper()
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"{marker} comment found",
                    context=line.strip()[:60],
                    hint="Address the TODO/FIXME before release",
                ))
        
        return results


class EmptyVariableRule(BaseRule):
    """
    Check for empty variable assignments.
    """
    
    rule_id = "STYLE005"
    name = "Empty Variable Assignment"
    description = "Flag empty variable assignments"
    default_severity = Severity.INFO
    groups = ["style"]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for var_name, assignments in context.variables.items():
            for assignment in assignments:
                if not assignment.value.strip() and assignment.operator == "=":
                    # Skip known intentionally empty variables
                    if var_name in {"SRC_URI", "DEPENDS", "RDEPENDS"}:
                        continue
                    
                    results.append(self.create_result(
                        file=context.path,
                        line=assignment.line,
                        message=f"Empty assignment for '{var_name}'",
                        hint="Remove if intentionally empty, or add a comment explaining why",
                    ))
        
        return results


class DuplicateInheritRule(BaseRule):
    """
    Check for duplicate inherit statements.
    """
    
    rule_id = "STYLE006"
    name = "Duplicate Inherit"
    description = "Check for duplicate inherit class references"
    default_severity = Severity.WARNING
    groups = ["style", "redundancy"]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        seen_classes = {}  # class name -> first line number
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("inherit"):
                classes = stripped.split()[1:]
                for cls in classes:
                    if cls in seen_classes:
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=f"Duplicate inherit of '{cls}' (first seen line {seen_classes[cls]})",
                            hint="Remove the duplicate inherit statement",
                        ))
                    else:
                        seen_classes[cls] = line_num
        
        return results
