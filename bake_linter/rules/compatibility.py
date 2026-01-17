"""
Compatibility rules for Yocto recipes.

These rules check for compatibility and portability issues.
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class DeprecatedCompatibleHostRule(BaseRule):
    """
    Check for deprecated COMPATIBLE_HOST patterns.
    
    COMPATIBLE_HOST should use proper regex syntax with anchors.
    """
    
    rule_id = "COMPAT001"
    name = "Deprecated COMPATIBLE_HOST Syntax"
    description = "Detects deprecated or improper COMPATIBLE_HOST patterns"
    default_severity = Severity.WARNING
    groups = ["compatibility", "deprecated"]
    hint = "Use modern regex syntax with anchors: ^(pattern)$"

    COMPAT_HOST_PATTERN = re.compile(r'^COMPATIBLE_HOST\s*=\s*["\']([^"\']+)["\']')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            match = self.COMPAT_HOST_PATTERN.match(stripped)
            if match:
                regex_value = match.group(1)
                
                # Check for missing anchors in complex patterns
                if '.*' in regex_value or '|' in regex_value:
                    if not regex_value.startswith('^'):
                        results.append(self.create_result(
                            file=context.path,
                            line=line_num,
                            message="COMPATIBLE_HOST pattern missing ^ anchor",
                            context=stripped[:60],
                            hint="Add ^ at start of regex for proper matching",
                        ))
        
        return results


class UnjustifiedMachineArchRule(BaseRule):
    """
    Check for PACKAGE_ARCH = "${MACHINE_ARCH}" without machine-specific code.
    
    Using MACHINE_ARCH when not necessary reduces sstate reuse and
    increases build times.
    """
    
    rule_id = "COMPAT002"
    name = "Unjustified MACHINE_ARCH"
    description = "Detects PACKAGE_ARCH = \"${MACHINE_ARCH}\" without clear justification"
    default_severity = Severity.WARNING
    groups = ["compatibility", "performance"]
    hint = "Only use MACHINE_ARCH for truly machine-specific content"

    MACHINE_ARCH_PATTERN = re.compile(r'PACKAGE_ARCH\s*=\s*["\']?\$\{MACHINE_ARCH\}["\']?')
    
    # Indicators of legitimate machine-specific recipes
    MACHINE_SPECIFIC_INDICATORS = [
        re.compile(r'inherit\s+module'),  # Kernel module
        re.compile(r'inherit\s+kernel'),  # Kernel recipe
        re.compile(r'MACHINE_FEATURES'),
        re.compile(r'KERNEL_MODULE'),
        re.compile(r'MACHINE_EXTRA'),
        re.compile(r'COMPATIBLE_MACHINE'),
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        machine_arch_line = 0
        has_machine_arch = False
        has_justification = False
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.MACHINE_ARCH_PATTERN.search(stripped):
                has_machine_arch = True
                machine_arch_line = line_num
            
            for indicator in self.MACHINE_SPECIFIC_INDICATORS:
                if indicator.search(stripped):
                    has_justification = True
                    break
        
        if has_machine_arch and not has_justification:
            results.append(self.create_result(
                file=context.path,
                line=machine_arch_line,
                message="PACKAGE_ARCH = \"${MACHINE_ARCH}\" without clear machine-specific code",
                hint="Remove MACHINE_ARCH unless recipe has machine-specific content",
            ))
        
        return results
