# -*- coding: utf-8 -*-
"""
Python code rules for Yocto recipes.

These rules check for issues in inline Python code within recipes
and Python function implementations.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class PrintVsBbNoteRule(BaseRule):
    """
    Check for print() usage instead of bb.note/bb.warn/bb.error.
    
    In BitBake Python code, bb.note() etc should be used instead of
    print() for proper logging integration.
    """
    
    rule_id = "PYTHON001"
    name = "Print Instead of bb.note"
    description = "Detects print() usage where bb.note/bb.warn should be used"
    default_severity = Severity.INFO
    groups = ["style", "logging", "python"]
    hint = "Use bb.note(), bb.warn(), bb.error() for logging in BitBake"

    PRINT_PATTERN = re.compile(r'\bprint\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_python = False
        python_start = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Track inline Python blocks: python __anonymous() { ... }
            # or python do_foo() { ... }
            if re.match(r'^python\s+(\w+\s*)?\(\)\s*\{', stripped):
                in_python = True
                python_start = line_num
                continue
            
            # Track ${@...} inline Python
            if '${@' in stripped:
                if self.PRINT_PATTERN.search(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="print() in inline Python expression",
                        context=stripped[:60],
                        hint="Use bb.note() for logging in BitBake",
                    ))
            
            if in_python and stripped == '}':
                in_python = False
                continue
            
            if in_python and self.PRINT_PATTERN.search(stripped):
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="print() used instead of bb.note/bb.warn/bb.error",
                    context=stripped[:60],
                    hint="Use bb.note(), bb.warn(), bb.error() for proper logging",
                ))
        
        return results


class DirectVarAssignmentRule(BaseRule):
    """
    Check for direct variable assignment instead of d.setVar in Python.
    
    In BitBake Python functions, variables should be set using d.setVar()
    or d.setVarFlag() rather than direct Python assignment.
    
    Note: This rule is informational as there are valid cases for local
    Python variables. It flags patterns that look like BitBake variable
    assignments without d.setVar.
    """
    
    rule_id = "PYTHON002"
    name = "Variable Assignment Without d.setVar"
    description = "Detects potential missing d.setVar() in Python functions"
    default_severity = Severity.INFO
    groups = ["style", "python"]
    hint = "Use d.setVar('VAR', value) to set BitBake variables in Python"

    # Common BitBake variables that might be accidentally assigned directly
    BITBAKE_VARS = [
        'PN', 'PV', 'PR', 'SRCREV', 'SRC_URI', 'S', 'B', 'D',
        'DEPENDS', 'RDEPENDS', 'PACKAGES', 'FILES', 'WORKDIR',
        'LICENSE', 'LIC_FILES_CHKSUM', 'HOMEPAGE', 'DESCRIPTION',
        'SUMMARY', 'SECTION', 'EXTRA_OECONF', 'EXTRA_OECMAKE',
        'PACKAGECONFIG', 'COMPATIBLE_MACHINE', 'MACHINE_FEATURES',
        'DISTRO_FEATURES', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS',
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_python = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track Python function entry
            if re.match(r'^python\s+(\w+\s*)?\(\)\s*\{', stripped):
                in_python = True
                continue
            
            if in_python and stripped == '}':
                in_python = False
                continue
            
            if in_python:
                # Look for direct assignments to BitBake variable names
                for var in self.BITBAKE_VARS:
                    # Match: VAR = "..." or VAR = '...' (Python assignment)
                    # but not d.getVar('VAR') or d.setVar('VAR', ...)
                    pattern = re.compile(rf'^{var}\s*=\s*["\'\[]')
                    if pattern.match(stripped):
                        # Check if it's actually a d.setVar call (false positive)
                        if 'd.setVar' not in stripped:
                            results.append(self.create_result(
                                file=context,
                                line=line_num,
                                message=f"Direct assignment to '{var}' in Python function",
                                context=stripped[:60],
                                hint=f"Use d.setVar('{var}', value) to set BitBake variables",
                            ))
        
        return results


class AnonymousPythonIssuesRule(BaseRule):
    """
    Check for common issues in anonymous Python functions.
    
    Anonymous Python functions (python __anonymous() or python()) have
    specific requirements and common pitfalls.
    """
    
    rule_id = "PYTHON003"
    name = "Anonymous Python Issues"
    description = "Detects common issues in anonymous Python functions"
    default_severity = Severity.WARNING
    groups = ["python", "reliability"]
    hint = "Ensure proper error handling in anonymous Python"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_anon_python = False
        anon_start = 0
        uses_d_getvar = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Track anonymous Python function
            if re.match(r'^python\s*(__anonymous)?\s*\(\)\s*\{', stripped):
                in_anon_python = True
                anon_start = line_num
                uses_d_getvar = False
                continue
            
            if in_anon_python:
                if 'd.getVar' in stripped:
                    uses_d_getvar = True
                
                # Check for common issues
                # 1. Using raise without bb.fatal
                if re.search(r'\braise\s+\w+', stripped) and 'bb.fatal' not in stripped:
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="raise in anonymous Python - consider bb.fatal()",
                        context=stripped[:60],
                        hint="bb.fatal() provides better error messages in BitBake",
                    ))
                
                # 2. sys.exit() in anonymous Python
                if 'sys.exit' in stripped:
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="sys.exit() in anonymous Python function",
                        context=stripped[:60],
                        hint="Use bb.fatal() instead of sys.exit()",
                    ))
                
                if stripped == '}':
                    in_anon_python = False
        
        return results
