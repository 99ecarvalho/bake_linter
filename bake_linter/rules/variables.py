"""
Variable assignment rules for Yocto recipes.

These rules check for proper variable usage patterns.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class GitRecipeWithoutSRCPVRule(BaseRule):
    """
    Check for git-based recipes without SRCPV in PV.
    
    Git recipes should include ${SRCPV} in PV for proper version tracking:
    - Allows sstate cache to detect source changes
    - Ensures correct package versioning
    - Standard practice for git recipes
    """
    
    rule_id = "VARIABLES001"
    name = "Git Recipe Without SRCPV"
    description = "Detects git-based recipes without SRCPV in PV"
    default_severity = Severity.WARNING
    groups = ["variables", "git"]
    hint = "Add +git${SRCPV} to PV for git-based recipes"

    GIT_SRC_PATTERN = re.compile(r'SRC_URI\s*[+:]?=.*(?:git://|gitsm://)')
    PV_PATTERN = re.compile(r'^PV\s*=\s*["\']([^"\']+)["\']')
    SRCPV_PATTERN = re.compile(r'\$\{SRCPV\}|SRCPV')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Check if this is a git recipe
        is_git_recipe = False
        pv_line = None
        pv_line_num = 0
        pv_value = ""
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.GIT_SRC_PATTERN.search(line):
                is_git_recipe = True
            
            pv_match = self.PV_PATTERN.match(stripped)
            if pv_match:
                pv_line = stripped
                pv_line_num = line_num
                pv_value = pv_match.group(1)
        
        # Skip _git.bb recipes (they typically inherit gitpkgv or similar)
        if context.path.name.endswith('_git.bb'):
            return results
        
        # Flag if git recipe without SRCPV in PV
        if is_git_recipe and pv_line and not self.SRCPV_PATTERN.search(pv_value):
            results.append(self.create_result(
                file=context.path,
                line=pv_line_num,
                message="Git-based recipe without ${SRCPV} in PV",
                context=pv_line[:60],
                hint="Change to PV = \"" + pv_value + "+git${SRCPV}\" for proper versioning",
            ))
        
        return results


class UnconventionalSAssignmentRule(BaseRule):
    """
    Check for unconventional S = "${WORKDIR}" assignment.
    
    S = "${WORKDIR}" is unusual and may indicate:
    - Flat source structure (no subdirectory)
    - Missing source directory specification
    - Potential build isolation issues
    """
    
    rule_id = "VARIABLES002"
    name = "Unconventional S Assignment"
    description = "Detects S = \"${WORKDIR}\" which is unconventional"
    default_severity = Severity.WARNING
    groups = ["variables"]
    hint = "Use S = \"${WORKDIR}/${PN}-${PV}\" or specify actual source directory"

    S_WORKDIR_PATTERN = re.compile(r'^S\s*=\s*["\']?\$\{WORKDIR\}["\']?\s*$')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.S_WORKDIR_PATTERN.match(stripped):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="Unconventional S = \"${WORKDIR}\" assignment",
                    context=stripped,
                    hint="Standard is S = \"${WORKDIR}/${PN}-${PV}\" or custom subdirectory",
                ))
        
        return results
