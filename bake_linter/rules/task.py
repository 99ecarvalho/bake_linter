# -*- coding: utf-8 -*-
"""
Task implementation rules for Yocto recipes.

These rules check for issues in shell task implementations like
do_compile, do_install, etc.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List, Set

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class UnquotedVariableRule(BaseRule):
    """
    Check for unquoted shell variable expansions in tasks.
    
    Unquoted variables can cause issues with paths containing spaces
    or special characters. This is a common shell scripting pitfall.
    
    IMPORTANT: This rule distinguishes between:
    - ${VAR} - BitBake variable expansion (SAFE - expanded before shell sees it)
    - $VAR   - Shell variable (NEEDS QUOTES - shell does word splitting)
    
    BitBake expands ${VAR} at parse time, so the shell never sees the variable
    syntax - it only sees the expanded value as a single token. This is safe.
    
    Only $VAR (without braces) is a shell variable that needs quoting.
    """
    
    rule_id = "TASK001"
    name = "Unquoted Variable Expansion"
    description = "Detects unquoted shell variables (not BitBake ${VAR}) in task code"
    default_severity = Severity.WARNING
    groups = ["shell", "reliability"]
    hint = "Quote shell variable expansions: \"$var\" instead of $var"

    # High-risk variables that should be quoted when used as shell variables
    # Note: ${VAR} is BitBake expansion (safe), $VAR is shell (needs quotes)
    HIGH_RISK_VARS = ['D', 'S', 'B', 'WORKDIR', 'STAGING_DIR', 'TMPDIR', 'HOME']

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_task = False
        task_start_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track task function entry/exit
            if re.match(r'^(do_\w+|fakeroot\s+do_\w+)\s*\(\)\s*\{', stripped):
                in_task = True
                task_start_line = line_num
                continue
            
            if in_task and stripped == '}':
                in_task = False
                continue
            
            if in_task:
                # Check high-risk variables - ONLY flag $VAR (shell variable), NOT ${VAR} (BitBake)
                for var in self.HIGH_RISK_VARS:
                    # Pattern matches $VAR but NOT ${VAR}
                    # $VAR is a shell variable and needs quoting
                    # ${VAR} is BitBake expansion, which is safe (expanded before shell)
                    pattern = re.compile(rf'\${var}\b(?!\}})')
                    matches = pattern.finditer(stripped)
                    for match in matches:
                        # Verify this is truly $VAR and not part of ${VAR}
                        pos = match.start()
                        # Check if preceded by { (which would make it ${VAR})
                        if pos > 0 and stripped[pos-1] == '{':
                            continue  # This is ${VAR}, BitBake expansion, skip
                        
                        # Check if it's actually unquoted
                        if not self._is_properly_quoted(stripped, var, pos):
                            results.append(self.create_result(
                                file=context,
                                line=line_num,
                                message=f"Shell variable ${var} should be quoted (use \"${var}\" or \"${{{var}}}\")",
                                context=stripped[:60],
                                hint=f'Quote shell variables: "${var}" or use BitBake expansion "${{{{var}}}}"',
                            ))
        
        return results
    
    def _is_properly_quoted(self, line: str, var: str, pos: int) -> bool:
        """Check if a variable at position is properly quoted in the line."""
        # Find if position is inside double quotes
        in_quotes = False
        i = 0
        while i < pos:
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_quotes = not in_quotes
            i += 1
        return in_quotes


class SudoUsageRule(BaseRule):
    """
    Check for sudo usage in task implementations.
    
    Yocto builds should never require sudo - they use pseudo/fakeroot
    for privileged operations. sudo indicates a broken build process.
    
    Excludes:
    - USERADD_PARAM where 'sudo' is a Unix group name (e.g., -G sudo)
    - Group membership specifications
    """
    
    rule_id = "TASK002"
    name = "Sudo Usage in Tasks"
    description = "Detects sudo usage in recipe task code"
    default_severity = Severity.ERROR
    groups = ["security", "build"]
    hint = "Use fakeroot for privileged operations, not sudo"

    # Pattern for sudo as a command (not as a group name)
    SUDO_CMD_PATTERN = re.compile(r'(?:^|\s|;|&&|\|\||\|)\s*sudo\s+')
    
    # Variables where 'sudo' may appear as a group name, not a command
    GROUP_CONTEXT_VARS = {
        'USERADD_PARAM', 'GROUPADD_PARAM', 'GROUPMEMS_PARAM',
    }
    
    # Pattern for sudo as a group name (not a command)
    GROUP_CONTEXT_PATTERN = re.compile(r'-G\s+\S*sudo|--groups\s+\S*sudo')
    
    # Documentation variables: "su and sudo ..." there is prose, not a command
    DOCUMENTATION_VARS = {
        'SUMMARY', 'DESCRIPTION', 'HOMEPAGE', 'BUGTRACKER', 'AUTHOR',
        'MAINTAINER', 'RECIPE_MAINTAINER', 'SECTION', 'LICENSE',
    }
    
    # Pattern to extract variable name
    VAR_ASSIGN_PATTERN = re.compile(r'^([A-Z][A-Z0-9_]*)(?::[^\s=]+)?\s*[+?:]?=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_task = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track task function entry/exit
            if re.match(r'^(do_\w+|fakeroot\s+do_\w+)\s*\(\)\s*\{', stripped):
                in_task = True
                continue
            
            if in_task and stripped == '}':
                in_task = False
                continue
            
            # Skip documentation, including overrides (SUMMARY:${PN}-foo) and
            # continuation lines
            if context.owner_base(line_num) in self.DOCUMENTATION_VARS:
                continue
            
            # Skip if 'sudo' appears as a group name context
            if self.GROUP_CONTEXT_PATTERN.search(stripped):
                continue
            
            # Skip USERADD_PARAM and similar variables (sudo is a group name there)
            var_match = self.VAR_ASSIGN_PATTERN.match(stripped)
            if var_match:
                var_name = var_match.group(1)
                if var_name in self.GROUP_CONTEXT_VARS:
                    continue
            
            if in_task and self.SUDO_CMD_PATTERN.search(stripped):
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="sudo should not be used in Yocto tasks",
                    context=stripped[:60],
                    hint="Use 'fakeroot do_task()' for privileged operations",
                ))
            
            # Also check for sudo outside tasks (in variables) - but not group names
            elif not in_task and 'sudo' in stripped.lower() and '=' in stripped:
                if self.SUDO_CMD_PATTERN.search(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="sudo command found in recipe variable",
                        context=stripped[:60],
                        hint="Remove sudo - Yocto uses pseudo/fakeroot",
                    ))
        
        return results


class NetworkAccessInCompileRule(BaseRule):
    """
    Check for network access in compile/build tasks.
    
    Network access during compile breaks reproducibility and can cause
    random build failures. All fetching should happen in do_fetch.
    """
    
    rule_id = "TASK003"
    name = "Network Access in Compile"
    description = "Detects potential network access in compile/build tasks"
    default_severity = Severity.ERROR
    groups = ["reproducibility", "network"]
    hint = "All downloads should happen in do_fetch via SRC_URI"

    # Network access indicators
    NETWORK_PATTERNS = [
        re.compile(r'\bcurl\s+'),
        re.compile(r'\bwget\s+'),
        re.compile(r'\bpip\s+install'),
        re.compile(r'\bnpm\s+install'),
        re.compile(r'\byarn\s+install'),
        re.compile(r'\byarn\s+add'),
        re.compile(r'\bgit\s+clone'),
        re.compile(r'\bgit\s+fetch'),
        re.compile(r'\bgit\s+pull'),
        re.compile(r'\bcargo\s+fetch'),
        re.compile(r'\bgo\s+get'),
        re.compile(r'\bgo\s+mod\s+download'),
        re.compile(r'\bgo\s+mod\s+tidy'),  # Can trigger downloads
        re.compile(r'\bapt-get\s+'),
        re.compile(r'\bdnf\s+'),
        re.compile(r'\byum\s+'),
    ]
    
    # Tasks that should not access network
    BUILD_TASKS = [
        'do_compile', 'do_configure', 'do_install', 'do_package',
        'do_patch', 'do_unpack', 'do_prepare_recipe_sysroot'
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        current_task = None
        in_task = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track task function entry/exit
            task_match = re.match(r'^(fakeroot\s+)?(do_\w+)\s*\(\)\s*\{', stripped)
            if task_match:
                in_task = True
                current_task = task_match.group(2)
                continue
            
            if in_task and stripped == '}':
                in_task = False
                current_task = None
                continue
            
            # Check for network access in build tasks
            if in_task and current_task in self.BUILD_TASKS:
                for pattern in self.NETWORK_PATTERNS:
                    if pattern.search(stripped):
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=f"Potential network access in {current_task}",
                            context=stripped[:60],
                            hint="Move downloads to SRC_URI for do_fetch",
                        ))
                        break
        
        return results
