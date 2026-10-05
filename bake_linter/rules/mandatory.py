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

import re
from typing import List

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
        
        # A required .inc often carries the descriptive metadata; None means
        # an include could not be resolved and may set it.
        has_summary = context.sets_variable("SUMMARY")
        has_description = context.sets_variable("DESCRIPTION")
        
        if has_summary is False and has_description is False:
            results.append(self.create_result(
                file=context,
                message="Missing SUMMARY or DESCRIPTION variable",
            ))
        elif has_description and has_summary is False:
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

    # Classes that set SRC_URI themselves (pypi, gnomebase, xfce and the
    # like build it from the recipe name), and classes of recipes that fetch
    # nothing: images, packagegroups, SDKs, and recipes that build from
    # another recipe's tree.
    EXEMPT_CLASSES = {
        "pypi", "gnomebase", "xfce", "xfce-app", "xfce-panel-plugin",
        "thunar-plugin", "gpe", "clutter", "mozilla",
        "nopackages", "populate_sdk", "populate_sdk_ext", "toolchain-scripts",
        "kernelsrc", "image", "core-image", "packagegroup",
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

        # Inherited here or in an include
        if context.inherits & self.EXEMPT_CLASSES:
            return []

        # Any assignment counts (SRC_URI:append, SRC_URI[sha256sum], ...),
        # here or in an include. None means an include was not found and
        # may set it.
        if context.sets_variable("SRC_URI") is False:
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

    # pypi and xfce (and the xfce classes built on it) set HOMEPAGE
    # themselves; images, packagegroups and SDKs have no upstream project to
    # point at.
    EXEMPT_CLASSES = {
        "pypi", "xfce", "xfce-app", "xfce-panel-plugin", "thunar-plugin",
        "packagegroup", "image", "core-image",
        "nopackages", "populate_sdk",
    }

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []

        results = []

        # Inherited here or in an include
        if context.inherits & self.EXEMPT_CLASSES:
            return []

        # Get LICENSE value, here or in an include
        license_val = ""
        structures = [context.structure] + [
            included.structure for included in context.included_files or []
        ]
        for structure in structures:
            for assignment in structure.assignments:
                if assignment.name == "LICENSE":
                    license_val += " " + assignment.value.upper()

        # CLOSED/Proprietary licenses don't need homepage
        if "CLOSED" in license_val or "PROPRIETARY" in license_val:
            return []

        # None means an include was not found and may set it
        if context.sets_variable("HOMEPAGE") is False:
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

    # require recipes-core/images/core-image-minimal.bb
    IMAGE_RECIPE = re.compile(r'image\S*\.bb$')

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        recipe_name = context.path.stem
        
        # Inherited here or in an include
        inherits = context.inherits

        # Recipes that do not package anything need neither class
        if "nopackages" in inherits:
            return []

        # An include that was not found may inherit the class
        if context.included_files is None:
            return []

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
            # An image built on another image requires that image's .bb
            builds_on_image = any(
                self.IMAGE_RECIPE.search(path) for path in context.structure.includes
            )
            if not builds_on_image and "image" not in inherits and "core-image" not in inherits:
                results.append(self.create_result(
                    file=context,
                    message="Recipe named '*-image*' should inherit an image class",
                    hint="Add 'inherit core-image' or 'inherit image' to the recipe",
                ))
        
        return results
