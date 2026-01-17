# -*- coding: utf-8 -*-
"""
Syntax rules for Yocto recipes.

These rules check for syntax errors that could cause parse failures.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
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
    VAR_ASSIGN_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*(?:[_:][\w-]+)?\s*[+?:]?=')

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
            m = self.VAR_ASSIGN_PATTERN.match(stripped)
            if m:
                # Find the first non-space after =
                eq_idx = stripped.find('=')
                value = stripped[eq_idx+1:].lstrip()
                if not value:
                    continue
                first = value[0]
                last = value[-1] if value else ''
                # Only check if value starts with a quote
                if first in ('"', "'"):
                    # If it ends with the same quote, it's fine
                    if last == first:
                        continue
                    # Otherwise, check if the number of that quote is odd (not closed)
                    quote_count = value.count(first)
                    # Allow single quotes inside double-quoted strings and vice versa
                    if quote_count % 2 != 0:
                        msg = f"Unmatched {'double' if first == '"' else 'single'} quote in variable assignment"
                        hint = f"Add missing closing {'double' if first == '"' else 'single'} quote"
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message=msg,
                            context=stripped[:60],
                            hint=hint,
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


class MixedOverrideSyntaxRule(BaseRule):
    """
    Check for recipes mixing old underscore and new colon override syntax.
    
    Mixing _append with :append in the same file causes parsing issues
    in modern Yocto versions and indicates incomplete migration.
    
    IMPORTANT: Only checks BitBake variable assignments and function declarations,
    NOT shell code inside task functions (where underscores in filenames are valid).
    """
    
    rule_id = "SYNTAX005"
    name = "Mixed Override Syntax"
    description = "Detects recipes using both old (_) and new (:) override syntax"
    default_severity = Severity.ERROR
    groups = ["syntax", "deprecated"]
    hint = "Convert all underscores to colons for overrides"

    # Pattern to match BitBake variable assignments (where override syntax matters)
    # Matches: VAR_append = "...", VAR:append = "...", RDEPENDS_${PN} = "..."
    VAR_ASSIGN_PATTERN = re.compile(
        r'^([A-Z_][A-Z0-9_]*)([_:][a-zA-Z0-9_${}\-]+)*\s*[+?:]?='
    )
    
    # Pattern to match task/function declarations
    # Matches: do_install_append() {, do_configure:prepend() {
    FUNC_DECL_PATTERN = re.compile(
        r'^(do_\w+|python\s+\w+|addtask\s+\w+|deltask\s+\w+|fakeroot\s+\w+)([_:][a-zA-Z0-9_${}\-]+)*\s*\('
    )

    # Old underscore-based override patterns (for variable/function context)
    OLD_OVERRIDE_SUFFIXES = ['_append', '_prepend', '_remove', '_class-', '_pn-', '_${PN}']
    
    # New colon-based override patterns (for variable/function context)  
    NEW_OVERRIDE_SUFFIXES = [':append', ':prepend', ':remove', ':class-', ':pn-', ':${PN}']

    def _has_old_syntax(self, identifier: str) -> bool:
        """Check if identifier uses old underscore override syntax."""
        for suffix in self.OLD_OVERRIDE_SUFFIXES:
            if suffix in identifier:
                return True
        return False
    
    def _has_new_syntax(self, identifier: str) -> bool:
        """Check if identifier uses new colon override syntax."""
        for suffix in self.NEW_OVERRIDE_SUFFIXES:
            if suffix in identifier:
                return True
        return False

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        old_syntax_lines = []
        new_syntax_lines = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Check for variable assignment
            var_match = self.VAR_ASSIGN_PATTERN.match(stripped)
            if var_match:
                # Get the full variable name with any overrides
                var_part = stripped[:stripped.find('=')].rstrip().rstrip('+?:')
                
                if self._has_old_syntax(var_part):
                    old_syntax_lines.append((line_num, stripped))
                elif self._has_new_syntax(var_part):
                    new_syntax_lines.append((line_num, stripped))
                continue
            
            # Check for function declaration (do_install_append, do_configure:prepend, etc.)
            func_match = self.FUNC_DECL_PATTERN.match(stripped)
            if func_match:
                # Get the function name part before (
                func_part = stripped[:stripped.find('(')].strip()
                
                if self._has_old_syntax(func_part):
                    old_syntax_lines.append((line_num, stripped))
                elif self._has_new_syntax(func_part):
                    new_syntax_lines.append((line_num, stripped))
                continue
            
            # Also check for addhandler, EXPORT_FUNCTIONS, etc. with overrides
            # These are top-level BitBake directives
            if any(stripped.startswith(kw) for kw in ['addhandler', 'EXPORT_FUNCTIONS', 'inherit']):
                if self._has_old_syntax(stripped):
                    old_syntax_lines.append((line_num, stripped))
                elif self._has_new_syntax(stripped):
                    new_syntax_lines.append((line_num, stripped))
        
        # Flag if both syntaxes are used
        if old_syntax_lines and new_syntax_lines:
            # Report on the first old syntax line
            line_num, line_content = old_syntax_lines[0]
            results.append(self.create_result(
                file=context.path,
                line=line_num,
                message=f"Mixed override syntax: found {len(old_syntax_lines)} old (_) and {len(new_syntax_lines)} new (:) syntax uses",
                context=line_content[:60],
                hint="Convert all old underscore syntax (_append) to new colon syntax (:append)",
            ))
        
        return results


class InvalidOverrideOrderingRule(BaseRule):
    """
    Check for incorrect override ordering in variable assignments.
    
    Canonical order: :class-*:pn-*:machine:distro:append/:prepend/:remove
    Operation overrides (:append, :prepend, :remove) should always be last.
    """
    
    rule_id = "SYNTAX006"
    name = "Invalid Override Ordering"
    description = "Detects incorrect override ordering in variable assignments"
    default_severity = Severity.WARNING
    groups = ["syntax"]
    hint = "Place :append/:prepend/:remove at the end of override chain"

    # Operation overrides that should be last
    OPERATION_OVERRIDES = [':append', ':prepend', ':remove']
    
    # Pattern to find variable assignments with multiple overrides
    MULTI_OVERRIDE_PATTERN = re.compile(r'^([A-Z_][A-Z0-9_]*)((?::[a-zA-Z0-9_${}+-]+)+)\s*[+?:]?=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            match = self.MULTI_OVERRIDE_PATTERN.match(stripped)
            if match:
                overrides_str = match.group(2)
                
                # Split into individual overrides
                overrides = [o for o in overrides_str.split(':') if o]
                
                if len(overrides) >= 2:
                    # Check if operation override is not last
                    for i, override in enumerate(overrides[:-1]):  # Exclude last
                        if any(op.lstrip(':') == override for op in self.OPERATION_OVERRIDES):
                            results.append(self.create_result(
                                file=context.path,
                                line=line_num,
                                message=f"Override ':{override}' should be last in override chain",
                                context=stripped[:60],
                                hint="Reorder to: VAR:class-*:pn-*:append (operation last)",
                            ))
                            break
        
        return results

