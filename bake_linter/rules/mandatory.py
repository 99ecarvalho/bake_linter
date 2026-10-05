# -*- coding: utf-8 -*-
"""
Mandatory variable rules for Yocto recipes.

These rules check for required variables in BitBake recipes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

from typing import List, Set

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class SummaryDescriptionRule(BaseRule):
    """
    Check that recipes have SUMMARY or DESCRIPTION defined.
    
    Recipes should have a SUMMARY (preferred) or DESCRIPTION variable
    to document what the recipe provides.
    """
    
    rule_id = "MANDATORY001"
    name = "Summary/Description Required"
    description = "Check that SUMMARY or DESCRIPTION is defined"
    default_severity = Severity.WARNING
    groups = ["mandatory", "documentation"]
    hint = "Add SUMMARY = \"Brief description of the recipe\""
    applicable_file_types = {"recipe"}

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        
        has_summary = "SUMMARY" in context.variables
        has_description = "DESCRIPTION" in context.variables
        
        if not has_summary and not has_description:
            results.append(self.create_result(
                file=context,
                message="Missing SUMMARY or DESCRIPTION variable",
            ))
        elif has_description and not has_summary:
            # Suggest using SUMMARY instead of DESCRIPTION
            results.append(self.create_result(
                file=context,
                message="Consider using SUMMARY instead of DESCRIPTION (SUMMARY is preferred)",
                severity=Severity.INFO,
                hint="SUMMARY is preferred over DESCRIPTION for brief recipe descriptions",
            ))
        
        return results


class SrcUriRule(BaseRule):
    """
    Check SRC_URI variable in recipes.
    
    Most recipes should have a SRC_URI defining where to fetch the source.
    Exceptions include meta-recipes (packagegroups, images) and local source.
    """
    
    rule_id = "MANDATORY002"
    name = "SRC_URI Check"
    description = "Check that SRC_URI is properly defined"
    default_severity = Severity.INFO
    groups = ["mandatory", "source"]
    hint = "Add SRC_URI pointing to the source location"
    applicable_file_types = {"recipe"}

    # Recipe types that don't need SRC_URI
    EXEMPT_PATTERNS = {
        "packagegroup-", "image-", "-image", 
        "-native", "-cross", "-sdk",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        recipe_name = context.path.stem
        
        # Check if this recipe type is exempt
        for pattern in self.EXEMPT_PATTERNS:
            if pattern in recipe_name:
                return []
        
        # Check for inherit packagegroup or image
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("inherit"):
                if "packagegroup" in stripped or "image" in stripped or "core-image" in stripped:
                    return []
        
        if "SRC_URI" not in context.variables:
            results.append(self.create_result(
                file=context,
                message="Missing SRC_URI variable",
                hint="Add SRC_URI or confirm this recipe uses local/generated sources",
            ))
        
        return results


class HomepageRule(BaseRule):
    """
    Check for HOMEPAGE variable in open-source recipes.
    
    Recipes with non-CLOSED licenses should have a HOMEPAGE pointing
    to the upstream project.
    """
    
    rule_id = "MANDATORY003"
    name = "Homepage Check"
    description = "Check that HOMEPAGE is defined for open-source recipes"
    default_severity = Severity.INFO
    groups = ["mandatory", "documentation"]
    hint = "Add HOMEPAGE = \"https://project-homepage.com\""
    applicable_file_types = {"recipe"}

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        
        # Get LICENSE value
        license_val = ""
        if "LICENSE" in context.variables:
            for assignment in context.variables["LICENSE"]:
                license_val = assignment.value.upper()
                break
        
        # CLOSED/Proprietary licenses don't need homepage
        if "CLOSED" in license_val or "PROPRIETARY" in license_val:
            return []
        
        if "HOMEPAGE" not in context.variables:
            results.append(self.create_result(
                file=context,
                message="Missing HOMEPAGE variable for open-source recipe",
            ))
        
        return results


class InheritCheck(BaseRule):
    """
    Check for missing inherit directives based on recipe patterns.
    """
    
    rule_id = "MANDATORY004"
    name = "Inherit Directive Check"
    description = "Check for appropriate inherit directives"
    default_severity = Severity.WARNING
    groups = ["mandatory", "inherit"]
    applicable_file_types = {"recipe"}

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        recipe_name = context.path.stem
        
        # Collect all inherit statements
        inherits: Set[str] = set()
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("inherit"):
                # Parse inherit classes
                parts = stripped.split()[1:]
                inherits.update(parts)
        
        # Check for packagegroup naming convention
        if recipe_name.startswith("packagegroup-"):
            if "packagegroup" not in inherits:
                results.append(self.create_result(
                    file=context,
                    message="Recipe named 'packagegroup-*' should 'inherit packagegroup'",
                    hint="Add 'inherit packagegroup' to the recipe",
                ))
        
        # Check for image naming convention
        if recipe_name.endswith("-image") or "-image-" in recipe_name:
            if "image" not in inherits and "core-image" not in inherits:
                results.append(self.create_result(
                    file=context,
                    message="Recipe named '*-image*' should inherit an image class",
                    hint="Add 'inherit core-image' or 'inherit image' to the recipe",
                ))
        
        return results
