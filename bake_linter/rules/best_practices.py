# -*- coding: utf-8 -*-
"""
Best practices rules for Yocto recipes.

These rules check for adherence to Yocto best practices.

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


class DoFetchModificationRule(BaseRule):
    """
    Check for modifications to do_fetch task.
    
    Modifying do_fetch is an anti-pattern; sources should be added
    to SRC_URI instead for proper checksumming and caching.
    """
    
    rule_id = "BESTPRACTICE001"
    name = "do_fetch Modification"
    description = "Detects modifications to do_fetch which should use SRC_URI"
    default_severity = Severity.WARNING
    groups = ["best_practices"]
    hint = "Add sources to SRC_URI instead of modifying do_fetch"

    DO_FETCH_PATTERN = re.compile(r'^do_fetch(?::append|:prepend|_append|_prepend)?\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.DO_FETCH_PATTERN.match(stripped):
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="Modifying do_fetch is an anti-pattern",
                    context=stripped[:60],
                    hint="Add sources to SRC_URI for proper checksumming and caching",
                ))
        
        return results


class CleanupInConfigureRule(BaseRule):
    """
    Check for rm commands in do_configure.
    
    Cleanup operations should be in do_clean or handled by the build system.
    """
    
    rule_id = "BESTPRACTICE002"
    name = "Cleanup in do_configure"
    description = "Detects rm commands in do_configure that may be misplaced"
    default_severity = Severity.INFO
    groups = ["best_practices"]
    hint = "Move cleanup to do_clean or let build system handle it"

    CONFIGURE_TASK_PATTERN = re.compile(r'^do_configure(?:[_:]|$|\s*\(\))')
    RM_PATTERN = re.compile(r'^\s*rm\s+-rf?\s+')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_configure = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.CONFIGURE_TASK_PATTERN.match(stripped):
                in_do_configure = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            if in_do_configure:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_configure = False
                    brace_depth = 0
                    continue
                
                if self.RM_PATTERN.match(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="rm command in do_configure may be misplaced",
                        context=stripped[:60],
                        hint="Consider moving to do_clean or removing if unnecessary",
                    ))
        
        return results


class MissingHomepageRule(BaseRule):
    """
    Check for recipes without HOMEPAGE when upstream project exists.
    
    HOMEPAGE is important documentation for package maintainers.
    """
    
    rule_id = "BESTPRACTICE003"
    name = "Missing HOMEPAGE"
    description = "Detects recipes without HOMEPAGE"
    default_severity = Severity.INFO
    groups = ["best_practices", "documentation"]
    hint = "Add HOMEPAGE = \"URL\" pointing to project website"
    
    enabled_by_default = False

    # Known hosting services to suggest HOMEPAGE from
    GITHUB_PATTERN = re.compile(r'github\.com/([^/]+/[^/;]+)')
    GITLAB_PATTERN = re.compile(r'gitlab\.com/([^/]+/[^/;]+)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip certain recipe types
        filename = context.path.name.lower()
        if any(skip in filename for skip in ['packagegroup', '-image']):
            return results
        
        has_homepage = False
        suggested_url = None
        
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("HOMEPAGE"):
                has_homepage = True
                break
            
            # Try to extract URL from SRC_URI
            if not suggested_url:
                gh_match = self.GITHUB_PATTERN.search(stripped)
                if gh_match:
                    suggested_url = f"https://github.com/{gh_match.group(1)}"
                gl_match = self.GITLAB_PATTERN.search(stripped)
                if gl_match:
                    suggested_url = f"https://gitlab.com/{gl_match.group(1)}"
        
        if not has_homepage and suggested_url:
            results.append(self.create_result(
                file=context,
                line=1,
                message="Recipe missing HOMEPAGE",
                hint=f'Consider adding: HOMEPAGE = "{suggested_url}"',
            ))
        
        return results


class SedInDoInstallRule(BaseRule):
    """
    Check for sed usage in do_install.
    
    File modifications should happen in do_configure or via patches,
    not during installation.
    """
    
    rule_id = "BESTPRACTICE004"
    name = "sed in do_install"
    description = "Detects sed usage in do_install that should be in do_configure"
    default_severity = Severity.WARNING
    groups = ["best_practices"]
    hint = "Move sed commands to do_configure or create a proper patch"

    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')
    SED_PATTERN = re.compile(r'^\s*sed\s+-i')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_do_install = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                if self.SED_PATTERN.match(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="sed -i in do_install modifies installed files",
                        context=stripped[:60],
                        hint="Move to do_configure or create a patch for reproducibility",
                    ))
        
        return results
