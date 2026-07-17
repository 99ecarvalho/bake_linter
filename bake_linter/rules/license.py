# -*- coding: utf-8 -*-
"""
License-related lint rules for Yocto recipes.

These rules check for proper license declarations in BitBake recipes.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List, Set

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class LicenseRequiredRule(BaseRule):
    """
    Check that recipes have a LICENSE variable defined.
    
    Every BitBake recipe should explicitly declare its license using
    the LICENSE variable. This is required for license compliance
    and proper manifest generation.
    """
    
    rule_id = "LICENSE001"
    name = "License Required"
    description = "Check that LICENSE variable is defined in recipes"
    default_severity = Severity.ERROR
    groups = ["license", "mandatory", "compliance"]
    hint = "Add a LICENSE variable, e.g., LICENSE = \"MIT\" or LICENSE = \"CLOSED\""
    applicable_file_types = {"recipe"}  # Only .bb files, not .bbappend or .inc

    # Common valid licenses
    KNOWN_LICENSES: Set[str] = {
        "MIT", "Apache-2.0", "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
        "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later", "LGPL-2.0", "LGPL-2.1",
        "LGPL-3.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0",
        "CLOSED", "Proprietary", "PD", "Public Domain", "Zlib",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        
        # Check if LICENSE is defined
        if "LICENSE" not in context.variables:
            results.append(self.create_result(
                file=context,
                message="Missing LICENSE variable",
                hint=self.hint,
            ))
        else:
            # Validate license value
            for assignment in context.variables["LICENSE"]:
                value = assignment.value.strip()
                if not value:
                    results.append(self.create_result(
                        file=context,
                        line=assignment.line,
                        message="LICENSE variable is empty",
                        hint="Specify a valid license identifier",
                        severity=Severity.ERROR,
                    ))
        
        return results


class LicenseTypoRule(BaseRule):
    """
    Detect common typos in license variable names.
    
    Common typos like LICENSEX, LICENCE, LISENSE are detected and reported.
    """
    
    rule_id = "LICENSE002"
    name = "License Typo Detection"
    description = "Detect common typos in LICENSE variable name"
    default_severity = Severity.ERROR
    groups = ["license", "typo"]
    hint = "Correct the variable name to LICENSE"

    # Common typos for LICENSE
    LICENSE_TYPOS = {"LICENSEX", "LICENCE", "LISENSE", "LISENCE", "LISCENSE", "LISCENCE"}

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for var_name in context.variables:
            if var_name in self.LICENSE_TYPOS:
                assignments = context.variables[var_name]
                for assignment in assignments:
                    results.append(self.create_result(
                        file=context,
                        line=assignment.line,
                        message=f"Possible LICENSE typo: '{var_name}' should be 'LICENSE'",
                        context=f"{var_name} = \"{assignment.value}\"",
                    ))
        
        return results


class LicFilesChkSumRule(BaseRule):
    """
    Check for LIC_FILES_CHKSUM when LICENSE is not CLOSED.
    
    Non-CLOSED licenses should have a corresponding LIC_FILES_CHKSUM
    to verify the license file content.
    """
    
    rule_id = "LICENSE003"
    name = "License File Checksum"
    description = "Check that LIC_FILES_CHKSUM is present for non-CLOSED licenses"
    default_severity = Severity.WARNING
    groups = ["license", "compliance"]
    hint = "Add LIC_FILES_CHKSUM pointing to license file, e.g., LIC_FILES_CHKSUM = \"file://LICENSE;md5=...\""
    applicable_file_types = {"recipe"}

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        
        # Get LICENSE value
        if "LICENSE" not in context.variables:
            return []
        
        license_val = ""
        for assignment in context.variables["LICENSE"]:
            license_val = assignment.value.upper()
            break
        
        # CLOSED licenses don't need checksum
        if "CLOSED" in license_val:
            return []
        
        # Check for LIC_FILES_CHKSUM
        if "LIC_FILES_CHKSUM" not in context.variables:
            results.append(self.create_result(
                file=context,
                message="Missing LIC_FILES_CHKSUM for non-CLOSED license",
                hint=self.hint,
            ))
        
        return results
