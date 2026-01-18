# -*- coding: utf-8 -*-
"""
Naming convention rules for Yocto recipes.

These rules check for consistent and proper naming conventions.

(c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
All rights reserved.
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
    
    IMPORTANT: This rule only applies to BitBake metadata context, NOT to
    Python code inside python functions where PEP 8 lowercase_with_underscores
    is the correct style for local variables.
    """
    
    rule_id = "NAMING001"
    name = "Variable Naming Convention"
    description = "Check for proper BitBake variable naming"
    default_severity = Severity.WARNING
    groups = ["naming", "style"]

    # Pattern for lowercase variable names (potential issue)
    LOWERCASE_VAR_PATTERN = re.compile(r'^[a-z][a-z0-9_]*\s*=')
    
    # Pattern to detect python function definition
    # Matches: python __anonymous() {, python do_foo() {, python foo:append() {
    PYTHON_FUNC_START = re.compile(r'^python\s+\w+(?::\w+)?\s*\(\s*\)\s*\{')
    
    # Pattern to detect shell function definition
    # Matches: do_install() {, do_configure:append() {, fakeroot do_install() {
    SHELL_FUNC_START = re.compile(r'^(?:fakeroot\s+)?do_\w+(?::\w+)?\s*\(\s*\)\s*\{')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        in_python_func = False
        in_shell_func = False
        brace_depth = 0
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Track entry into Python function blocks
            if self.PYTHON_FUNC_START.match(stripped):
                in_python_func = True
                brace_depth = 1
                continue
            
            # Track entry into shell function blocks
            if self.SHELL_FUNC_START.match(stripped):
                in_shell_func = True
                brace_depth = 1
                continue
            
            # Track brace depth to know when we exit a function
            if in_python_func or in_shell_func:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_python_func = False
                    in_shell_func = False
                    brace_depth = 0
                # Skip checking inside Python functions - lowercase is correct PEP 8 style
                # Skip checking inside shell functions - shell variables can be lowercase
                continue
            
            # Check for lowercase variable names (only in BitBake metadata context)
            if self.LOWERCASE_VAR_PATTERN.match(stripped):
                var_name = stripped.split("=")[0].strip()
                
                # These are valid lowercase names (keywords/directives)
                if var_name in {"do_", "python", "inherit", "require", "include"}:
                    continue
                
                results.append(self.create_result(
                    file=context.path,
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
    """
    
    rule_id = "NAMING002"
    name = "Recipe Naming Convention"
    description = "Check recipe file naming follows conventions"
    default_severity = Severity.INFO
    groups = ["naming", "style"]
    applicable_file_types = {"recipe"}

    # Pattern for valid recipe names
    VALID_NAME_PATTERN = re.compile(r'^[a-z0-9][-a-z0-9+.]*_[0-9].*\.bb$')

    def check(self, context: FileContext) -> List[LintResult]:
        if not self.is_applicable(context):
            return []
        
        results = []
        filename = context.path.name
        
        # Check for underscore in recipe name (before version)
        name_part = filename.rsplit("_", 1)[0] if "_" in filename else filename
        
        if "__" in name_part or name_part != name_part.replace("_", "-"):
            results.append(self.create_result(
                file=context.path,
                message=f"Recipe name uses underscore; prefer hyphens (e.g., 'my-recipe' not 'my_recipe')",
                hint="Rename recipe to use hyphens instead of underscores in the name portion",
                severity=Severity.INFO,
            ))
        
        # Check for missing version
        if "_" not in filename:
            results.append(self.create_result(
                file=context.path,
                message="Recipe filename missing version (expected: name_version.bb)",
                hint="Rename recipe to include version, e.g., myrecipe_1.0.bb or myrecipe_git.bb",
            ))
        
        # Check for uppercase in filename
        if filename != filename.lower():
            results.append(self.create_result(
                file=context.path,
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
            for assignment in context.variables["PN"]:
                actual_pn = assignment.value.strip().strip('"').strip("'")
                
                if actual_pn and actual_pn != expected_pn:
                    results.append(self.create_result(
                        file=context.path,
                        line=assignment.line,
                        message=f"PN ('{actual_pn}') differs from recipe filename ('{expected_pn}')",
                        hint="Either rename the recipe or remove explicit PN setting",
                    ))
        
        return results
