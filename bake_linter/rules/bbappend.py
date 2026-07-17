# -*- coding: utf-8 -*-
"""
BBAppend-specific rules for Yocto recipes.

These rules check for proper .bbappend file patterns.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class MissingFilesextrapathsRule(BaseRule):
    """
    Check for .bbappend files adding files without FILESEXTRAPATHS.
    
    When a .bbappend adds files via SRC_URI, FILESEXTRAPATHS must be set
    so BitBake knows where to find the local files.
    """
    
    rule_id = "BBAPPEND001"
    name = "Missing FILESEXTRAPATHS"
    description = "Detects .bbappend files adding files without FILESEXTRAPATHS"
    default_severity = Severity.WARNING
    groups = ["bbappend"]
    hint = "Add FILESEXTRAPATHS:prepend := \"${THISDIR}/files:\""
    
    # Only applies to .bbappend files
    applicable_file_types = {"bbappend"}

    # Pattern to find file:// in SRC_URI
    FILE_URI_PATTERN = re.compile(r'file://')
    
    # Pattern to find FILESEXTRAPATHS
    FILESEXTRAPATHS_PATTERN = re.compile(r'^FILESEXTRAPATHS[_:]')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Only check .bbappend files
        if not str(context.path).endswith('.bbappend'):
            return results
        
        # Check if SRC_URI has file:// entries
        has_file_uri = False
        file_uri_line = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            
            if 'SRC_URI' in stripped and self.FILE_URI_PATTERN.search(stripped):
                has_file_uri = True
                file_uri_line = line_num
                break
        
        if not has_file_uri:
            return results
        
        # Check for FILESEXTRAPATHS
        has_filesextrapaths = False
        for line in context.lines:
            stripped = line.strip()
            if self.FILESEXTRAPATHS_PATTERN.match(stripped):
                has_filesextrapaths = True
                break
        
        if not has_filesextrapaths:
            results.append(self.create_result(
                file=context,
                line=file_uri_line,
                message="SRC_URI adds files but FILESEXTRAPATHS is not set",
                hint='Add: FILESEXTRAPATHS:prepend := "${THISDIR}/files:"',
            ))
        
        return results


class TaskOverrideWithoutSuffixRule(BaseRule):
    """
    Check for .bbappend files completely overriding tasks without :append/:prepend.
    
    In .bbappend files, using do_install() completely replaces the base recipe's
    task, which is usually unintended. Use do_install:append() or :prepend() instead.
    """
    
    rule_id = "BBAPPEND002"
    name = "Task Override Without Suffix"
    description = "Detects .bbappend files overriding tasks without :append/:prepend"
    default_severity = Severity.ERROR
    groups = ["bbappend", "syntax"]
    hint = "Use do_taskname:append() or do_taskname:prepend() instead"
    
    # Only applies to .bbappend files
    applicable_file_types = {"bbappend"}

    # Pattern to find task definitions that completely override (no :append/:prepend)
    # Matches: do_install() { or do_install () { but not do_install:append()
    TASK_OVERRIDE_PATTERN = re.compile(
        r'^(do_[a-z_]+)\s*\(\s*\)\s*\{?'
    )
    
    # Common tasks that should use :append/:prepend in bbappend
    COMMON_TASKS = [
        'do_install', 'do_configure', 'do_compile', 'do_patch',
        'do_unpack', 'do_fetch', 'do_prepare_recipe_sysroot',
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Only check .bbappend files
        if not str(context.path).endswith('.bbappend'):
            return results
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith("#"):
                continue
            
            match = self.TASK_OVERRIDE_PATTERN.match(stripped)
            if match:
                task_name = match.group(1)
                
                # Check it's not already using :append/:prepend
                if ':append' not in stripped and ':prepend' not in stripped:
                    # Check it's a common task
                    if task_name in self.COMMON_TASKS:
                        results.append(self.create_result(
                            file=context,
                            line=line_num,
                            message=f"'{task_name}()' completely overrides base recipe task",
                            context=stripped[:60],
                            hint=f"Use {task_name}:append() or {task_name}:prepend() to extend instead",
                        ))
        
        return results


class VersionSpecificBbappendRule(BaseRule):
    """
    Check for version-specific .bbappend files that may break on updates.
    
    Files like recipe_1.5.3.bbappend will stop working when the base recipe
    updates to a new version. Use recipe_%.bbappend for robustness.
    """
    
    rule_id = "BBAPPEND003"
    name = "Version-Specific bbappend"
    description = "Detects version-specific .bbappend files that may break on updates"
    default_severity = Severity.INFO
    groups = ["bbappend", "maintenance"]
    hint = "Consider using recipe_%.bbappend for version-agnostic appends"
    
    applicable_file_types = {"bbappend"}

    # Pattern to detect version-specific bbappend (has version number, not %)
    VERSION_PATTERN = re.compile(r'_\d+\.\d+(?:\.\d+)?\.bbappend$')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        if not str(context.path).endswith('.bbappend'):
            return results
        
        filename = context.path.name
        
        if self.VERSION_PATTERN.search(filename) and '%' not in filename:
            results.append(self.create_result(
                file=context,
                line=1,
                message=f"Version-specific bbappend '{filename}' may break on version updates",
                hint="Use recipe_%.bbappend unless version-specific changes are required",
            ))
        
        return results


class EmptyBbappendRule(BaseRule):
    """
    Check for empty or comment-only .bbappend files.
    
    Empty bbappend files add build overhead without providing value
    and should be removed or populated with actual content.
    """
    
    rule_id = "BBAPPEND004"
    name = "Empty bbappend File"
    description = "Detects .bbappend files with no actual content"
    default_severity = Severity.WARNING
    groups = ["bbappend", "cleanup"]
    hint = "Remove empty .bbappend or add actual configuration"
    
    applicable_file_types = {"bbappend"}

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        if not str(context.path).endswith('.bbappend'):
            return results
        
        # Check if there's any non-comment, non-whitespace content
        has_content = False
        for line in context.lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                has_content = True
                break
        
        if not has_content:
            results.append(self.create_result(
                file=context,
                line=1,
                message="Empty .bbappend file (only comments or whitespace)",
                hint="Remove unused .bbappend or add actual configuration",
            ))
        
        return results


class GlobalVariableInBbappendRule(BaseRule):
    """
    Check for global configuration variables in .bbappend files.
    
    Certain variables should only be set in local.conf or distro config,
    not in recipe bbappends as they affect the entire build.
    """
    
    rule_id = "BBAPPEND005"
    name = "Global Variable in bbappend"
    description = "Detects global configuration variables in .bbappend files"
    default_severity = Severity.WARNING
    groups = ["bbappend", "scope"]
    hint = "Move global settings to local.conf or distro configuration"
    
    applicable_file_types = {"bbappend"}

    # Variables that should NOT be set in bbappend files
    GLOBAL_VARIABLES = [
        'TMPDIR', 'DL_DIR', 'SSTATE_DIR', 'DEPLOY_DIR',
        'DISTRO', 'MACHINE', 'TCMODE', 'TCLIBC',
        'BB_NUMBER_THREADS', 'PARALLEL_MAKE',
        'PACKAGE_CLASSES', 'EXTRA_IMAGE_FEATURES',
        'IMAGE_INSTALL', 'IMAGE_FEATURES',
        'DISTRO_FEATURES', 'MACHINE_FEATURES',
        'LICENSE_FLAGS_ACCEPTED', 'LICENSE_FLAGS_WHITELIST',
        'BBMASK', 'BBLAYERS',
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        if not str(context.path).endswith('.bbappend'):
            return results
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            for var in self.GLOBAL_VARIABLES:
                # Check for direct assignment or append
                if re.match(rf'^{var}\s*[?+:]?=', stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message=f"Global variable '{var}' should not be set in .bbappend",
                        context=stripped[:60],
                        hint="Move to local.conf, site.conf, or distro configuration",
                    ))
                    break  # One warning per line
        
        return results
