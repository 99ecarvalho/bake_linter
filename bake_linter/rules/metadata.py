# -*- coding: utf-8 -*-
"""
Metadata rules for Yocto recipes.

These rules check for proper recipe metadata.

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


class MissingBugtrackerRule(BaseRule):
    """
    Check for recipes without BUGTRACKER metadata.
    
    BUGTRACKER helps track upstream issues and is useful documentation.
    """
    
    rule_id = "METADATA001"
    name = "Missing BUGTRACKER"
    description = "Detects recipes without BUGTRACKER metadata"
    default_severity = Severity.INFO
    groups = ["metadata", "documentation"]
    hint = "Add BUGTRACKER = \"URL\" pointing to upstream issue tracker"
    
    # Enabled by default but low priority
    enabled_by_default = False

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip native recipes, packagegroups, images
        filename = context.path.name.lower()
        if any(skip in filename for skip in ['-native', 'packagegroup', '-image']):
            return results
        
        has_bugtracker = False
        has_homepage = False
        
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("BUGTRACKER"):
                has_bugtracker = True
            if stripped.startswith("HOMEPAGE"):
                has_homepage = True
        
        # Only flag if there's a HOMEPAGE but no BUGTRACKER
        if has_homepage and not has_bugtracker:
            results.append(self.create_result(
                file=context,
                line=1,
                message="Recipe has HOMEPAGE but missing BUGTRACKER",
                hint="Add BUGTRACKER = \"URL\" for upstream issue tracking",
            ))
        
        return results


class CompatibleMachineSyntaxRule(BaseRule):
    """
    Check for improper COMPATIBLE_MACHINE regex syntax.
    
    COMPATIBLE_MACHINE should use proper regex with anchors.
    """
    
    rule_id = "METADATA002"
    name = "COMPATIBLE_MACHINE Syntax"
    description = "Detects improper COMPATIBLE_MACHINE regex syntax"
    default_severity = Severity.WARNING
    groups = ["metadata", "compatibility"]
    hint = "Use proper regex with anchors: ^(machine1|machine2)$"

    COMPAT_MACHINE_PATTERN = re.compile(r'^COMPATIBLE_MACHINE\s*=\s*["\']([^"\']+)["\']')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            match = self.COMPAT_MACHINE_PATTERN.match(stripped)
            if match:
                regex_value = match.group(1)
                
                # Check for missing anchors
                if not regex_value.startswith('^') and not regex_value.startswith('('):
                    # Simple machine name without anchors
                    if '|' not in regex_value and '*' not in regex_value and '.' not in regex_value:
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message="COMPATIBLE_MACHINE without regex anchors may match unintended machines",
                            context=stripped[:60],
                            hint=f'Use COMPATIBLE_MACHINE = "^{regex_value}$" for exact match',
                        ))
        
        return results


class MissingSectionRule(BaseRule):
    """
    Check for recipes without SECTION classification.
    
    SECTION helps with package organization and discovery.
    """
    
    rule_id = "METADATA003"
    name = "Missing SECTION"
    description = "Detects recipes without SECTION classification"
    default_severity = Severity.INFO
    groups = ["metadata"]
    hint = "Add SECTION = \"category\" (e.g., base, libs, net, utils)"
    
    enabled_by_default = False

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip certain recipe types
        filename = context.path.name.lower()
        if any(skip in filename for skip in ['packagegroup', '-image', '-native']):
            return results
        
        has_section = False
        
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("SECTION"):
                has_section = True
                break
        
        if not has_section:
            results.append(self.create_result(
                file=context,
                line=1,
                message="Recipe missing SECTION classification",
                hint="Add SECTION = \"category\" for package organization",
            ))
        
        return results
