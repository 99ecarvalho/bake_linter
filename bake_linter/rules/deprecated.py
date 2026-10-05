# -*- coding: utf-8 -*-
"""
Deprecated syntax detection rules for Yocto recipes.

These rules detect usage of deprecated BitBake syntax that should be updated.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List, Dict, Pattern

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class DeprecatedOverrideSyntaxRule(BaseRule):
    """
    Detect deprecated override syntax using underscore.
    
    Since Yocto Honister (3.4), the override syntax changed from
    underscore (_) to colon (:). For example:
    - Old: RDEPENDS_${PN} += "foo"
    - New: RDEPENDS:${PN} += "foo"
    """
    
    rule_id = "DEPRECATED001"
    name = "Deprecated Override Syntax"
    description = "Detect old underscore-based override syntax"
    default_severity = Severity.WARNING
    groups = ["deprecated", "syntax"]
    hint = "Use colon (:) instead of underscore (_) for overrides. Example: RDEPENDS:${PN} instead of RDEPENDS_${PN}"

    # Pattern to match old override syntax
    # Matches: VAR_something, VAR_${PN}, VAR_append, etc.
    OLD_OVERRIDE_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9_]*?)_(append|prepend|remove|'
        r'\$\{[A-Z_]+\}|[a-z][a-z0-9_-]*)\s*[+?:]?='
    )

    # Known variables that legitimately use underscore in their base name
    UNDERSCORE_VARS = {
        "SRC_URI", "LIC_FILES_CHKSUM", "PR_INC", "PV_MAJOR", "PV_MINOR",
        "COMPATIBLE_MACHINE", "PREFERRED_VERSION", "PREFERRED_PROVIDER",
        "TUNE_FEATURES", "PACKAGE_ARCH", "TARGET_ARCH", "BUILD_ARCH",
        "IMAGE_INSTALL", "IMAGE_FEATURES", "DISTRO_FEATURES",
        "MACHINE_FEATURES", "EXTRA_OECONF", "EXTRA_OECMAKE",
        "FILES_SOLIBSDEV", "INSANE_SKIP", "ALLOW_EMPTY",
        # update-alternatives.bbclass reads ALTERNATIVE_PRIORITY_<pkg> and
        # ALTERNATIVE_TARGET_<pkg> by name (getVar('ALTERNATIVE_PRIORITY_%s'
        # % pkg)): the underscore is part of the variable, not an override.
        "ALTERNATIVE_PRIORITY", "ALTERNATIVE_TARGET",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue
            
            # Check for old override syntax
            match = self.OLD_OVERRIDE_PATTERN.match(stripped)
            if match:
                var_base = match.group(1)
                override = match.group(2)
                
                # Skip if base var legitimately has underscore
                if var_base in self.UNDERSCORE_VARS:
                    continue
                
                # Check for _append, _prepend, _remove (definitely deprecated)
                if override in ("append", "prepend", "remove"):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"Deprecated '_{override}' syntax; use ':{override}' instead",
                        context=stripped[:80],
                        hint=f"Change '{var_base}_{override}' to '{var_base}:{override}'",
                    ))
                elif override.startswith("${"):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"Deprecated underscore override syntax; use colon instead",
                        context=stripped[:80],
                        hint=f"Change '{var_base}_{override}' to '{var_base}:{override}'",
                    ))
        
        return results


class DeprecatedFunctionsRule(BaseRule):
    """
    Detect usage of deprecated BitBake functions.
    """
    
    rule_id = "DEPRECATED002"
    name = "Deprecated Functions"
    description = "Detect usage of deprecated BitBake functions"
    default_severity = Severity.WARNING
    groups = ["deprecated"]
    hint = "Update to use the replacement function"

    # Mapping of deprecated functions to their replacements
    DEPRECATED_FUNCTIONS: Dict[str, str] = {
        "base_contains": "bb.utils.contains",
        "oe_filter": "Use oe.utils.str_filter",
        "oe_filter_out": "Use oe.utils.str_filter_out",
        "base_conditional": "Use oe.utils.conditional",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            for old_func, replacement in self.DEPRECATED_FUNCTIONS.items():
                if old_func in line:
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"Deprecated function '{old_func}'",
                        context=stripped[:80],
                        hint=f"Replace with {replacement}",
                    ))
        
        return results


class DeprecatedVariablesRule(BaseRule):
    """
    Detect usage of deprecated BitBake variables.
    """
    
    rule_id = "DEPRECATED003"
    name = "Deprecated Variables"
    description = "Detect usage of deprecated BitBake variables"
    default_severity = Severity.WARNING
    groups = ["deprecated"]

    # Mapping of deprecated variables to their replacements
    DEPRECATED_VARIABLES: Dict[str, str] = {
        "PRINC": "Removed in modern Yocto; remove this variable",
        "PSTAGE_BROKEN": "Removed; use BROKEN instead",
        "SRCREV_pn-": "Use SRCREV:pn- (colon syntax)",
        "PREFERRED_VERSION_virtual/": "Prefer using PREFERRED_PROVIDER",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for var_name, assignments in context.variables.items():
            for deprecated, hint in self.DEPRECATED_VARIABLES.items():
                if var_name == deprecated or var_name.startswith(deprecated):
                    for assignment in assignments:
                        results.append(self.create_result(
                            file=context,
                            line=assignment.line,
                            message=f"Deprecated variable '{var_name}'",
                            hint=hint,
                        ))
        
        return results


class PythonTwoSyntaxRule(BaseRule):
    """
    Detect Python 2 syntax in inline Python code.
    
    BitBake now uses Python 3; Python 2 syntax should be updated.
    """
    
    rule_id = "DEPRECATED004"
    name = "Python 2 Syntax Detection"
    description = "Detect Python 2 syntax in inline Python"
    default_severity = Severity.ERROR
    groups = ["deprecated", "python"]

    # Patterns that indicate Python 2 syntax
    PYTHON2_PATTERNS = [
        (re.compile(r'print\s+["\']'), "Use print() function instead of print statement"),
        (re.compile(r'except\s+\w+\s*,\s*\w+:'), "Use 'except Error as e:' syntax"),
        (re.compile(r'\.has_key\s*\('), "Use 'key in dict' instead of dict.has_key(key)"),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        in_python = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Track if we're in a python block
            if stripped.startswith("python"):
                in_python = True
            elif in_python and stripped == "}":
                in_python = False
            
            # Also check inline python ${@...}
            has_inline_python = "${@" in line
            
            if in_python or has_inline_python:
                for pattern, message in self.PYTHON2_PATTERNS:
                    if pattern.search(line):
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=message,
                            context=stripped[:80],
                        ))
        
        return results
