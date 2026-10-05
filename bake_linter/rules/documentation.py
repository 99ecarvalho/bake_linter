# -*- coding: utf-8 -*-
"""
Documentation rules for Yocto recipes.

These rules check for documentation quality and metadata completeness.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class IdenticalSummaryDescriptionRule(BaseRule):
    """
    Check for identical SUMMARY and DESCRIPTION.
    
    SUMMARY is a brief one-line overview, while DESCRIPTION should
    provide more details. Having them identical suggests copy-paste.
    """
    
    rule_id = "DOC001"
    name = "Identical SUMMARY and DESCRIPTION"
    description = "Detects when SUMMARY and DESCRIPTION have the same content"
    default_severity = Severity.WARNING
    groups = ["documentation", "metadata"]
    hint = "DESCRIPTION should expand on SUMMARY with more details"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        summary_value = None
        summary_line = 0
        description_value = None
        description_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Extract SUMMARY value
            match = re.match(r'^SUMMARY\s*=\s*["\'](.+?)["\']', stripped)
            if match:
                summary_value = match.group(1)
                summary_line = line_num
            
            # Extract DESCRIPTION value
            match = re.match(r'^DESCRIPTION\s*=\s*["\'](.+?)["\']', stripped)
            if match:
                description_value = match.group(1)
                description_line = line_num
        
        if summary_value and description_value:
            if summary_value.strip() == description_value.strip():
                results.append(self.create_result(
                    file=context,
                    line=description_line,
                    message="DESCRIPTION is identical to SUMMARY",
                    context=f"Both: \"{summary_value[:40]}...\"",
                    hint="DESCRIPTION should provide more details than SUMMARY",
                ))
        
        return results


class MissingSummaryRule(BaseRule):
    """
    Check for missing SUMMARY in recipe files.
    
    SUMMARY provides a brief one-line description of the package,
    shown in package managers and documentation.
    """
    
    rule_id = "DOC002"
    name = "Missing SUMMARY"
    description = "Detects recipe files without SUMMARY"
    default_severity = Severity.INFO
    groups = ["documentation", "metadata"]
    hint = "Add SUMMARY = \"Brief one-line description\""
    
    applicable_file_types = {"recipe"}

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        if not str(context.path).endswith('.bb'):
            return results
        
        has_summary = False
        
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("SUMMARY"):
                has_summary = True
                break
        
        if not has_summary:
            # Check if inheriting from a class that sets SUMMARY
            inherits_classes = False
            for line in context.lines:
                if 'inherit' in line and any(c in line for c in ['core-image', 'packagegroup']):
                    inherits_classes = True
                    break
            
            if not inherits_classes:
                results.append(self.create_result(
                    file=context,
                    line=1,
                    message="Recipe missing SUMMARY",
                    hint="Add SUMMARY with brief package description",
                ))
        
        return results


class TruncatedDescriptionRule(BaseRule):
    """
    Check for DESCRIPTION that's too short or truncated.
    
    If DESCRIPTION exists but is very brief (under 30 chars), it may
    be accidentally truncated or not properly set.
    """
    
    rule_id = "DOC003"
    name = "Truncated DESCRIPTION"
    description = "Detects DESCRIPTION that appears truncated"
    default_severity = Severity.INFO
    groups = ["documentation", "metadata"]
    hint = "DESCRIPTION should provide meaningful package details"

    MIN_DESCRIPTION_LENGTH = 30

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Look for short DESCRIPTION
            match = re.match(r'^DESCRIPTION\s*=\s*["\'](.+?)["\']', stripped)
            if match:
                desc = match.group(1)
                if len(desc) < self.MIN_DESCRIPTION_LENGTH:
                    # Skip if it's clearly a placeholder or reference
                    if '${' in desc or desc == 'TODO':
                        continue
                    
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"DESCRIPTION appears truncated ({len(desc)} chars)",
                        context=f'DESCRIPTION = "{desc}"',
                        hint=f"Consider expanding DESCRIPTION (min ~{self.MIN_DESCRIPTION_LENGTH} chars)",
                    ))
        
        return results
