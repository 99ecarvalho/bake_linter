"""
Syntax rules for Yocto recipes.

These rules check for syntax errors that could cause parse failures.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class UnmatchedQuotesRule(BaseRule):
    """
    Check for unmatched quotes in variable assignments.
    
    Unmatched quotes will cause BitBake parse errors.
    """
    
    rule_id = "SYNTAX001"
    name = "Unmatched Quotes"
    description = "Detects unmatched quotes in variable assignments"
    default_severity = Severity.ERROR
    groups = ["syntax"]
    hint = "Add missing closing quote"

    # Pattern for variable assignments
    VAR_ASSIGN_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*(?:[_:]\S+)?\s*[+?:]?=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.rstrip()
            
            if stripped.startswith("#"):
                continue
            
            # Skip lines with continuation
            if stripped.endswith('\\'):
                continue
            
            # Check variable assignments
            if self.VAR_ASSIGN_PATTERN.match(stripped):
                # Count quotes (simple check, doesn't handle escaped quotes perfectly)
                double_quotes = stripped.count('"') - stripped.count('\\"')
                single_quotes = stripped.count("'") - stripped.count("\\'")
                
                if double_quotes % 2 != 0:
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Unmatched double quote in variable assignment",
                        context=stripped[:60],
                        hint="Add missing closing double quote",
                    ))
                
                if single_quotes % 2 != 0:
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Unmatched single quote in variable assignment",
                        context=stripped[:60],
                        hint="Add missing closing single quote",
                    ))
        
        return results


class MissingLineContinuationRule(BaseRule):
    """
    Check for potential missing line continuations in multiline assignments.
    
    Detects patterns that look like incomplete multiline assignments.
    """
    
    rule_id = "SYNTAX002"
    name = "Missing Line Continuation"
    description = "Detects potential missing line continuation characters"
    default_severity = Severity.WARNING
    groups = ["syntax"]
    hint = "Add \\ at end of line for multiline assignments"

    # Pattern for variable assignment start
    VAR_START_PATTERN = re.compile(r'^([A-Z_][A-Z0-9_]*(?:[_:]\S+)?)\s*[+?:]?=\s*"')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_multiline = False
        start_line = 0
        var_name = ""
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.rstrip()
            
            if stripped.startswith("#"):
                continue
            
            if not in_multiline:
                match = self.VAR_START_PATTERN.match(stripped)
                if match:
                    var_name = match.group(1)
                    # Check if line ends with quote (complete) or continuation
                    if not stripped.endswith('"') and not stripped.endswith('\\'):
                        # Starts assignment but doesn't complete or continue
                        in_multiline = True
                        start_line = line_num
            else:
                # In multiline mode
                if stripped.endswith('"'):
                    in_multiline = False
                elif stripped.endswith('\\'):
                    continue  # Proper continuation
                elif stripped and not stripped.startswith('#'):
                    # Line doesn't end with continuation or closing quote
                    # This might be an error
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message=f"Possible missing line continuation for '{var_name}'",
                        context=stripped[:60],
                        hint="Add \\ at end of line or close the string with \"",
                    ))
                    in_multiline = False
        
        return results


class TabsInPythonFunctionRule(BaseRule):
    """
    Check for tab characters in Python function indentation.
    
    Python requires consistent indentation. Mixing tabs and spaces
    can cause IndentationError.
    """
    
    rule_id = "SYNTAX003"
    name = "Tabs in Python Functions"
    description = "Detects tab characters in Python function indentation"
    default_severity = Severity.ERROR
    groups = ["syntax", "python"]
    hint = "Replace tabs with 4 spaces"

    # Pattern to detect python function definition
    PYTHON_FUNC_PATTERN = re.compile(r'^python\s+\w+\s*\(|^def\s+\w+\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_python_func = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Detect python function start
            if self.PYTHON_FUNC_PATTERN.match(stripped):
                in_python_func = True
                brace_depth = 0
            
            if in_python_func:
                brace_depth += stripped.count('{') - stripped.count('}')
                
                # Check for tabs
                if '\t' in line and not stripped.startswith('#'):
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Tab character in Python function (use spaces)",
                        context=stripped[:60],
                        hint="Replace tabs with 4 spaces for consistent indentation",
                    ))
                
                if brace_depth <= 0 and '{' in line:
                    brace_depth = 1
                elif brace_depth <= 0:
                    in_python_func = False
        
        return results


class UnclosedVariableExpansionRule(BaseRule):
    """
    Check for unclosed ${...} variable expansions.
    
    Missing closing braces will cause BitBake parse errors.
    """
    
    rule_id = "SYNTAX004"
    name = "Unclosed Variable Expansion"
    description = "Detects unclosed ${...} variable expansions"
    default_severity = Severity.ERROR
    groups = ["syntax"]
    hint = "Add missing } to close variable expansion"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.rstrip()
            
            if stripped.startswith("#"):
                continue
            
            # Skip lines with continuation (check full multiline later)
            if stripped.endswith('\\'):
                continue
            
            # Count ${ and } - simple heuristic
            # This doesn't perfectly handle nested expansions or strings
            open_count = stripped.count('${')
            close_count = stripped.count('}')
            
            # Account for } that aren't closing ${ (like function braces)
            # Heuristic: check if there are more ${ than }
            # and the line contains ${
            if open_count > 0 and open_count > close_count:
                # Verify there's actually an unclosed expansion
                depth = 0
                in_expansion = False
                for i, char in enumerate(stripped):
                    if stripped[i:i+2] == '${':
                        depth += 1
                        in_expansion = True
                    elif char == '}' and in_expansion:
                        depth -= 1
                        if depth == 0:
                            in_expansion = False
                
                if depth > 0:
                    results.append(self.create_result(
                        file=context.path,
                        line=line_num,
                        message="Unclosed variable expansion ${...}",
                        context=stripped[:60],
                        hint="Add missing } to close the variable expansion",
                    ))
        
        return results
