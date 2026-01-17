"""
Task implementation rules for Yocto recipes.

These rules check for issues in shell task implementations like
do_compile, do_install, etc.
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
    """
    
    rule_id = "TASK001"
    name = "Unquoted Variable Expansion"
    description = "Detects unquoted shell variables in task code"
    default_severity = Severity.WARNING
    groups = ["shell", "reliability"]
    hint = "Quote variable expansions: \"${var}\" instead of ${var}"

    # Pattern for unquoted variable expansions in common contexts
    # Matches ${VAR} or $VAR that's not inside quotes
    UNQUOTED_PATTERNS = [
        # rm, cp, mv, install with unquoted path args
        re.compile(r'\b(rm|cp|mv|install|mkdir|chmod|chown)\s+(-[a-zA-Z]+\s+)*\$\{?[A-Za-z_][A-Za-z0-9_]*\}?(?!\s*["\'])'),
        # cd to unquoted variable
        re.compile(r'\bcd\s+\$\{?[A-Za-z_][A-Za-z0-9_]*\}?(?!\s*["\'])'),
        # for loop with unquoted variable in iteration
        re.compile(r'\bfor\s+\w+\s+in\s+\$\{?[A-Za-z_][A-Za-z0-9_]*\}?(?!\s*["\'])'),
    ]
    
    # High-risk variables that should always be quoted
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
                # Check high-risk variables specifically
                for var in self.HIGH_RISK_VARS:
                    # Look for ${VAR} or $VAR not in quotes
                    pattern = re.compile(rf'(\$\{{{var}\}}|\${var}\b)(?!["\'])')
                    if pattern.search(stripped):
                        # Check if it's actually unquoted
                        if not self._is_properly_quoted(stripped, var):
                            results.append(self.create_result(
                                file=context.path,
                                line=line_num,
                                message=f"High-risk variable ${var} may be unquoted",
                                context=stripped[:60],
                                hint=f'Use "${{{var}}}" to handle paths with spaces',
                            ))
        
        return results
    
    def _is_properly_quoted(self, line: str, var: str) -> bool:
        """Check if a variable is properly quoted in the line."""
        # Simple heuristic: look for the variable inside double quotes
        pattern = rf'"[^"]*\$\{{{var}\}}[^"]*"'
        if re.search(pattern, line):
            return True
        # Also check for single-quoted (though variable won't expand)
        pattern = rf"'[^']*\$\{{{var}\}}[^']*'"
        if re.search(pattern, line):
            return True
        return False


class SudoUsageRule(BaseRule):
    """
    Check for sudo usage in task implementations.
    
    Yocto builds should never require sudo - they use pseudo/fakeroot
    for privileged operations. sudo indicates a broken build process.
    """
    
    rule_id = "TASK002"
    name = "Sudo Usage in Tasks"
    description = "Detects sudo usage in recipe task code"
    default_severity = Severity.ERROR
    groups = ["security", "build"]
    hint = "Use fakeroot for privileged operations, not sudo"

    SUDO_PATTERN = re.compile(r'\bsudo\s+')

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
            
            if in_task and self.SUDO_PATTERN.search(stripped):
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message="sudo should not be used in Yocto tasks",
                    context=stripped[:60],
                    hint="Use 'fakeroot do_task()' for privileged operations",
                ))
            
            # Also check for sudo outside tasks (in variables)
            if 'sudo' in stripped.lower() and '=' in stripped:
                if self.SUDO_PATTERN.search(stripped):
                    results.append(self.create_result(
                        file=context.path,
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
                            file=context.path,
                            line=line_num,
                            message=f"Potential network access in {current_task}",
                            context=stripped[:60],
                            hint="Move downloads to SRC_URI for do_fetch",
                        ))
                        break
        
        return results
