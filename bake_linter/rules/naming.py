# -*- coding: utf-8 -*-
"""
Naming convention rules for Yocto recipes.

These rules check for consistent and proper naming conventions.

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


class VariableNamingRule(BaseRule):
    """
    Check for proper variable naming conventions.
    
    BitBake variables should follow these conventions:
    - All uppercase for standard variables (LICENSE, SRC_URI)
    - Lowercase for overrides after colon (RDEPENDS:${PN})
    
    IMPORTANT: This rule only applies to BitBake metadata context, NOT to:
    - Python code inside python functions (PEP 8 lowercase is correct)
    - Shell code inside shell functions (lowercase locals are standard)
    - Known lowercase Yocto/OE-Core variables (hostname, etc.)
    
    Shell functions include do_* tasks and any custom shell function like:
    - do_install() { ... }
    - my_helper_func () { ... }
    - uboot_compile_config () { ... }
    """
    
    rule_id = "NAMING001"
    name = "Variable Naming Convention"
    description = "Check for proper BitBake variable naming"
    default_severity = Severity.WARNING
    groups = ["naming", "style"]

    # Known lowercase BitBake/Yocto variables (intentional exceptions)
    # These are legitimate lowercase variables defined by Yocto/OE-Core
    LOWERCASE_EXCEPTIONS = {
        # base-files recipe
        'hostname',         # Controls /etc/hostname creation
        # Python context (though usually inside functions)
        'd',                # DataSmart object
        'e',                # Event object
        # Bootloader recipes
        'cfgscript',        # U-Boot configuration script
        # Kernel recipes
        'kconf',            # Kernel config fragments

        # autotools.bbclass: extra aclocal search paths
        'acpaths',
        # security_flags.inc: the _FORTIFY_SOURCE flag a recipe may clear
        'lcl_maybe_fortify',
        # bitbake.conf installation directories
        'prefix', 'exec_prefix', 'baselib',
    }

    # Other lowercase names that BitBake metadata defines on purpose:
    # bitbake.conf directories (bindir, systemd_unitdir, base_libdir,
    # nonarch_base_libdir, ...) and the program lists recipes hand to
    # update-alternatives (base_bin_progs, sbin_progs, ...).
    LOWERCASE_EXCEPTION_PATTERN = re.compile(
        r'^(?:[a-z0-9_]*dir|base_[a-z0-9_]+|[a-z0-9_]*_prefix|[a-z0-9_]*_progs)$'
    )

    # Pattern for lowercase variable names (potential issue)
    LOWERCASE_VAR_PATTERN = re.compile(
        r'^([a-z][a-z0-9_]*)\s*(?:\?\?=|\?=|:=|\+=|=\+|\.=|=\.|=)'
    )

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        for line_num, line in enumerate(context.lines, start=1):
            # Only BitBake assignments: a line starting at column 0 that
            # starts a logical assignment. Continuation lines and function
            # bodies (shell locals, PEP 8 python names) are not BitBake
            # variables.
            if line[:1].isspace() or not context.is_top_level_assignment(line_num):
                continue
            stripped = line.strip()

            # Check for lowercase variable names (only in BitBake metadata context)
            match = self.LOWERCASE_VAR_PATTERN.match(stripped)
            if match:
                var_name = match.group(1)

                # Skip known Yocto/OE-Core lowercase variables
                if (var_name in self.LOWERCASE_EXCEPTIONS
                        or self.LOWERCASE_EXCEPTION_PATTERN.match(var_name)):
                    continue
                
                # These are valid lowercase names (keywords/directives)
                if var_name in {"do_", "python", "inherit", "require", "include"}:
                    continue
                
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Lowercase variable name '{var_name}' - BitBake variables should be UPPERCASE",
                    context=stripped[:60],
                    hint="Use UPPERCASE for BitBake variables",
                ))
        
        return results


class RecipeNamingRule(BaseRule):
    """
    Check recipe file naming conventions.
    
    Recipe files should follow the naming convention:
    - recipe-name_version.bb
    - Use hyphens, not underscores in names
    - Version should be present
    
    Exceptions where version in filename is optional:
    - Native recipes (-native): often use PV in recipe
    - Cross recipes (-cross, -crosssdk): toolchain components
    - Packagegroups (packagegroup-*): configuration only
    - Init scripts (init-*, initscripts): system configuration
    - Base system (base-*, core-*): infrastructure
    """
    
    rule_id = "NAMING002"
    name = "Recipe Naming Convention"
    description = "Check recipe file naming follows conventions"
    default_severity = Severity.INFO
    groups = ["naming", "style"]
    applicable_file_types = {"recipe"}

    # Pattern for valid recipe names
    VALID_NAME_PATTERN = re.compile(r'^[a-z0-9][-a-z0-9+.]*_[0-9].*\.bb$')
    
    # Recipes that commonly don't have version in filename
    # These are typically infrastructure/toolchain recipes where PV is set in recipe
    VERSION_OPTIONAL_SUFFIXES = [
        '-native',
        '-cross',
        '-crosssdk',
        '-initial',
        '-sdk',
    ]
    
    VERSION_OPTIONAL_PREFIXES = [
        'packagegroup-',
        'init-',
        'initscripts',
        'base-',
        'core-image-',
        'virtual/',
    ]

    def _is_version_optional(self, filename: str, content: str) -> bool:
        """Check if version in filename is optional for this recipe type."""
        name_part = filename.replace('.bb', '')
        
        # Check suffixes (native, cross, etc.)
        for suffix in self.VERSION_OPTIONAL_SUFFIXES:
            if name_part.endswith(suffix):
                return True
        
        # Check prefixes (packagegroup, init, etc.)
        for prefix in self.VERSION_OPTIONAL_PREFIXES:
            if name_part.startswith(prefix):
                return True
        
        # Check if PV is defined in recipe content (version in recipe, not filename)
        if re.search(r'^\s*PV\s*[?:]?=', content, re.MULTILINE):
            return True
        
        return False

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        filename = context.path.name
        
        # Check for underscore in recipe name (before version)
        name_part = filename.rsplit("_", 1)[0] if "_" in filename else filename
        
        if "__" in name_part or name_part != name_part.replace("_", "-"):
            results.append(self.create_result(
                file=context,
                message=f"Recipe name uses underscore; prefer hyphens (e.g., 'my-recipe' not 'my_recipe')",
                hint="Rename recipe to use hyphens instead of underscores in the name portion",
                severity=Severity.INFO,
            ))
        
        # Check for missing version
        if "_" not in filename:
            # Skip if version is optional for this recipe type
            if not self._is_version_optional(filename, context.content):
                results.append(self.create_result(
                    file=context,
                    message="Recipe filename missing version (expected: name_version.bb)",
                    hint="Rename recipe to include version, e.g., myrecipe_1.0.bb or myrecipe_git.bb",
                ))
        
        # Check for uppercase in filename
        if filename != filename.lower():
            results.append(self.create_result(
                file=context,
                message="Recipe filename contains uppercase characters",
                hint="Use lowercase for recipe filenames",
            ))
        
        return results


class InconsistentPNRule(BaseRule):
    """
    Check that PN matches the recipe filename.
    
    If PN is explicitly set, it should typically match the recipe name.
    """
    
    rule_id = "NAMING003"
    name = "PN Consistency Check"
    description = "Check that PN matches recipe filename if explicitly set"
    default_severity = Severity.WARNING
    groups = ["naming", "consistency"]
    applicable_file_types = {"recipe"}

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        
        # Get recipe name from filename
        filename = context.path.name
        expected_pn = filename.rsplit("_", 1)[0] if "_" in filename else filename.replace(".bb", "")
        
        # Check if PN is explicitly set
        if "PN" in context.variables:
            # PN suffixed with expansions is the cross-canadian/SDK idiom:
            # one recipe built per target, e.g. foo-cross-canadian-${MACHINE}
            suffixed = re.compile(re.escape(expected_pn) + r'(?:-\$\{[A-Z_]+\})+')
            for assignment in context.variables["PN"]:
                # PN:class-devupstream and similar name a variant of the
                # recipe for one override only
                if assignment.is_override:
                    continue
                actual_pn = assignment.value.strip().strip('"').strip("'")

                if actual_pn and actual_pn != expected_pn and not suffixed.fullmatch(actual_pn):
                    results.append(self.create_result(
                        file=context,
                        line=assignment.line,
                        message=f"PN ('{actual_pn}') differs from recipe filename ('{expected_pn}')",
                        hint="Either rename the recipe or remove explicit PN setting",
                    ))
        
        return results
