# -*- coding: utf-8 -*-
"""
Variable assignment rules for Yocto recipes.

These rules check for proper variable usage patterns.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
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


class UnusedVariableAssignmentRule(BaseRule):
    """
    Check for variables assigned but never referenced.
    
    Variables that are defined but not used may indicate dead code
    or forgotten refactoring.
    """
    
    rule_id = "VARIABLES003"
    name = "Unused Variable Assignment"
    description = "Detects variables assigned but never referenced in the recipe"
    default_severity = Severity.INFO
    groups = ["variables", "redundancy"]
    hint = "Remove unused variable or add reference if intended"
    
    # Variables that should be excluded (metadata, exported, consumed by classes, etc.)
    STANDARD_VARS = {
        # Core BitBake variables
        'PN', 'PV', 'PR', 'PE', 'S', 'B', 'D', 'T', 'WORKDIR',
        'SRCPV', 'SRCDATE', 'SRCREV',
        
        # Standard metadata (consumed by BitBake)
        'LICENSE', 'LIC_FILES_CHKSUM', 'SRC_URI',
        'SUMMARY', 'DESCRIPTION', 'HOMEPAGE', 'BUGTRACKER',
        'SECTION', 'AUTHOR', 'MAINTAINER', 'PRIORITY',
        
        # Dependencies and packages
        'DEPENDS', 'RDEPENDS', 'RRECOMMENDS', 'RPROVIDES',
        'RCONFLICTS', 'RREPLACES', 'PACKAGES', 'PROVIDES',
        'FILES', 'FILESEXTRAPATHS', 'FILESPATH',
        
        # Build configuration
        'EXTRA_OECONF', 'EXTRA_OECMAKE', 'EXTRA_OEMAKE',
        'PACKAGECONFIG', 'COMPATIBLE_MACHINE', 'COMPATIBLE_HOST',
        'MACHINE_FEATURES', 'DISTRO_FEATURES', 'BBCLASSEXTEND',
        'inherit', 'require', 'include',
        
        # Compiler flags
        'CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CPPFLAGS',
        
        # Package metadata
        'PACKAGE_ARCH', 'INSANE_SKIP', 'ALLOW_EMPTY',
        
        # Features check variables (consumed by features_check.bbclass)
        'REQUIRED_DISTRO_FEATURES', 'CONFLICT_DISTRO_FEATURES', 'ANY_OF_DISTRO_FEATURES',
        'REQUIRED_MACHINE_FEATURES', 'CONFLICT_MACHINE_FEATURES', 'ANY_OF_MACHINE_FEATURES',
        
        # Upstream tracking (consumed by devtool/recipetool)
        'UPSTREAM_CHECK_URI', 'UPSTREAM_CHECK_REGEX',
        'UPSTREAM_CHECK_GITTAGREGEX', 'UPSTREAM_VERSION_UNKNOWN',
        
        # CVE tracking
        'CVE_PRODUCT', 'CVE_VERSION', 'CVE_CHECK_IGNORE',
        
        # Layer metadata (consumed by bitbake-layers)
        'LAYERSERIES_COMPAT', 'LAYERDEPENDS', 'LAYERRECOMMENDS',
        
        # Systemd (consumed by systemd.bbclass)
        'SYSTEMD_SERVICE', 'SYSTEMD_AUTO_ENABLE', 'SYSTEMD_PACKAGES',
        
        # Init scripts (consumed by update-rc.d.bbclass)
        'INITSCRIPT_NAME', 'INITSCRIPT_PARAMS', 'INITSCRIPT_PACKAGES',
        
        # Kernel modules (consumed by module.bbclass)
        'KERNEL_MODULE_AUTOLOAD', 'KERNEL_MODULE_PROBECONF',
        
        # Update alternatives (consumed by update-alternatives.bbclass)
        'ALTERNATIVE', 'ALTERNATIVE_PRIORITY', 'ALTERNATIVE_LINK_NAME', 'ALTERNATIVE_TARGET',
        
        # Useradd (consumed by useradd.bbclass)
        'USERADD_PACKAGES', 'USERADD_PARAM', 'GROUPADD_PARAM', 'GROUPMEMS_PARAM',
        
        # RAUC (consumed by rauc.bbclass)
        'RAUC_BUNDLE_COMPATIBLE', 'RAUC_BUNDLE_VERSION', 'RAUC_BUNDLE_DESCRIPTION',
        'RAUC_BUNDLE_FORMAT', 'RAUC_BUNDLE_SLOTS', 'RAUC_KEY_FILE', 'RAUC_CERT_FILE',
    }

    VAR_ASSIGNMENT_PATTERN = re.compile(r'^([A-Z][A-Z0-9_]*)\s*[?:]?=')
    VAR_REFERENCE_PATTERN = re.compile(r'\$\{([A-Z][A-Z0-9_]*)\}')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        assignments = {}  # var_name -> line_num
        references = set()
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track assignments
            match = self.VAR_ASSIGNMENT_PATTERN.match(stripped)
            if match:
                var_name = match.group(1)
                if var_name not in self.STANDARD_VARS:
                    assignments[var_name] = line_num
            
            # Track references
            refs = self.VAR_REFERENCE_PATTERN.findall(line)
            references.update(refs)
        
        # Find unused variables
        for var_name, line_num in assignments.items():
            if var_name not in references:
                results.append(self.create_result(
                    file=context.path,
                    line=line_num,
                    message=f"Variable '{var_name}' assigned but never referenced",
                    hint="Remove if unused or add ${" + var_name + "} reference",
                ))
        
        return results


class VariableRedefinitionRule(BaseRule):
    """
    Check for variables redefined without clear intent.
    
    Multiple immediate assignments to the same variable may indicate
    copy-paste errors or confusion.
    """
    
    rule_id = "VARIABLES004"
    name = "Variable Redefinition"
    description = "Detects variables redefined in same scope without clear intent"
    default_severity = Severity.WARNING
    groups = ["variables", "conflicts"]
    hint = "Use ?= for defaults, += for additions, or remove duplicate"

    IMMEDIATE_ASSIGN_PATTERN = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*')
    # Override pattern: VAR:override or VAR_override (must have : or _ followed by non-underscore)
    OVERRIDE_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*:[a-z][\w-]*\s*=|^[A-Z][A-Z0-9_]*_[a-z][\w-]*\s*=')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        immediate_assignments = {}  # var_name -> [(line_num, line)]
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Skip override-specific assignments
            if self.OVERRIDE_PATTERN.match(stripped):
                continue
            
            match = self.IMMEDIATE_ASSIGN_PATTERN.match(stripped)
            if match:
                var_name = match.group(1)
                if var_name not in immediate_assignments:
                    immediate_assignments[var_name] = []
                immediate_assignments[var_name].append((line_num, stripped))
        
        # Flag variables with multiple immediate assignments
        for var_name, assigns in immediate_assignments.items():
            if len(assigns) > 1:
                first_line = assigns[0][0]
                last_line = assigns[-1][0]
                results.append(self.create_result(
                    file=context.path,
                    line=last_line,
                    message=f"Variable '{var_name}' redefined (first at line {first_line})",
                    hint="Use ?= for default, += to append, or remove duplicate",
                ))
        
        return results


class ExcessiveAppendPrependRule(BaseRule):
    """
    Check for excessive append/prepend chaining on same variable.
    
    Many append/prepend operations can be hard to track and may
    indicate need for direct assignment.
    """
    
    rule_id = "VARIABLES005"
    name = "Excessive Append/Prepend"
    description = "Detects variables with many append/prepend operations"
    default_severity = Severity.INFO
    groups = ["variables", "style"]
    hint = "Consider using direct assignment or simplifying"
    
    MAX_OPERATIONS = 3

    APPEND_PREPEND_PATTERN = re.compile(r'^([A-Z][A-Z0-9_]*)[:_](append|prepend)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        operations = {}  # var_name -> count
        first_occurrence = {}  # var_name -> line_num
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            match = self.APPEND_PREPEND_PATTERN.match(stripped)
            if match:
                var_name = match.group(1)
                if var_name not in operations:
                    operations[var_name] = 0
                    first_occurrence[var_name] = line_num
                operations[var_name] += 1
        
        for var_name, count in operations.items():
            if count > self.MAX_OPERATIONS:
                results.append(self.create_result(
                    file=context.path,
                    line=first_occurrence[var_name],
                    message=f"Variable '{var_name}' has {count} append/prepend operations",
                    hint="Consider simplifying with direct assignment",
                ))
        
        return results
