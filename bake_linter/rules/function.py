# -*- coding: utf-8 -*-
"""
Function and task structure rules for Yocto recipes.

These rules check for proper function definitions, task ordering,
and consistency in function types.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List, Dict, Tuple

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class TaskFunctionOrderRule(BaseRule):
    """
    Check that standard task functions are in conventional order.
    
    While not strictly required, following the standard task order
    improves recipe readability and maintainability.
    """
    
    rule_id = "FUNCTION001"
    name = "Task Function Order"
    description = "Verifies standard task functions follow conventional order"
    default_severity = Severity.INFO
    groups = ["style", "functions"]
    hint = "Reorder task definitions to follow standard sequence"
    
    # Standard BitBake task order
    TASK_ORDER = [
        'do_fetch', 'do_unpack', 'do_patch',
        'do_prepare_recipe_sysroot', 'do_configure',
        'do_compile', 'do_install', 'do_populate_sysroot',
        'do_package', 'do_package_write',
    ]
    
    TASK_PATTERN = re.compile(r'^(?:fakeroot\s+)?(?:python\s+)?(do_\w+)\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        task_positions: List[Tuple[str, int]] = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            match = self.TASK_PATTERN.match(stripped)
            if match:
                task_name = match.group(1)
                # Only track standard tasks
                if task_name in self.TASK_ORDER:
                    task_positions.append((task_name, line_num))
        
        # Check order
        if len(task_positions) >= 2:
            for i in range(len(task_positions) - 1):
                curr_task, curr_line = task_positions[i]
                next_task, next_line = task_positions[i + 1]
                
                curr_idx = self.TASK_ORDER.index(curr_task) if curr_task in self.TASK_ORDER else -1
                next_idx = self.TASK_ORDER.index(next_task) if next_task in self.TASK_ORDER else -1
                
                if curr_idx > next_idx and curr_idx != -1 and next_idx != -1:
                    results.append(self.create_result(
                        file=context,
                        line=next_line,
                        message=f"Task {next_task} defined after {curr_task} (non-standard order)",
                        hint=f"Convention: {next_task} should come before {curr_task}",
                    ))
                    break  # One warning per file
        
        return results


class PythonShellMixingRule(BaseRule):
    """
    Check for mixing Python and shell function types for same task.
    
    Using different function types for the same task (base + append)
    can cause subtle bugs and confusion.
    """
    
    rule_id = "FUNCTION002"
    name = "Python/Shell Function Mixing"
    description = "Detects inconsistent mixing of Python and shell for same task"
    default_severity = Severity.WARNING
    groups = ["functions", "python", "shell"]
    hint = "Use consistent function type (all shell or all Python) for task"

    SHELL_TASK_PATTERN = re.compile(r'^(?:fakeroot\s+)?(do_\w+)\s*\(\)\s*\{')
    PYTHON_TASK_PATTERN = re.compile(r'^python\s+(do_\w+)(?:[_:]\w+)?\s*\(\)\s*\{')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        shell_tasks: Dict[str, int] = {}  # task -> line_num
        python_tasks: Dict[str, int] = {}
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Check for Python task first (more specific)
            match = self.PYTHON_TASK_PATTERN.match(stripped)
            if match:
                task_name = match.group(1)
                python_tasks[task_name] = line_num
                continue
            
            # Check for shell task
            match = self.SHELL_TASK_PATTERN.match(stripped)
            if match:
                task_name = match.group(1)
                shell_tasks[task_name] = line_num
        
        # Find tasks with mixed types
        mixed_tasks = set(shell_tasks.keys()) & set(python_tasks.keys())
        
        for task in mixed_tasks:
            # Report on the later occurrence
            line_num = max(shell_tasks[task], python_tasks[task])
            results.append(self.create_result(
                file=context,
                line=line_num,
                message=f"Task '{task}' has both shell and Python definitions",
                hint="Use consistent type: all shell or all Python",
            ))
        
        return results


class EmptyTaskOverrideRule(BaseRule):
    """
    Check for empty or meaningless task function overrides.
    
    Empty task overrides add processing overhead without benefit
    and may indicate incomplete implementation.
    """
    
    rule_id = "TASK004"
    name = "Empty Task Override"
    description = "Detects empty or meaningless task function overrides"
    default_severity = Severity.INFO
    groups = ["functions", "redundancy"]
    hint = "Remove empty task override or add implementation"

    TASK_START_PATTERN = re.compile(r'^(?:fakeroot\s+)?(?:python\s+)?(do_\w+)(?:[_:]\w+)?\s*\(\)\s*\{')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        in_task = False
        task_name = ""
        task_line = 0
        task_content = []
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            match = self.TASK_START_PATTERN.match(stripped)
            if match and not in_task:
                in_task = True
                task_name = match.group(1)
                task_line = line_num
                task_content = []
                brace_depth = 1
                continue
            
            if in_task:
                brace_depth += stripped.count('{') - stripped.count('}')
                
                # Collect non-empty, non-comment content
                if stripped and not stripped.startswith('#'):
                    if stripped != '}':
                        task_content.append(stripped)
                
                if brace_depth <= 0:
                    # Task ended - check if empty
                    if not task_content:
                        results.append(self.create_result(
                            file=context,
                            line=task_line,
                            message=f"Empty task override: {task_name}",
                            hint="Remove empty override or add implementation",
                        ))
                    
                    in_task = False
                    task_content = []
        
        return results
